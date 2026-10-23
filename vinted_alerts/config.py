"""Load the TOML config describing watches (searches) and notifiers."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .client import params_from_search_url

# Friendly config keys -> Vinted API params.
_PARAM_KEYS = {
    "query": "search_text",
    "catalog_ids": "catalog_ids",
    "brand_ids": "brand_ids",
    "size_ids": "size_ids",
    "status_ids": "status_ids",
    "color_ids": "color_ids",
    "material_ids": "material_ids",
}


@dataclass
class Watch:
    name: str
    params: dict[str, str]
    target_price: float | None = None    # alert when total price <= this
    below_average_pct: float | None = None  # alert when price is X% under the median
    min_samples: int = 20                # prices needed before trusting the median
    min_price: float = 0.0               # ignore listings cheaper than this (often fakes/accessories)
    include_words: list[str] = field(default_factory=list)  # title must contain all of these
    exclude_words: list[str] = field(default_factory=list)  # title must contain none of these


@dataclass
class Config:
    watches: list[Watch]
    domain: str = "www.vinted.it"
    interval: int = 60          # seconds between scans
    pages_per_scan: int = 1
    bootstrap_pages: int = 3    # pages fetched on first run to learn average prices
    use_total_price: bool = True  # compare prices including buyer protection fee
    db_path: str = "vinted_alerts.db"
    telegram: dict | None = None
    discord: dict | None = None


def _ids(value) -> str:
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return str(value)


def _words(value) -> list[str]:
    return [w.lower() for w in (value or [])]


def parse_watch(raw: dict) -> Watch:
    if "name" not in raw:
        raise ValueError("Ogni [[watch]] deve avere un 'name'")
    params = params_from_search_url(raw["url"]) if raw.get("url") else {}
    for key, api_key in _PARAM_KEYS.items():
        if key in raw:
            params[api_key] = _ids(raw[key])
    # Prefilter on Vinted's side. Without below_average_pct we don't need a price
    # baseline, so target_price can narrow the search directly.
    if "max_price" in raw:
        params["price_to"] = str(raw["max_price"])
    elif "target_price" in raw and "below_average_pct" not in raw:
        params["price_to"] = str(raw["target_price"])
    if "min_price" in raw:
        params["price_from"] = str(raw["min_price"])
    if not params:
        raise ValueError(f"Watch '{raw['name']}': serve almeno 'query' o 'url'")
    watch = Watch(
        name=raw["name"],
        params=params,
        target_price=raw.get("target_price"),
        below_average_pct=raw.get("below_average_pct"),
        min_samples=int(raw.get("min_samples", 20)),
        min_price=float(raw.get("min_price", 0)),
        include_words=_words(raw.get("include_words")),
        exclude_words=_words(raw.get("exclude_words")),
    )
    if watch.target_price is None and watch.below_average_pct is None:
        raise ValueError(
            f"Watch '{watch.name}': imposta 'target_price' e/o 'below_average_pct'")
    return watch


def load_config(path: str | Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    watches = [parse_watch(w) for w in raw.get("watch", [])]
    if not watches:
        raise ValueError("Nessuna ricerca definita: aggiungi almeno un blocco [[watch]]")
    general = raw.get("general", {})
    return Config(
        watches=watches,
        domain=general.get("domain", "www.vinted.it"),
        interval=int(general.get("interval", 60)),
        pages_per_scan=int(general.get("pages_per_scan", 1)),
        bootstrap_pages=int(general.get("bootstrap_pages", 3)),
        use_total_price=bool(general.get("use_total_price", True)),
        db_path=general.get("db_path", "vinted_alerts.db"),
        telegram=raw.get("telegram"),
        discord=raw.get("discord"),
    )
