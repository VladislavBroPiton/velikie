"""Собирает data/people.json: первые 15 историй + новые из data/new_*.json с фото из tools/photos_new.json.

Новые люди перемешиваются с фиксированным зерном так, чтобы рубрики чередовались день ото дня.
Люди без фото пропускаются (выводится список).
"""
import json, random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
people = json.loads((ROOT / "data/people.json").read_text("utf-8"))
base = [p for p in people if p["id"] in {
    "tyson", "ali", "jackson", "ford", "ferrari", "jobs", "brucelee", "arnold", "chanel",
    "gagarin", "pele", "disney", "edison", "jordan", "honda"}]
photos = json.loads((ROOT / "tools/photos_new.json").read_text("utf-8"))

new, missing = [], []
for n in "12345":
    for p in json.loads((ROOT / f"data/new_{n}.json").read_text("utf-8")):
        ph = [{k: v for k, v in x.items() if k != "file"} for x in photos.get(p["id"], [])
              if (ROOT / x["src"]).exists()]
        if not ph:
            missing.append(p["id"]); continue
        p["photos"] = ph
        new.append(p)

# чередование рубрик: по кругу берём из каждой рубрики по одному
rng = random.Random(150)
groups = defaultdict(list)
for p in new:
    groups[p["field"]].append(p)
for g in groups.values():
    rng.shuffle(g)
# равномерно распределяем каждую рубрику по всей очереди (большие рубрики не скапливаются в конце)
order = sorted((p for g in groups.values() for p in g),
               key=lambda p: (groups[p["field"]].index(p) + rng.random() * 0.8) / len(groups[p["field"]]))

result = base + order
assert len({p["id"] for p in result}) == len(result)
(ROOT / "data/people.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), "utf-8")
print("всего:", len(result), "| без фото:", missing)
