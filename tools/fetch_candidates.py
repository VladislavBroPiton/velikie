"""Собирает кандидатов-фото из статей Википедии (файлы Wikimedia Commons)."""
import json, sys, urllib.error, time, urllib.parse, urllib.request
from pathlib import Path

UA = {"User-Agent": "VelikieApp/1.0 (personal PWA)"}
PEOPLE = {
    "ali": "Muhammad Ali", "tyson": "Mike Tyson", "jackson": "Michael Jackson",
    "ford": "Henry Ford", "ferrari": "Enzo Ferrari", "jobs": "Steve Jobs",
    "brucelee": "Bruce Lee", "arnold": "Arnold Schwarzenegger",
    "chanel": "Coco Chanel", "gagarin": "Yuri Gagarin", "pele": "Pelé",
    "disney": "Walt Disney", "edison": "Thomas Edison",
    "jordan": "Michael Jordan", "honda": "Soichiro Honda",
}
BAD = ("signature", "logo", "flag", "icon", "map", "commons-", "wiki", "symbol",
       "star", "seal", "emblem", "stamp", "coin", "grave", "tomb", "plaque")

def api(params):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("429 не прошёл")

out = {}
for key, title in PEOPLE.items():
    lead = api({"action": "query", "titles": title, "prop": "pageimages",
                "piprop": "name", "format": "json", "redirects": 1})
    lead_name = next(iter(lead["query"]["pages"].values())).get("pageimage")
    d = api({"action": "query", "titles": title, "generator": "images", "gimlimit": 60,
             "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata",
             "iiurlwidth": 900, "format": "json", "redirects": 1})
    cands = []
    for p in d.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        name = p["title"].removeprefix("File:")
        if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 350:
            continue
        if any(b in name.lower() for b in BAD):
            continue
        meta = ii.get("extmetadata", {})
        cands.append({
            "file": name, "thumb": ii.get("thumburl"),
            "page": ii.get("descriptionurl"),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "lead": name.replace(" ", "_") == (lead_name or ""),
        })
    cands.sort(key=lambda c: not c["lead"])
    out[key] = cands
    print(key, len(cands), file=sys.stderr)
    time.sleep(3)

Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
