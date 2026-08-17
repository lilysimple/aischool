"""
tg_ask_photo.py

Присылает автору несколько фотографий-кандидатов, пронумерованных,
и ждёт ответа с номером. Нужен для шага, где агент подобрал 2-3 фото
под тему поста, а выбирает человек.

Всё общение с Telegram идёт через библиотеку python-telegram-bot.

Запуск:
    python3 scripts/tg_ask_photo.py input/photos/a.jpg input/photos/b.jpg \
        --question "Какое фото ставим?"

Печатает в stdout путь к выбранному файлу.
"""

import argparse
import asyncio
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TIMEOUT_MIN = 30
POLL_INTERVAL_SEC = 2


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("photos", nargs="+", help="2-3 файла-кандидата")
    ap.add_argument("--question", default="Какое фото ставим? Ответьте номером.")
    args = ap.parse_args()

    if not TOKEN or not CHAT_ID:
        print("Не найдены TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID в .env.")
        sys.exit(1)

    paths = [Path(p) for p in args.photos]
    missing = [p for p in paths if not p.exists()]
    if missing:
        print("Не найдены файлы: " + ", ".join(str(p) for p in missing))
        sys.exit(1)

    if not 2 <= len(paths) <= 10:
        print("Нужно от 2 до 10 фотографий.")
        sys.exit(1)

    bot = Bot(token=TOKEN)
    chat_id = int(CHAT_ID)

    # Отправляем кандидатов альбомом, подпись с нумерацией — на первом фото
    listing = "\n".join(f"{i + 1}. {p.name}" for i, p in enumerate(paths))
    caption = f"{args.question}\n\n{listing}"

    files = []
    try:
        media = []
        for i, path in enumerate(paths):
            fh = open(path, "rb")
            files.append(fh)
            media.append(InputMediaPhoto(media=fh, caption=caption if i == 0 else None))
        try:
            await bot.send_media_group(chat_id=chat_id, media=media)
        except TelegramError as e:
            print(f"Не удалось отправить фотографии: {e}")
            sys.exit(1)
    finally:
        for fh in files:
            fh.close()

    updates = await bot.get_updates(limit=1, timeout=1)
    offset = updates[-1].update_id + 1 if updates else None

    deadline = time.monotonic() + TIMEOUT_MIN * 60
    while time.monotonic() < deadline:
        updates = await bot.get_updates(offset=offset, timeout=10)
        for upd in updates:
            offset = upd.update_id + 1
            msg = upd.message
            if msg is None or msg.chat.id != chat_id or not msg.text:
                continue

            match = re.search(r"\d+", msg.text)
            if not match:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"Нужен номер от 1 до {len(paths)}. Попробуйте ещё раз.",
                )
                continue

            choice = int(match.group())
            if not 1 <= choice <= len(paths):
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"Такого варианта нет. Нужен номер от 1 до {len(paths)}.",
                )
                continue

            print(paths[choice - 1])
            return
        await asyncio.sleep(POLL_INTERVAL_SEC)

    print("Тайм-аут: ответ не пришёл за отведённое время.")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
