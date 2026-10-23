"""Scan loop: fetch new listings, update price history, fire alerts."""

from __future__ import annotations

import logging
import random
import time

from .client import VintedClient, VintedError
from .config import Config, Watch
from .deals import Deal, evaluate, matches_filters
from .store import Store

log = logging.getLogger(__name__)


class Scanner:
    def __init__(self, config: Config, client: VintedClient, store: Store, notifiers: list):
        self.config = config
        self.client = client
        self.store = store
        self.notifiers = notifiers

    def _price(self, item) -> float:
        return item.total_price if self.config.use_total_price else item.price

    def bootstrap(self, watch: Watch) -> None:
        """First run for a watch: learn prices from existing listings without alerting."""
        if self.store.has_history(watch.name):
            return
        log.info("[%s] primo avvio: raccolgo i prezzi attuali per calcolare la media", watch.name)
        for page in range(1, self.config.bootstrap_pages + 1):
            items = self.client.search(watch.params, page=page)
            for item in items:
                if matches_filters(watch, item):
                    self.store.add(watch.name, item.id, self._price(item), item.title, item.url)
            if not items:
                break
        median, n = self.store.median_price(watch.name)
        if median is not None:
            log.info("[%s] mediana iniziale %.2f su %d annunci", watch.name, median, n)

    def scan_watch(self, watch: Watch) -> list[Deal]:
        deals = []
        for page in range(1, self.config.pages_per_scan + 1):
            items = self.client.search(watch.params, page=page)
            new = [i for i in items if not self.store.is_seen(watch.name, i.id)]
            for item in new:
                if not matches_filters(watch, item):
                    continue
                price = self._price(item)
                # Evaluate against history *before* adding this item to it.
                median, samples = self.store.median_price(watch.name)
                deal = evaluate(watch, item, price, median, samples)
                self.store.add(watch.name, item.id, price, item.title, item.url,
                               alerted=deal is not None)
                if deal:
                    deals.append(deal)
                    self._notify(watch, deal)
            # Results are newest first: if a page had nothing new, older pages won't either.
            if not new:
                break
        return deals

    def _notify(self, watch: Watch, deal: Deal) -> None:
        for notifier in self.notifiers:
            try:
                notifier.send(watch.name, deal)
            except Exception:  # one broken channel must not stop the others
                log.exception("Notifica fallita su %s", type(notifier).__name__)

    def run_once(self) -> list[Deal]:
        deals = []
        for watch in self.config.watches:
            try:
                self.bootstrap(watch)
                deals += self.scan_watch(watch)
            except (VintedError, OSError, ValueError) as e:
                log.error("[%s] %s", watch.name, e)
            time.sleep(random.uniform(1, 3))  # be gentle between searches
        return deals

    def run_forever(self) -> None:
        log.info("Monitoraggio di %d ricerche ogni ~%ds (Ctrl+C per uscire)",
                 len(self.config.watches), self.config.interval)
        while True:
            deals = self.run_once()
            log.info("Scansione completata: %d affari trovati", len(deals))
            # Jitter makes the polling pattern less bot-like.
            time.sleep(self.config.interval * random.uniform(0.8, 1.2))
