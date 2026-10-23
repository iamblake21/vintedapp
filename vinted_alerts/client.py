"""Client that reads listings from Vinted's catalog (search results) page.

Vinted no longer serves the old public `/api/v2/catalog/items` endpoint, but the
server-rendered catalog page contains every listing card, so we parse those.
"""

from __future__ import annotations

import html
import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse

import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

# Params we control ourselves; ignored when copied from a website URL.
_IGNORED_URL_PARAMS = {"time", "search_id", "page", "order", "disabled_personalization"}

# Card labels per site language, mapped to Item fields.
_LABELS = {
    "brand": "brand", "marca": "brand", "marque": "brand", "marke": "brand", "merk": "brand",
    "condizioni": "condition", "condition": "condition", "état": "condition",
    "zustand": "condition", "estado": "condition", "staat": "condition",
    "taglia": "size", "size": "size", "taille": "size", "größe": "size",
    "talla": "size", "maat": "size",
}

_TAG_RE = re.compile(r"<(a|img)\b[^>]*product-item-id-(\d+)--(overlay-link|image--img)[^>]*>")
_ATTR_RE = re.compile(r'([a-zA-Z-]+)="([^"]*)"')
# One money token such as "20.00 €", "1.234,50 €" or "£20.00".
_MONEY_RE = re.compile(r"^(?P<pre>[^\d\s]{1,3})?\s?(?P<amount>\d+(?:[.,\u00a0\u202f]\d+)*)"
                       r"\s?(?P<post>[^\d\s]{1,3})?$")
_LABEL_SPLIT_RE = re.compile(r",\s(?=[^,:]{2,20}:\s)")

_CURRENCIES = {"€": "EUR", "£": "GBP", "zł": "PLN", "Kč": "CZK", "kr": "SEK", "Ft": "HUF",
               "lei": "RON", "$": "USD"}


class VintedError(Exception):
    pass


@dataclass(frozen=True)
class Item:
    id: int
    title: str
    price: float
    total_price: float  # price + buyer protection fee, what you actually pay
    currency: str
    url: str
    brand: str = ""
    size: str = ""
    condition: str = ""
    photo_url: str = ""


def parse_amount(text: str) -> float:
    """Parse "20.00", "20,00", "1.234,50" or "1,234.50"."""
    text = text.replace(" ", "").replace(" ", "").replace(" ", "")
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text)


def parse_card_title(raw: str) -> dict:
    """Split a card label like
    "Nike Dunk, Brand: Nike, Condizioni: Ottime, Taglia: 38, 40.00 €, 42.70 €".

    Fields are separated by ", " while decimal commas ("44,5") have no space,
    so the last one or two tokens are the item price and the total price."""
    tokens = html.unescape(raw).strip().split(", ")
    money = []
    while tokens and len(money) < 2:
        m = _MONEY_RE.match(tokens[-1].strip())
        if not m or not (m.group("pre") or m.group("post")):
            break
        money.insert(0, m)
        tokens.pop()
    if not money or not tokens:
        raise ValueError(f"prezzo non trovato in {raw!r}")
    symbol = money[0].group("pre") or money[0].group("post")
    fields = {"price": parse_amount(money[0].group("amount")),
              "total_price": parse_amount(money[-1].group("amount")),
              "currency": _CURRENCIES.get(symbol, symbol)}
    head, *labelled = _LABEL_SPLIT_RE.split(", ".join(tokens))
    fields["title"] = head.strip()
    for part in labelled:
        label, _, value = part.partition(":")
        key = _LABELS.get(label.strip().lower())
        if key:
            fields[key] = value.strip()
    return fields


def parse_catalog_html(page: str, base_url: str) -> list[Item]:
    cards: dict[int, dict] = {}
    for m in _TAG_RE.finditer(page):
        attrs = dict(_ATTR_RE.findall(m.group(0)))
        card = cards.setdefault(int(m.group(2)), {})
        if m.group(1) == "a":
            card["href"] = html.unescape(attrs.get("href", ""))
            card["label"] = attrs.get("title", "")
        else:
            card["photo"] = html.unescape(attrs.get("src", ""))
            card.setdefault("label", attrs.get("alt", ""))
    items = []
    for item_id, card in cards.items():
        try:
            fields = parse_card_title(card.get("label", ""))
        except ValueError as e:
            log.debug("Annuncio %s ignorato: %s", item_id, e)
            continue
        href = card.get("href", "").split("?")[0] or f"/items/{item_id}"
        items.append(Item(id=item_id, url=base_url + href if href.startswith("/") else href,
                          photo_url=card.get("photo", ""), **fields))
    return items


def params_from_search_url(url: str) -> list[tuple[str, str]]:
    """Keep the filters of a search URL copied from the Vinted website."""
    return [(k, v) for k, v in parse_qsl(urlparse(url).query)
            if v != "" and k not in _IGNORED_URL_PARAMS]


class VintedClient:
    def __init__(self, domain: str = "www.vinted.it", timeout: float = 20.0,
                 max_retries: int = 3, session: requests.Session | None = None):
        self.base = f"https://{domain}"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        })
        self._has_cookie = False

    def _refresh_session(self) -> None:
        """Visiting the homepage sets the anonymous session cookies."""
        self.session.cookies.clear()
        resp = self.session.get(self.base + "/", timeout=self.timeout)
        if resp.status_code >= 400:
            raise VintedError(f"Impossibile aprire {self.base} (HTTP {resp.status_code})")
        self._has_cookie = True

    def search(self, params: list[tuple[str, str]], page: int = 1) -> list[Item]:
        """Newest-first search results (96 per page)."""
        query = [*params, ("order", "newest_first")]
        if page > 1:
            query.append(("page", str(page)))
        delay = 2.0
        for attempt in range(1, self.max_retries + 1):
            if not self._has_cookie:
                self._refresh_session()
            resp = self.session.get(self.base + "/catalog", params=query, timeout=self.timeout)
            if resp.status_code == 200:
                items = parse_catalog_html(resp.text, self.base)
                if items:
                    return items
                if "product-item-id-" in resp.text:
                    raise VintedError("Annunci presenti ma non leggibili: il sito potrebbe "
                                      "essere cambiato")
                # No cards at all: either truly no results or a transient soft block.
                if attempt == self.max_retries:
                    return []
                log.info("Pagina senza annunci, rinnovo la sessione e riprovo")
                self._has_cookie = False
            elif resp.status_code in (401, 403):
                log.info("Sessione Vinted scaduta (HTTP %s), la rinnovo", resp.status_code)
                self._has_cookie = False
            elif resp.status_code == 429 or resp.status_code >= 500:
                log.warning("Vinted HTTP %s, riprovo tra %.0fs", resp.status_code, delay)
            else:
                raise VintedError(f"Ricerca fallita: HTTP {resp.status_code}")
            if attempt < self.max_retries:
                time.sleep(delay)
                delay *= 2
        raise VintedError(f"Ricerca fallita dopo {self.max_retries} tentativi")
