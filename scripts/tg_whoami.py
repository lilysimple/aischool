"""
tg_whoami.py

Показывает chat_id того, кто последним написал вашему боту.
Раньше это делалось сырым HTTP-запросом (requests.get(".../getUpdates")).
Теперь работу с Telegram API целиком берёт на себя библиотека
python-telegram-bot — она сама собирает запрос, разбирает ответ
и отдаёт удобные Python-объекты (Update, Chat, User).

Запуск:
    python3 scripts/tg_whoami.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def main() -> None:
    if not TOKEN:
        print("Не найден TELEGRAM_BOT_TOKEN в .env — заполните шаг 5.")
        sys.exit(1)

    bot = Bot(token=TOKEN)

    try:
        updates = await bot.get_updates(limit=20, timeout=5)
    except TelegramError as e:
        print(f"Telegram вернул ошибку: {e}")
        sys.exit(1)

    if not updates:
        print(
            "Обновлений нет. Проверьте:\n"
            "  1) вы написали боту хотя бы одно сообщение\n"
            "  2) токен в .env скопирован без лишних пробелов"
        )
        return

    print(f"Найдено обновлений: {len(updates)}\n")

    seen = set()
    for upd in updates:
        msg = upd.message or upd.channel_post
        if msg is None:
            continue
        chat = msg.chat
        if chat.id in seen:
            continue
        seen.add(chat.id)

        who = " ".join(
            part
            for part in [chat.first_name, chat.last_name, f"@{chat.username}" if chat.username else None]
            if part
        ) or chat.title or "без имени"

        print(f"chat_id: {chat.id}")
        print(f"тип:     {chat.type}")
        print(f"кто:     {who}")
        print("-" * 30)


if __name__ == "__main__":
    asyncio.run(main())
