"""Minimal client for Vinted's (unofficial) web catalog API."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse

import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

# Vinted's website uses e.g. `catalog[]=5&brand_ids[]=53`; the API wants
# `catalog_ids=5&brand_ids=53` (comma separated for multiple values).
_URL_PARAM_ALIASES = {"catalog": "catalog_ids"}
_IGNORED_URL_PARAMS = {"time", "search_id", "page", "disabled_personalization"}


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
    seller: str = ""

    @classmethod
    def from_api(cls, data: dict) -> "Item":
        price, currency = _parse_price(data.get("price"), data.get("currency"))
        total, _ = _parse_price(data.get("total_item_price"), currency)
        photo = data.get("photo") or {}
        user = data.get("user") or {}
        return cls(
            id=int(data["id"]),
            title=data.get("title") or "",
            price=price,
            total_price=total or price,
            currency=currency or "EUR",
            url=data.get("url") or "",
            brand=data.get("brand_title") or "",
            size=data.get("size_title") or "",
            condition=data.get("status") or "",
            photo_url=photo.get("url") or "",
            seller=user.get("login") or "",
        )


def _parse_price(value, currency=None) -> tuple[float, str | None]:
    """Vinted returns prices either as "12.5" or {"amount": "12.5", "currency_code": "EUR"}."""
    if value is None:
        return 0.0, currency
    if isinstance(value, dict):
        return float(value.get("amount") or 0), value.get("currency_code") or currency
    return float(value), currency


def params_from_search_url(url: str) -> dict[str, str]:
    """Turn a search URL copied from the Vinted website into API query params."""
    grouped: dict[str, list[str]] = {}
    for key, value in parse_qsl(urlparse(url).query):
        key = key.removesuffix("[]")
        key = _URL_PARAM_ALIASES.get(key, key)
        if key in _IGNORED_URL_PARAMS or value == "":
            continue
        grouped.setdefault(key, []).append(value)
    return {k: ",".join(v) for k, v in grouped.items()}


class VintedClient:
    def __init__(self, domain: str = "www.vinted.it", timeout: float = 15.0,
                 max_retries: int = 3, session: requests.Session | None = None):
        self.base = f"https://{domain}"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        })
        self._has_cookie = False

    def _refresh_session(self) -> None:
        """Visiting the homepage sets the anonymous `access_token_web` cookie the API needs."""
        self.session.cookies.clear()
        resp = self.session.get(self.base + "/", timeout=self.timeout)
        if resp.status_code >= 400:
            raise VintedError(f"Impossibile aprire {self.base} (HTTP {resp.status_code})")
        self._has_cookie = True

    def search(self, params: dict, per_page: int = 96, page: int = 1) -> list[Item]:
        query = {"order": "newest_first", **params, "per_page": per_page, "page": page}
        delay = 2.0
        for attempt in range(1, self.max_retries + 1):
            if not self._has_cookie:
                self._refresh_session()
            resp = self.session.get(self.base + "/api/v2/catalog/items",
                                    params=query, timeout=self.timeout)
            if resp.status_code == 200:
                return [Item.from_api(d) for d in resp.json().get("items", [])]
            if resp.status_code in (401, 403):
                log.info("Sessione Vinted scaduta (HTTP %s), la rinnovo", resp.status_code)
                self._has_cookie = False
            elif resp.status_code == 429 or resp.status_code >= 500:
                log.warning("Vinted HTTP %s, riprovo tra %.0fs", resp.status_code, delay)
            else:
                raise VintedError(f"Ricerca fallita: HTTP {resp.status_code} {resp.text[:200]}")
            if attempt < self.max_retries:
                time.sleep(delay)
                delay *= 2
        raise VintedError(f"Ricerca fallita dopo {self.max_retries} tentativi")
