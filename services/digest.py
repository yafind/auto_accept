import asyncio
from datetime import datetime, timedelta

from aiogram import Bot

from database import Database
from handlers.admin import format_stats


def build_digest(rows: list, date: str) -> str:
    return f"📊 Дайджест за {date}\n\n{format_stats(rows)}"


def seconds_until(hour_minute: str) -> float:
    hour, minute = (int(value) for value in hour_minute.split(":", 1))
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def send_digest(bot: Bot, database: Database, admin_id: int) -> None:
    date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    await bot.send_message(admin_id, build_digest(await database.stats(date), date))


async def digest_loop(bot: Bot, database: Database, admin_id: int, digest_time: str) -> None:
    while True:
        await asyncio.sleep(seconds_until(digest_time))
        await send_digest(bot, database, admin_id)
