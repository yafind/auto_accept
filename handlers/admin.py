import csv
import io
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from channels import load_channels
from database import Database


router = Router()


@router.message(lambda message: message.text == "🛠 Команды админа")
async def admin_help(message: Message, messages: dict[str, str], admin_id: int) -> None:
    if not await is_admin(message, admin_id):
        return
    await message.answer(messages["admin_help"])


async def is_admin(message: Message, admin_id: int) -> bool:
    if message.from_user.id != admin_id:
        await message.answer("Недостаточно прав.")
        return False
    return True


def format_stats(rows: list) -> str:
    values = {row["status"]: row["count"] for row in rows}
    total = sum(values.values())
    return "\n".join([
        f"📊 Заявок: {total}",
        f"✅ Одобрено: {values.get('approved', 0)}",
        f"❌ Отклонено: {values.get('declined', 0)}",
        f"⏱ Истекло: {values.get('expired', 0)}",
        f"📝 Ожидают: {values.get('pending', 0)}",
    ])


@router.message(Command("stats"))
async def stats(message: Message, command: CommandObject, database: Database, admin_id: int) -> None:
    if not await is_admin(message, admin_id):
        return
    date = datetime.now().strftime("%Y-%m-%d") if command.args == "today" else None
    await message.answer(format_stats(await database.stats(date)))


@router.message(Command("ban", "unban"))
async def ban(message: Message, command: CommandObject, database: Database, admin_id: int) -> None:
    if not await is_admin(message, admin_id):
        return
    if not command.args or not command.args.strip().lstrip("-").isdigit():
        await message.answer("Использование: /ban <user_id> или /unban <user_id>")
        return
    user_id = int(command.args)
    banned = message.text.split()[0].lower() == "/ban"
    await database.set_banned(user_id, banned)
    await message.answer(f"Пользователь {user_id}: {'заблокирован' if banned else 'разблокирован'}.")


@router.message(Command("channels"))
async def channels_command(message: Message, database: Database, admin_id: int) -> None:
    if not await is_admin(message, admin_id):
        return
    rows = await database.active_channels()
    await message.answer("\n".join(f"• {row['link']} ({row['channel_id']})" for row in rows) or "Активных каналов нет.")


@router.message(Command("reload"))
async def reload_channels(message: Message, database: Database, admin_id: int, channels: list, channels_file) -> None:
    if not await is_admin(message, admin_id):
        return
    refreshed = load_channels(channels_file)
    channels.clear()
    channels.extend(refreshed)
    await database.sync_channels(refreshed)
    await message.answer(f"Каналы перечитаны: {len(refreshed)}.")


@router.message(Command("export"))
async def export_logs(message: Message, database: Database, admin_id: int) -> None:
    if not await is_admin(message, admin_id):
        return
    rows = await database.fetchall("SELECT * FROM logs ORDER BY created_at DESC")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "event_type", "user_id", "channel_id", "details", "created_at"])
    writer.writerows(tuple(row) for row in rows)
    await message.answer_document(BufferedInputFile(buffer.getvalue().encode(), filename="logs.csv"))


@router.message(Command("digest"))
async def digest_command(message: Message, database: Database, admin_id: int, send_digest) -> None:
    if not await is_admin(message, admin_id):
        return
    await send_digest()
    await message.answer("Дайджест отправлен.")
