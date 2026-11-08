"""Выкладывает изменённые и новые файлы проекта в VladislavBroPiton/velikie.

Идёт через Git Data API: каждый файл заливается blob'ом, затем собирается одно дерево,
коммит и перевод веток main и gh-pages (сайт отдаётся именно из gh-pages).
Прогресс печатает по ходу, чтобы было видно, что процесс жив.
"""
import base64, io, json, os, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

REPO = "VladislavBroPiton/velikie"
ROOT = Path(__file__).resolve().parent.parent
MSG = sys.argv[1] if len(sys.argv) > 1 else "обновление"

tok = ""
for line in io.open(r"C:\MyPythonProjects\Мои проекты\_монитор\.env", encoding="utf-8"):
    if line.startswith("GITHUB_TOKEN_1"):
        tok = line.split("=", 1)[1].strip()
if not tok:
    raise SystemExit("нет токена")


def api(path, data=None, method=None, tries=4):
    url = "https://api.github.com/repos/" + REPO + path
    body = json.dumps(data).encode() if data is not None else None
    for a in range(tries):
        req = urllib.request.Request(url, data=body, method=method or ("POST" if data else "GET"))
        req.add_header("Authorization", "Bearer " + tok)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "velikie-deploy")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            code = getattr(e, "code", 0)
            if code and code not in (403, 429, 500, 502, 503):
                raise
            time.sleep(10 * (a + 1))
    raise RuntimeError("не удалось: " + path)


# какие файлы изменились или появились — спрашиваем у git
out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
                     encoding="utf-8").stdout
files = []
for line in out.splitlines():
    st, name = line[:2].strip(), line[3:].strip().strip('"')
    if st == "D":
        continue
    if name.startswith("tools/") and not name.endswith(".py"):
        continue                                   # логи и промежуточные списки не выкладываем
    p = ROOT / name
    if p.is_file():
        files.append(name)

print("файлов к выкладке:", len(files), flush=True)

head = api("/git/ref/heads/main")["object"]["sha"]
base_tree = api("/git/commits/" + head)["tree"]["sha"]

tree = []
for i, name in enumerate(files, 1):
    raw = (ROOT / name).read_bytes()
    if name == "index.html" and len(raw) < 50000:
        raise SystemExit("index.html подозрительно мал")
    sha = api("/git/blobs", {"content": base64.b64encode(raw).decode(), "encoding": "base64"})["sha"]
    tree.append({"path": name.replace("\\", "/"), "mode": "100644", "type": "blob", "sha": sha})
    if i % 25 == 0 or i == len(files):
        print("  залито", i, "из", len(files), flush=True)

new_tree = api("/git/trees", {"base_tree": base_tree, "tree": tree})["sha"]
commit = api("/git/commits", {"message": MSG, "tree": new_tree, "parents": [head]})["sha"]
api("/git/refs/heads/main", {"sha": commit}, method="PATCH")
api("/git/refs/heads/gh-pages", {"sha": commit}, method="PATCH")
print("коммит", commit[:10], "выложен в main и gh-pages", flush=True)
