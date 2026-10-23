"""Quick live check that the Vinted catalog API answers our client."""

import sys

sys.path.insert(0, ".")
from vinted_alerts.client import VintedClient  # noqa: E402

client = VintedClient()
items = client.search({"search_text": "nike dunk"}, per_page=5)
print(f"OK: {len(items)} articoli")
for it in items:
    print(f"- {it.id} | {it.title} | {it.price} (totale {it.total_price}) {it.currency} | {it.url}")
sys.exit(0 if items else 1)
