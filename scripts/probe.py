"""Diagnostics: find which Vinted catalog endpoint currently answers."""

import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"})

home = s.get("https://www.vinted.it/")
print("HOME", home.status_code, home.url, "cookies:", list(s.cookies.keys()))
paths = sorted(set(re.findall(r'["\'](/(?:web/)?api/[A-Za-z0-9_/\-]+)', home.text)))
print("API paths in homepage:", paths[:60])

cat = s.get("https://www.vinted.it/catalog?search_text=nike%20dunk")
print("CATALOG PAGE", cat.status_code, len(cat.text))
paths = sorted(set(re.findall(r'(/(?:web/)?api/[A-Za-z0-9_/\-]+)', cat.text)))
print("API paths in catalog page:", paths[:60])
m = re.search(r'.{200}"price".{300}', cat.text)
print("price snippet:", m.group(0) if m else None)

candidates = [
    "/api/v2/catalog/items",
    "/api/v2/items",
    "/web/api/core/catalog/items",
    "/api/v2/catalog/items/search",
]
for p in candidates:
    for accept in ("application/json, text/plain, */*",):
        r = s.get("https://www.vinted.it" + p, headers={"Accept": accept},
                  params={"search_text": "nike dunk", "per_page": 3, "order": "newest_first"})
        print("TRY", p, r.status_code, r.headers.get("content-type"), r.text[:300].replace("\n", " "))
