"""Diagnostics: dump the structure of item cards on Vinted's catalog page."""

import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
BASE = "https://www.vinted.it"
s = requests.Session()
s.headers.update({"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"})
s.get(BASE + "/")

for url in (BASE + "/catalog?search_text=nike%20dunk&order=newest_first",
            BASE + "/catalog?search_text=nike+dunk&order=newest_first",
            BASE + "/catalog?search_text=nike%20dunk&order=newest_first&page=1"):
    r = s.get(url)
    title = re.search(r"<title>(.*?)</title>", r.text)
    print("VARIANT", url, r.status_code, len(r.text), title.group(1) if title else None,
          r.text.count("product-item-id-"))

for page_no in (1, 2):
    url = BASE + "/catalog?search_text=nike%20dunk&order=newest_first"
    if page_no > 1:
        url += f"&page={page_no}"
    resp = s.get(url)
    html = resp.text
    print("STATUS", resp.status_code, len(html), resp.url)
    ids = list(dict.fromkeys(re.findall(r'product-item-id-(\d+)', html)))
    print(f"PAGE {page_no}: {len(ids)} items, first ids {ids[:5]}")
    if page_no == 1 and ids:
        alts = re.findall(r'alt="([^"]*€[^"]*)"', html)
        for a in alts[:15]:
            print("ALT", a)
        start = html.find("product-item-id-" + ids[0])
        card_start = html.rfind("<div", 0, start - 1500)
        print("CARD", html[start - 1500:start + 3500])
        # Is the item data also embedded as JSON (RSC payload)?
        for needle in (ids[0] + '\\\\",', '\\"id\\":' + ids[0], '"id":' + ids[0], ids[0]):
            print("JSON?", repr(needle), html.count(needle))
        idx = html.find('\\"id\\":' + ids[0])
        if idx >= 0:
            print("RSC", html[idx - 300: idx + 2000])

# Filters from website URLs: price_to / catalog[] / brand_ids[]
r = s.get(BASE + "/catalog?search_text=nike%20dunk&price_to=30&currency=EUR&order=newest_first")
print("PRICE_TO", re.findall(r'alt="[^"]*?(\d+[.,]\d+) €, (\d+[.,]\d+) €"', r.text)[:20])
