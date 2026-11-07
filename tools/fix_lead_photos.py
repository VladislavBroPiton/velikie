"""Второй проход: ставит главный портрет статьи первым фото тем, у кого его нет в photos_new.json.

Запускать после fetch_new_photos.py (не одновременно).
"""
import io, json, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "VelikieApp/1.0 (personal PWA)"}
OUT = ROOT / "tools/photos_new.json"


def get(url):
    for a in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            time.sleep(15 * (a + 1))
    raise RuntimeError("429 не прошёл")


def api(host, params):
    params = {**params, "format": "json", "formatversion": 2}
    return json.loads(get(f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)))


lists = json.loads((ROOT / "tools/new_people.json").read_text("utf-8"))
done = json.loads(OUT.read_text("utf-8"))
for pid, title in [x for v in lists.values() for x in v]:
    photos = done.get(pid, [])
    p = api("en.wikipedia.org", {"action": "query", "titles": title, "redirects": 1,
                                 "prop": "pageimages", "piprop": "name"})["query"]["pages"][0]
    lead = p.get("pageimage")
    if not lead or any(ph.get("file", "").replace(" ", "_") == lead for ph in photos):
        continue
    ii = api("commons.wikimedia.org", {"action": "query", "titles": "File:" + lead, "prop": "imageinfo",
                                       "iiprop": "url|extmetadata", "iiurlwidth": 960})["query"]["pages"][0]
    if "imageinfo" not in ii:  # файл лежит в самой Википедии, а не на Commons — лицензия не свободная
        print(pid, "портрет не на Commons, пропуск", flush=True)
        continue
    ii = ii["imageinfo"][0]
    # сдвигаем имеющиеся файлы, портрет становится первым; держим максимум 3
    photos = photos[:2]
    for k in range(len(photos), 0, -1):
        src, dst = ROOT / f"photos/{pid}-{k}.jpg", ROOT / f"photos/{pid}-{k + 1}.jpg"
        if dst.exists():
            dst.unlink()
        src.rename(dst)
        photos[k - 1]["src"] = f"photos/{dst.name}"
    im = Image.open(io.BytesIO(get(ii["thumburl"]))).convert("RGB")
    im.thumbnail((960, 1300))
    im.save(ROOT / f"photos/{pid}-1.jpg", "JPEG", quality=80, optimize=True, progressive=True)
    photos.insert(0, {"src": f"photos/{pid}-1.jpg", "page": ii["descriptionurl"], "file": lead.replace("_", " "),
                      "license": ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")})
    for extra in ROOT.glob(f"photos/{pid}-4.jpg"):
        extra.unlink()
    done[pid] = photos
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), "utf-8")
    print(pid, "портрет добавлен", len(photos), flush=True)
    time.sleep(2)
print("ГОТОВО", flush=True)
