import asyncio
import contextlib

from aiogram import Bot, Dispatcher

from channels import load_channels
from config import load_settings
from database import Database
from handlers import admin, callback, join_request, start
from messages import load_messages
from services.digest import digest_loop, send_digest
from services.expiration import expiration_loop
from services.heartbeat import heartbeat_loop
from utils.logger import setup_logger


async def main() -> None:
    settings = load_settings()
    logger = setup_logger()
    channels = load_channels(settings.channels_file)
    messages = load_messages(settings.messages_file)
    database = Database(settings.database_path)
    await database.connect()
    await database.sync_channels(channels)

    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_routers(start.router, join_request.router, callback.router, admin.router)
    send_admin_digest = lambda: send_digest(bot, database, settings.admin_id)
    background_tasks = [
        asyncio.create_task(expiration_loop(bot, database, settings.admin_id, messages, logger)),
        asyncio.create_task(heartbeat_loop(bot, settings.admin_id, settings.heartbeat_interval, logger)),
        asyncio.create_task(digest_loop(bot, database, settings.admin_id, settings.digest_time)),
    ]
    try:
        await dispatcher.start_polling(
            bot,
            database=database,
            messages=messages,
            channels=channels,
            admin_id=settings.admin_id,
            logger=logger,
            channels_file=settings.channels_file,
            send_digest=send_admin_digest,
        )
    finally:
        for task in background_tasks:
            task.cancel()
        await asyncio.gather(*background_tasks, return_exceptions=True)
        await bot.session.close()
        await database.close()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
