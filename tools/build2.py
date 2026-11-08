"""Добавляет новых героев из data/new2_*.json в данные приложения.

Берёт тексты из new2_*.json, годы и место рождения из tools/meta_new.json,
фотографии из tools/photos_new_2.json. Раскладывает по четырём файлам:
people.json (карточка), extra.json (лента лет), facts.json (цифры), world.json (точка на карте).

Люди без скачанных фотографий пропускаются и выводятся списком.
Новые перемешиваются с чередованием рубрик, чтобы дни не шли подряд одной темой.
Запуск повторно безопасен: уже добавленные обновляются на месте.
"""
import json, random, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"


def load(p, default=None):
    f = Path(p)
    return json.loads(f.read_text("utf-8")) if f.exists() else default


def save(p, obj):
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1), "utf-8")


meta = load(ROOT / "tools/meta_new.json", {})
photos = load(ROOT / "tools/photos_new_2.json", {})
people = load(D / "people.json", [])
extra = load(D / "extra.json", {})
facts = load(D / "facts.json", {})
world = load(D / "world.json", {})

batches = sorted(D.glob("new2_*.json"), key=lambda f: int(f.stem.split("_")[1]))
fresh, no_photo, no_meta = [], [], []
for b in batches:
    for p in load(b):
        pid = p["id"]
        m = meta.get(pid)
        ph = [{k: v for k, v in x.items() if k != "file"} for x in photos.get(pid, [])
              if (ROOT / x["src"]).exists()]
        if not m:
            no_meta.append(pid); continue
        if not ph:
            no_photo.append(pid); continue
        card = {"id": pid, "name": p["name"], "years": m["years"], "field": p["field"],
                "role": p["role"], "teaser": p["teaser"], "story": p["story"],
                "quotes": p["quotes"], "lesson": p["lesson"], "photos": ph}
        fresh.append(card)
        extra[pid] = {"timeline": p["timeline"], "highlight": p["highlight"]}
        facts[pid] = p["facts"]
        if "x" in m:
            world[pid] = {"place": m["place"], "x": m["x"], "y": m["y"]}

# уже добавленных обновляем на месте, остальных ставим в конец вперемешку по рубрикам
known = {p["id"]: i for i, p in enumerate(people)}
add = []
for c in fresh:
    if c["id"] in known:
        people[known[c["id"]]] = c
    else:
        add.append(c)

groups = defaultdict(list)
for c in add:
    groups[c["field"]].append(c)
rng = random.Random(360)
for g in groups.values():
    rng.shuffle(g)
mixed, keys = [], sorted(groups, key=lambda k: -len(groups[k]))
while any(groups[k] for k in keys):
    for k in keys:
        if groups[k]:
            mixed.append(groups[k].pop())
people += mixed

save(D / "people.json", people)
save(D / "extra.json", extra)
save(D / "facts.json", facts)
save(D / "world.json", world)

print("в приложении теперь:", len(people), flush=True)
print("добавлено новых:", len(mixed), "| обновлено:", len(fresh) - len(mixed), flush=True)
if no_photo:
    print("без фото (пропущены):", " ".join(no_photo), flush=True)
if no_meta:
    print("без дат (пропущены):", " ".join(no_meta), flush=True)
