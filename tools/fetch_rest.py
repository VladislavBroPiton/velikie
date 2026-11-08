"""Добор фотографий для тех, кому не хватило при обычном проходе.

Ищет снимки прямо по Викискладу (а не по статье Википедии) и берёт первые подходящие.
Список берёт из tools/missing.json, результат дописывает в tools/photos_new_2.json.
"""
import io, json, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "VelikieApp/1.0 (personal PWA)"}
OUT = ROOT / "tools/photos_new_2.json"
BAD = ("signature", "logo", "flag", "icon", "map", "symbol", "seal", "emblem", "stamp", "coin",
       "grave", "tomb", "plaque", "statue", "monument", "memorial", "house", "museum", "birthplace",
       "poster", "cover", "autograph", "star", "bust", "sculpture", "banknote", "mural", "diagram",
       "chart", "building", "factory", "street", "church", "award", "medal")

# что искать для каждого: запрос и слово, которое должно быть в имени файла
QUERY = {
    "faraday":   ("Michael Faraday portrait", "faraday"),
    "fermi":     ("Enrico Fermi", "fermi"),
    "aldrin":    ("Buzz Aldrin astronaut", "aldrin"),
    "shepard":   ("Alan Shepard astronaut", "shepard"),
    "boeing":    ("William E. Boeing", "boeing"),
    "jpmorgan":  ("J.P. Morgan financier portrait", "morgan"),
    "ohno":      ("Taiichi Ohno", "ohno"),
    "ortega":    ("Amancio Ortega", "ortega"),
    "ysl":       ("Yves Saint Laurent designer", "laurent"),
    "marykay":   ("Mary Kay Ash businesswoman", "kay"),
}


def get(url):
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            time.sleep(20 * (a + 1))
    raise RuntimeError("не отвечает")


def api(params):
    params = {**params, "format": "json", "formatversion": 2}
    return json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)))


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))


def find(query, key, limit=3):
    d = api({"action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": 6,
             "gsrlimit": 40, "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata",
             "iiurlwidth": 960})
    out = []
    for p in d.get("query", {}).get("pages", []):
        ii = (p.get("imageinfo") or [{}])[0]
        name = p["title"][5:]
        n = norm(name)
        if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 400:
            continue
        if key not in n or any(b in n for b in BAD):
            continue
        out.append({"file": name, "thumb": ii["thumburl"], "page": ii["descriptionurl"],
                    "license": ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")})
        if len(out) >= limit:
            break
    return out


done = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {}
missing = json.loads((ROOT / "tools/missing.json").read_text("utf-8"))

for pid in missing:
    if pid not in QUERY:
        print(pid, "— нет запроса", flush=True)
        continue
    query, key = QUERY[pid]
    try:
        cands = find(query, key)
        photos = []
        for k, c in enumerate(cands, 1):
            dst = ROOT / f"photos/{pid}-{k}.jpg"
            if not dst.exists():
                im = Image.open(io.BytesIO(get(c["thumb"]))).convert("RGB")
                im.thumbnail((960, 1300))
                im.save(dst, "JPEG", quality=80, optimize=True, progressive=True)
                time.sleep(3)
            photos.append({"src": f"photos/{dst.name}", "page": c["page"],
                           "license": c["license"], "file": c["file"]})
        if photos:
            done[pid] = photos
        print(pid, len(photos), flush=True)
    except Exception as e:
        print(pid, "ОШИБКА", e, flush=True)
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), "utf-8")
    time.sleep(4)
print("ГОТОВО", flush=True)
