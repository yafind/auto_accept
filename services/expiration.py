import asyncio
import logging

from aiogram import Bot

from database import Database
from services.approval import notify_admin


async def expiration_loop(bot: Bot, database: Database, admin_id: int, messages: dict[str, str], logger: logging.Logger) -> None:
    while True:
        for application in await database.pending_expired():
            try:
                await bot.decline_chat_join_request(application["channel_id"], application["user_id"])
                if await database.expire_application(application["id"]):
                    await bot.send_message(application["user_id"], messages["expired"])
                    await database.log("application_expired", application["user_id"], application["channel_id"])
                    await notify_admin(bot, admin_id, f"⏱ Заявка истекла\n👤 ID: {application['user_id']}\n📢 Канал: {application['channel_id']}")
            except Exception as exc:
                logger.exception("expiration failed: %s", exc)
        await asyncio.sleep(30)
