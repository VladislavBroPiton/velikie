"""Фото для новых людей: портрет из статьи Википедии + до 2 снимков с фамилией в имени файла.
Повторный запуск докачивает недостающее. Итог — tools/photos_new.json."""
import io, json, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "VelikieApp/1.0 (personal PWA)"}
OUT = ROOT / "tools/photos_new_2.json"
BAD = ("signature", "logo", "flag", "icon", "map", "symbol", "seal", "emblem", "stamp", "coin",
       "grave", "tomb", "plaque", "statue", "monument", "memorial", "house", "museum", "birthplace",
       "poster", "cover", "autograph", "star", "bust", "sculpture", "banknote", "mural")

def get(url):
    """При ограничении частоты ждём столько, сколько просит сервер, но не бесконечно:
    после трёх попыток человека пропускаем — доберём его повторным запуском."""
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503): raise
            wait = e.headers.get("Retry-After")
            time.sleep(min(int(wait), 60) if (wait or "").isdigit() else 20 * (a + 1))
    raise RuntimeError("ограничение частоты")

def api(params, host="en.wikipedia.org"):
    params = {**params, "format": "json", "formatversion": 2}
    return json.loads(get(f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)))

def norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))

def pick(title):
    d = api({"action": "query", "titles": title, "redirects": 1, "prop": "pageimages", "piprop": "name"})
    lead = d["query"]["pages"][0].get("pageimage")
    d = api({"action": "query", "titles": title, "redirects": 1, "generator": "images", "gimlimit": 80,
             "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 960})
    pages = d.get("query", {}).get("pages", [])
    words = [w for w in norm(title).replace(".", " ").split() if len(w) > 2 and w not in ("the", "brothers", "jr")]
    key = words[-1] if words else ""
    if title == "Wright brothers": key = "wright"
    if title == "Michelangelo": key = "michelangelo"
    res = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        name = p["title"][5:]
        is_lead = lead and name.replace(" ", "_") == lead
        if not ii.get("thumburl") or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if not is_lead:
            n = norm(name)
            if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 400 or key not in n or any(b in n for b in BAD):
                continue
        res.append({"file": name, "thumb": ii["thumburl"], "page": ii["descriptionurl"], "lead": bool(is_lead),
                    "license": ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")})
    res.sort(key=lambda x: not x["lead"])
    return res[:3]

lists = json.loads((ROOT / "tools/new_people_2.json").read_text("utf-8"))
done = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {}
for pid, title in [x for v in lists.values() for x in v]:
    if pid in done and all((ROOT / ph["src"]).exists() for ph in done[pid]) and done[pid]:
        continue
    try:
        cands = pick(title); photos = []
        for k, c in enumerate(cands, 1):
            dst = ROOT / f"photos/{pid}-{k}.jpg"
            if not dst.exists():
                im = Image.open(io.BytesIO(get(c["thumb"]))).convert("RGB")
                im.thumbnail((960, 1300))
                im.save(dst, "JPEG", quality=80, optimize=True, progressive=True)
                time.sleep(4)
            photos.append({"src": f"photos/{dst.name}", "page": c["page"], "license": c["license"], "file": c["file"]})
        done[pid] = photos
        print(pid, len(photos), flush=True)
    except Exception as e:
        print(pid, "ОШИБКА", e, flush=True)
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), "utf-8")
    time.sleep(5)
print("ГОТОВО", flush=True)
