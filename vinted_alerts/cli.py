"""Command line entry point: `python -m vinted_alerts <command>`."""

from __future__ import annotations

import argparse
import logging
import sys

from .client import VintedClient
from .config import load_config
from .deals import Deal
from .notify import build_notifiers
from .scanner import Scanner
from .store import Store


def _build(args) -> tuple[Scanner, Store]:
    config = load_config(args.config)
    store = Store(config.db_path)
    client = VintedClient(domain=config.domain)
    notifiers = build_notifiers(config.telegram, config.discord)
    return Scanner(config, client, store, notifiers), store


def cmd_run(args) -> int:
    scanner, store = _build(args)
    try:
        scanner.run_forever()
    except KeyboardInterrupt:
        print("\nInterrotto.")
    finally:
        store.close()
    return 0


def cmd_once(args) -> int:
    scanner, store = _build(args)
    try:
        deals = scanner.run_once()
        print(f"Scansione completata: {len(deals)} affari trovati")
    finally:
        store.close()
    return 0


def cmd_stats(args) -> int:
    config = load_config(args.config)
    store = Store(config.db_path)
    rows = store.stats()
    if not rows:
        print("Nessun dato ancora: esegui prima 'once' o 'run'.")
    for watch in config.watches:
        median, n = store.median_price(watch.name)
        row = next((r for r in rows if r[0] == watch.name), None)
        if not row:
            continue
        _, count, low, avg, alerted = row
        print(f"{watch.name}: {count} annunci visti · mediana {median:.2f} (ultimi {n}) · "
              f"media {avg:.2f} · minimo {low:.2f} · avvisi {alerted or 0}")
    store.close()
    return 0


def cmd_search(args) -> int:
    """Quick one-off search, handy to check filters and typical prices."""
    config = load_config(args.config) if args.config else None
    client = VintedClient(domain=config.domain if config else args.domain)
    items = client.search([("search_text", args.query)])
    for it in items[: args.limit]:
        print(f"{it.total_price:8.2f} {it.currency}  {it.title[:60]:60}  {it.url}")
    if items:
        prices = sorted(i.total_price for i in items)
        print(f"\n{len(items)} annunci · mediana {prices[len(prices) // 2]:.2f} · "
              f"min {prices[0]:.2f} · max {prices[-1]:.2f}")
    return 0


def cmd_test_notify(args) -> int:
    from .client import Item

    config = load_config(args.config)
    item = Item(id=1, title="Articolo di prova", price=10.0, total_price=11.2, currency="EUR",
                url=f"https://{config.domain}/", brand="Test", size="M", condition="Ottime")
    deal = Deal(item=item, price=11.2, reasons=["notifica di prova"])
    for notifier in build_notifiers(config.telegram, config.discord):
        notifier.send("test", deal)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vinted_alerts",
                                     description="Avvisi di prezzo per Vinted")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, help_text in (
        ("run", cmd_run, "monitora il feed in continuo"),
        ("once", cmd_once, "esegue una sola scansione"),
        ("stats", cmd_stats, "mostra prezzi medi raccolti"),
        ("test-notify", cmd_test_notify, "invia una notifica di prova"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("-c", "--config", default="config.toml")
        p.set_defaults(func=func)

    p = sub.add_parser("search", help="ricerca veloce senza configurazione")
    p.add_argument("query")
    p.add_argument("-c", "--config")
    p.add_argument("--domain", default="www.vinted.it")
    p.add_argument("-n", "--limit", type=int, default=20)
    p.set_defaults(func=cmd_search)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S",
                        stream=sys.stderr)
    return args.func(args)
