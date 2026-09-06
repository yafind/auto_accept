import asyncio
import logging

from aiogram import Bot


async def heartbeat_loop(bot: Bot, admin_id: int, interval: int, logger: logging.Logger) -> None:
    while True:
        try:
            await bot.send_message(admin_id, "💓 Бот работает нормально")
        except Exception:
            logger.exception("heartbeat failed")
        await asyncio.sleep(interval)
