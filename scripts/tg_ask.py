"""
tg_ask.py

Отправляет вопрос агенту-человеку в личный чат Telegram (TELEGRAM_CHAT_ID)
и блокируется, пока не придёт ответ. Ответ печатается в stdout — так его
может прочитать Claude Code, продолжающий сценарий в prompts/run-daily.md.

Работа с Telegram идёт через python-telegram-bot (Bot.send_message +
Bot.get_updates), а не через сырые POST-запросы к api.telegram.org.

Запуск:
    python3 scripts/tg_ask.py "Текст вопроса"
"""

import asyncio
import os
import sys
import time

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POLL_INTERVAL_SEC = 2
TIMEOUT_MIN = 30  # сколько ждём ответа, прежде чем сдаться


async def main() -> None:
    if len(sys.argv) < 2:
        print("Использование: python3 scripts/tg_ask.py \"текст вопроса\"")
        sys.exit(1)

    if not TOKEN or not CHAT_ID:
        print("Не найдены TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID в .env.")
        sys.exit(1)

    question = sys.argv[1]
    bot = Bot(token=TOKEN)
    chat_id = int(CHAT_ID)

    try:
        await bot.send_message(chat_id=chat_id, text=question)
    except TelegramError as e:
        print(f"Не удалось отправить сообщение: {e}")
        sys.exit(1)

    # Запоминаем, с какого update_id начинать, чтобы не поймать старые сообщения
    updates = await bot.get_updates(limit=1, timeout=1)
    offset = updates[-1].update_id + 1 if updates else None

    deadline = time.monotonic() + TIMEOUT_MIN * 60

    while time.monotonic() < deadline:
        updates = await bot.get_updates(offset=offset, timeout=10)
        for upd in updates:
            offset = upd.update_id + 1
            msg = upd.message
            if msg is None or msg.chat.id != chat_id:
                continue
            if msg.text:
                print(msg.text)
                return
        await asyncio.sleep(POLL_INTERVAL_SEC)

    print("Тайм-аут: ответ не пришёл за отведённое время.")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
