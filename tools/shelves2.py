"""Пополняет подборки на главной и добавляет новые.

Берёт people.json как источник правды: id, которых там нет, молча отбрасываются,
поэтому запускать можно в любой момент — после догрузки людей просто запустить снова.
"""
import json, io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"

people = {p["id"] for p in json.loads((D / "people.json").read_text("utf-8"))}

# что дописать в существующие подборки
ADD = {
    "Начинали с нуля": "faraday dickens jacklondon hokusai repin levitan gucci chungjuyung ambani "
                       "ortega kamprad vanderbilt gillette andersen ramanujan tsiolkovsky mittal "
                       "esteelauder michaeldell grove",
    "Пробились после 40": "dior gucci westwood marykay hokusai cezanne flwright morganfreeman "
                          "leebyungchul lindgren cervantes matisse kandinsky boeing deming",
    "Наши": "gogol bulgakov lermontov turgenev yesenin mayakovsky akhmatova tsvetaeva solzhenitsyn "
            "pasternak sholokhov repin shishkin serov vrubel levitan kandinsky malevich faberge "
            "tsiolkovsky vernadsky kapitsa landau sakharov lobachevsky perelman pirogov ilizarov "
            "fyodorov botkin mechnikov przhevalsky miklukho bellingshausen chkalov titov tupolev "
            "kutuzov nakhimov ushakov zhukov rokossovsky nevsky donskoy stolypin witte tarkovsky "
            "ranevskaya gaidai rachmaninoff shostakovich",
    "Изобретатели и инженеры": "benz daimler citroen eiffel gaudi corbusier flwright boeing tupolev "
                               "nobel dyson noyce gordonmoore hewlett ohno piccard maxwell faraday "
                               "shannon lovelace hopper",
    "Не сломались": "goya renoir matisse fdr euler vrubel malala rosaparks shepard munch "
                    "rokossovsky solzhenitsyn akhmatova ilizarov fyodorov",
}

# новые подборки
NEW = [
    ("Признали слишком поздно",
     "botticelli caravaggio cezanne vangogh tsiolkovsky lobachevsky deming bach vivaldi kafka "
     "tsvetaeva pasternak bulgakov semmelweis busterkeaton escher mendeleev ramanujan noether"),
    ("Работали вопреки болезни",
     "renoir matisse goya beethoven hawking fdr euler vrubel levitan tsiolkovsky monet degas "
     "chopin vivaldi shepard hopkins kurosawa scorsese"),
    ("Сменили дело в зрелости",
     "kandinsky vanderbilt matisse boeing leebyungchul morganfreeman westwood dior lindgren "
     "cervantes gucci marykay harrisonford deming nobel"),
    ("Начинали в гараже и сарае",
     "hewlett larrypage brin jobs wozniak dyson ibuka daimler benz boeing michaeldell "
     "noyce gillette heinz"),
]

shelves = json.loads((D / "shelves.json").read_text("utf-8"))
known = {s["title"]: s for s in shelves}

for title, ids in ADD.items():
    if title not in known:
        continue
    cur = known[title]["ids"]
    for pid in ids.split():
        if pid in people and pid not in cur:
            cur.append(pid)

for title, ids in NEW:
    if title in known:
        continue
    got = [pid for pid in ids.split() if pid in people]
    if len(got) >= 6:
        shelves.append({"title": title, "ids": got})

# подчищаем id, которых больше нет в приложении
for s in shelves:
    s["ids"] = [pid for pid in s["ids"] if pid in people]

(D / "shelves.json").write_text(json.dumps(shelves, ensure_ascii=False, indent=1), "utf-8")
for s in shelves:
    print(s["title"], "—", len(s["ids"]), "историй")
