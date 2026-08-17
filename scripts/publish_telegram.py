"""
publish_telegram.py

Публикует пост в канал: одна картинка-обложка и текст под ней.

Telegram ограничивает подпись к фотографии 1024 знаками — это не наше
решение, а лимит платформы, и обойти его в одном сообщении нельзя.
Скрипт проверяет длину заранее и отказывается публиковать переросший
текст, вместо того чтобы получить ошибку от Telegram на полпути.

Текст размечается через parse_mode=HTML. Поддерживаются теги
<b>, <i>, <u>, <s>, <code>, <pre>, <a href>, <blockquote> и
<span class="tg-spoiler">. Списков (<ul>, <li>) в Telegram нет:
маркеры делаются обычными символами в тексте.

Работа с Telegram идёт через библиотеку python-telegram-bot.

Запуск:
    python3 scripts/publish_telegram.py output/2026-08-17
    (в папке ожидаются cover.png и post.html)
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

MAX_CAPTION_LEN = 1024

ALLOWED_TAGS = {
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre", "blockquote", "span", "tg-spoiler", "br",
}


def visible_length(html: str) -> int:
    """Длина текста без учёта тегов — именно её считает Telegram."""
    return len(re.sub(r"<[^>]+>", "", html))


def check_tags(html: str) -> list:
    """Возвращает список тегов, которых Telegram не понимает."""
    found = {t.lower() for t in re.findall(r"</?([a-zA-Z][\w-]*)", html)}
    return sorted(found - ALLOWED_TAGS)


async def main() -> None:
    if len(sys.argv) < 2:
        print("Использование: python3 scripts/publish_telegram.py output/<папка>")
        sys.exit(1)

    if not TOKEN or not CHANNEL_ID:
        print("Не найдены TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL_ID в .env.")
        sys.exit(1)

    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"Папка не найдена: {folder}")
        sys.exit(1)

    cover = folder / "cover.png"
    post = folder / "post.html"

    if not cover.exists():
        print(f"Нет обложки {cover}. Сначала запустите render_cover.py.")
        sys.exit(1)
    if not post.exists():
        print(f"Нет текста {post}.")
        sys.exit(1)

    text = post.read_text(encoding="utf-8").strip()
    if not text:
        print(f"Файл {post} пустой.")
        sys.exit(1)

    bad = check_tags(text)
    if bad:
        print(
            "Telegram не понимает эти теги: " + ", ".join(bad) + ".\n"
            "Разрешены: b, i, u, s, a, code, pre, blockquote, span class=tg-spoiler.\n"
            "Списков в Telegram нет — маркеры делаются символами в тексте."
        )
        sys.exit(1)

    length = visible_length(text)
    if length > MAX_CAPTION_LEN:
        print(
            f"Текст длиннее лимита Telegram: {length} знаков при максимуме "
            f"{MAX_CAPTION_LEN} (теги не считаются). Сократите на "
            f"{length - MAX_CAPTION_LEN} знаков и запустите снова."
        )
        sys.exit(1)

    bot = Bot(token=TOKEN)
    chat_id = CHANNEL_ID if CHANNEL_ID.startswith("@") else int(CHANNEL_ID)

    try:
        with open(cover, "rb") as fh:
            message = await bot.send_photo(
                chat_id=chat_id,
                photo=fh,
                caption=text,
                parse_mode=ParseMode.HTML,
            )
    except TelegramError as e:
        print(f"Telegram отказал в публикации: {e}")
        sys.exit(1)

    if message.chat.username:
        print(f"Опубликовано: https://t.me/{message.chat.username}/{message.message_id}")
    else:
        print(f"Опубликовано в канал {chat_id}, message_id={message.message_id}")


if __name__ == "__main__":
    asyncio.run(main())
