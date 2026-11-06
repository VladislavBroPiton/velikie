"""Отправляет ежедневное push-уведомление о «человеке дня».

Запускается GitHub Actions по расписанию. Секреты:
  VAPID_PRIVATE  — закрытый ключ VAPID (base64url, 32 байта)
  SUBSCRIPTIONS  — JSON-подписка браузера (или список подписок)
  SITE_URL       — адрес сайта, например https://vladislavbropiton.github.io/velikie/
"""
import json
import os
import sys
import time
from pathlib import Path

from pywebpush import WebPushException, webpush

START_DAY = 20763  # 06.11.2026 — как START_DAY в index.html


def today_person(people):
    day = int((time.time() + 3 * 3600) // 86400)  # сутки по Москве
    return people[(day - START_DAY) % len(people)]


def main():
    people = json.loads(Path(__file__).with_name("data").joinpath("people.json").read_text("utf-8"))
    p = today_person(people)
    site = os.environ.get("SITE_URL", "").rstrip("/") + "/"
    payload = json.dumps({
        "title": p["name"],
        "body": p["teaser"],
        "url": f"./#/p/{p['id']}",
        "image": site + p["photos"][0]["src"],
    }, ensure_ascii=False)

    subs = json.loads(os.environ["SUBSCRIPTIONS"])
    if isinstance(subs, dict):
        subs = [subs]
    failed = 0
    for sub in subs:
        try:
            webpush(sub, payload, vapid_private_key=os.environ["VAPID_PRIVATE"],
                    vapid_claims={"sub": "mailto:velikie-app@example.com"}, ttl=6 * 3600)
            print("отправлено:", p["name"], sub["endpoint"][:60])
        except WebPushException as e:
            failed += 1
            print("ошибка:", e, getattr(e.response, "text", "")[:300])
    sys.exit(1 if failed == len(subs) else 0)


if __name__ == "__main__":
    main()
