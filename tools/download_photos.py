"""Скачивает выбранные фото с Wikimedia Commons и прописывает их в data/people.json.

Использование: python tools/download_photos.py picks.json
picks.json: {"tyson": ["Файл1.jpg", "Файл2.jpg"], ...}
"""
import io, json, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "VelikieApp/1.0 (personal PWA)"}

def get(url):
    for a in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(10 * (a + 1))
    raise RuntimeError("429")

def info(files):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "titles": "|".join("File:" + f for f in files), "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 960, "format": "json"})
    d = json.loads(get(u)); res = {}
    norm = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
    for p in d["query"]["pages"].values():
        ii = p["imageinfo"][0]
        res[norm.get(p["title"], p["title"])[5:]] = {
            "thumb": ii["thumburl"], "page": ii["descriptionurl"],
            "license": ii["extmetadata"].get("LicenseShortName", {}).get("value", "")}
    return res

picks = json.loads(Path(sys.argv[1]).read_text("utf-8"))
people = json.loads((ROOT / "data/people.json").read_text("utf-8"))
(ROOT / "photos").mkdir(exist_ok=True)
for person in people:
    files = picks.get(person["id"])
    if not files: continue
    meta = info(files); photos = []
    for k, f in enumerate(files, 1):
        m = meta[f]; dst = ROOT / f"photos/{person['id']}-{k}.jpg"
        if not dst.exists():
            im = Image.open(io.BytesIO(get(m["thumb"]))).convert("RGB")
            im.thumbnail((1000, 1300))
            im.save(dst, "JPEG", quality=80, optimize=True, progressive=True)
            time.sleep(1)
        photos.append({"src": f"photos/{dst.name}", "page": m["page"], "license": m["license"]})
    person["photos"] = photos
    print(person["id"], len(photos), flush=True)
    (ROOT / "data/people.json").write_text(json.dumps(people, ensure_ascii=False, indent=1), "utf-8")
