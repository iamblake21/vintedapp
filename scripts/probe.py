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
for needle in ("nike", "Nike", "€", "amount", "currency_code", "photo"):
    idx = page.find(needle)
    print(f"PAGE {needle!r}: count={page.count(needle)}",
          repr(page[max(0, idx - 200): idx + 200]) if idx >= 0 else "")

scripts = sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', page)))
seen = set()
for src in scripts:
    js = s.get(urljoin(BASE, src), timeout=15).text
    for pat in (r'.{200}catalog/blocks.{200}', r'.{120}catalogItems.{120}',
                r'.{60}["`\'/]api/v\d.{100}', r'.{60}web/api.{100}', r'.{40}baseURL.{120}'):
        for m in re.finditer(pat, js):
            snippet = m.group(0)
            if snippet not in seen and len(seen) < 60:
                seen.add(snippet)
                print("JS", src.rsplit('/', 1)[-1], pat[:20], repr(snippet))

params = {"search_text": "nike dunk", "per_page": 3, "order": "newest_first"}
for p in ["/api/v2/catalog/blocks", "/web/api/core/catalog/blocks", "/catalog/blocks",
          "/api/v2/catalog/items?", "/web/api/core/catalog/items/search"]:
    r = s.get(BASE + p, params=params, headers={"Accept": "application/json"})
    print("TRY", p, r.status_code, r.headers.get("content-type"), r.text[:400].replace("\n", " "))
