import asyncio
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

from database import Database


async def approve_with_retry(bot: Bot, channel_id: int, user_id: int, attempts: int = 3) -> None:
    for attempt in range(attempts):
        try:
            await bot.approve_chat_join_request(chat_id=channel_id, user_id=user_id)
            return
        except (TelegramBadRequest, TelegramNetworkError):
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(2**attempt)


def processing_seconds(row: object) -> float:
    return max(0.0, time.time() - time.mktime(time.strptime(str(row), "%Y-%m-%d %H:%M:%S")))


async def notify_admin(bot: Bot, admin_id: int, text: str) -> None:
    await bot.send_message(admin_id, text)
