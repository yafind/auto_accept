from datetime import timedelta
import logging

from aiogram import Bot, Router
from aiogram.types import ChatJoinRequest

from database import Database, utc_now
from keyboards import confirmation_keyboard


router = Router()


@router.chat_join_request()
async def handle_chat_join_request(request: ChatJoinRequest, bot: Bot, database: Database, messages: dict[str, str], logger: logging.Logger) -> None:
    user = request.from_user
    channel_id = request.chat.id
    await database.upsert_user(user.id, user.username, user.first_name)
    if await database.is_banned(user.id) or not await database.is_channel_active(channel_id):
        await bot.decline_chat_join_request(channel_id, user.id)
        await database.log("application_declined", user.id, channel_id, "banned_or_inactive")
        return

    expires_at = utc_now() + timedelta(minutes=10)
    application_id = await database.create_application(user.id, channel_id, expires_at)
    channel_name = request.chat.username and f"@{request.chat.username}" or request.chat.title
    await bot.send_message(
        user.id,
        messages["confirmation"].format(channel=channel_name),
        reply_markup=confirmation_keyboard(application_id),
    )
    await database.log("application_created", user.id, channel_id, str(application_id))
    logger.info("join request created: application=%s user=%s channel=%s", application_id, user.id, channel_id)
