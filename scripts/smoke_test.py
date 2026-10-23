"""Live check against Vinted: parse a real catalog page and run one full scan."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vinted_alerts.cli import main  # noqa: E402
from vinted_alerts.client import VintedClient  # noqa: E402

items = VintedClient().search([("search_text", "nike dunk")])
print(f"{len(items)} articoli letti")
for it in items[:10]:
    print(f"- {it.id} | {it.title} | {it.brand} | {it.size} | {it.condition} | "
          f"{it.price} -> {it.total_price} {it.currency} | {it.url} | {it.photo_url[:50]}")
assert len(items) >= 50, "troppi pochi annunci: parsing rotto?"
assert all(i.total_price >= i.price > 0 for i in items)
assert sum(bool(i.brand) for i in items) > len(items) / 2

# Full pipeline: bootstrap prices, then a scan with an always-hit target.
with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp, "config.toml")
    cfg.write_text(f"""
[general]
db_path = "{tmp}/test.db"
bootstrap_pages = 2

[[watch]]
name = "smoke"
query = "nike dunk"
below_average_pct = 40
min_samples = 20
""")
    assert main(["once", "-c", str(cfg)]) == 0
    assert main(["stats", "-c", str(cfg)]) == 0
print("SMOKE TEST OK")
