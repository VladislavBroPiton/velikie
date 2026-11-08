"""Годы жизни и место рождения новых героев — из Wikidata.

Берёт список tools/new_people_2.json, по названию статьи находит элемент Wikidata,
достаёт дату рождения (P569), смерти (P570) и место рождения (P19) с координатами.
Координаты пересчитывает в точку на data/map.svg (viewBox 1000×500, широты от 78°N до 56°S).

Итог — tools/meta_new.json: {id: {years, place, x, y, born, died}}
"""
import json, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "VelikieApp/1.0 (personal PWA)"}
OUT = ROOT / "tools/meta_new.json"


def get(url):
    for a in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(5 * (a + 1))
    raise RuntimeError("не отвечает: " + url[:90])


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def qids(titles):
    """название статьи -> Q-идентификатор"""
    out = {}
    for part in chunks(titles, 40):
        d = get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "titles": "|".join(part), "redirects": 1,
            "prop": "pageprops", "ppprop": "wikibase_item", "format": "json", "formatversion": 2}))
        norm = {n["to"]: n["from"] for n in d["query"].get("normalized", [])}
        norm.update({r["to"]: r["from"] for r in d["query"].get("redirects", [])})
        for p in d["query"]["pages"]:
            q = (p.get("pageprops") or {}).get("wikibase_item")
            t = p["title"]
            while t in norm:                     # разворачиваем цепочку перенаправлений
                t = norm[t]
            if q:
                out[t] = q
        time.sleep(0.4)
    return out


def entities(ids, props="claims|labels"):
    out = {}
    for part in chunks(ids, 40):
        d = get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(part), "props": props,
            "languages": "ru|en", "format": "json"}))
        out.update(d.get("entities", {}))
        time.sleep(0.4)
    return out


def claim(ent, prop):
    c = (ent.get("claims") or {}).get(prop) or []
    for x in c:
        v = (x.get("mainsnak") or {}).get("datavalue")
        if v:
            return v["value"]
    return None


def year(val):
    if not val:
        return None
    t = val.get("time", "")                       # вид: +1835-07-25T00:00:00Z
    sign, body = t[0], t[1:]
    y = int(body.split("-")[0])
    return -y if sign == "-" else y


def to_map(lat, lon):
    """долгота -> x, широта -> y на карте 1000×500 (обрезана: 78°N … 56°S)"""
    return round((lon + 180) * 1000 / 360, 1), round((78 - lat) * 500 / 134, 1)


lists = json.loads((ROOT / "tools/new_people_2.json").read_text("utf-8"))
pairs = [x for v in lists.values() for x in v]
title2id = {t: i for i, t in pairs}

q = qids([t for _, t in pairs])
print("нашлось элементов:", len(q), "из", len(pairs), flush=True)

ents = entities(sorted(set(q.values())))
places = set()
raw = {}
for title, qid in q.items():
    e = ents.get(qid) or {}
    b, d = year(claim(e, "P569")), year(claim(e, "P570"))
    pl = claim(e, "P19")
    pq = pl.get("id") if isinstance(pl, dict) else None
    if pq:
        places.add(pq)
    raw[title2id[title]] = {"born": b, "died": d, "place_q": pq}

pl_ents = entities(sorted(places))
pl_info = {}
for pq, e in pl_ents.items():
    coord = claim(e, "P625")
    lab = (e.get("labels") or {})
    name = (lab.get("ru") or lab.get("en") or {}).get("value")
    if coord and name:
        x, y = to_map(coord["latitude"], coord["longitude"])
        pl_info[pq] = {"place": name, "x": x, "y": y}

res = {}
for pid, v in raw.items():
    b, d = v["born"], v["died"]
    if b is None:
        years = ""
    elif d is None:
        years = "род. %d" % b
    else:
        years = "%d–%d" % (b, d)                  # тире длинное, как в людях
    item = {"years": years, "born": b, "died": d}
    item.update(pl_info.get(v["place_q"]) or {})
    res[pid] = item

OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
no_place = [k for k, v in res.items() if "x" not in v]
no_years = [k for k, v in res.items() if not v["years"]]
print("готово:", len(res), "| без места:", len(no_place), "| без дат:", len(no_years), flush=True)
if no_place:
    print("без места:", " ".join(no_place), flush=True)
if no_years:
    print("без дат:", " ".join(no_years), flush=True)
