"""Decide whether a listing is a deal worth alerting on."""

from __future__ import annotations

from dataclasses import dataclass

from .client import Item
from .config import Watch


@dataclass
class Deal:
    item: Item
    price: float
    reasons: list[str]
    median: float | None = None

    @property
    def discount_pct(self) -> float | None:
        if not self.median:
            return None
        return (1 - self.price / self.median) * 100


def matches_filters(watch: Watch, item: Item) -> bool:
    title = item.title.lower()
    # "gold|oro" means either word is fine.
    if any(not any(alt in title for alt in w.split("|")) for w in watch.include_words):
        return False
    if any(w in title for w in watch.exclude_words):
        return False
    return True


def evaluate(watch: Watch, item: Item, price: float,
             median: float | None, samples: int) -> Deal | None:
    if price < watch.min_price:
        return None
    reasons = []
    if watch.target_price is not None and price <= watch.target_price:
        reasons.append(f"prezzo ≤ target {watch.target_price:.2f}")
    if (watch.below_average_pct is not None and median
            and samples >= watch.min_samples
            and price <= median * (1 - watch.below_average_pct / 100)):
        reasons.append(f"{(1 - price / median) * 100:.0f}% sotto la mediana ({median:.2f})")
    if not reasons:
        return None
    return Deal(item=item, price=price, reasons=reasons, median=median)
