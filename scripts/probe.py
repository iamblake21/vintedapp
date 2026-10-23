"""Diagnostics: find which Vinted catalog endpoint currently answers."""

import re
from urllib.parse import urljoin

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
BASE = "https://www.vinted.it"
s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"})
s.get(BASE + "/")

page = s.get(BASE + "/catalog?search_text=nike%20dunk&order=newest_first").text
for needle in ("catalog/items", "total_item_price", "__NEXT_DATA__", "/web/api", "api/v2",
               "self.__next_f", "item_box", "price_numeric"):
    idx = page.find(needle)
    print(f"NEEDLE {needle!r}: count={page.count(needle)}",
          repr(page[max(0, idx - 150): idx + 250]) if idx >= 0 else "")

scripts = sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', page)))
print("SCRIPTS", len(scripts))
endpoints = set()
for src in scripts[:80]:
    url = urljoin(BASE, src)
    try:
        js = s.get(url, timeout=15).text
    except Exception as e:
        print("ERR", url, e)
        continue
    for m in re.finditer(r'["`\'](/?(?:web/api/[a-z_\-]+/|api/v2/)?catalog[A-Za-z0-9_/\-${}.]*)["`\']', js):
        endpoints.add(m.group(1))
    for m in re.finditer(r'.{80}catalog/items.{120}', js):
        print("JS", src.rsplit('/', 1)[-1], repr(m.group(0)))
print("ENDPOINT STRINGS", sorted(endpoints)[:100])

for p in ["/web/api/core/catalog/items", "/web/api/catalog/items", "/api/v2/catalog/items"]:
    r = s.get(BASE + p, params={"search_text": "nike dunk", "per_page": 3, "order": "newest_first"},
              headers={"Accept": "application/json"})
    print("TRY", p, r.status_code, r.text[:300].replace("\n", " "))
