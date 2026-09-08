from datetime import timedelta
import logging

from aiogram import Bot, Router
from aiogram.types import ChatJoinRequest
from aiogram.exceptions import TelegramForbiddenError

from database import Database, utc_now
from keyboards import confirmation_keyboard
from services.approval import approve_with_retry

router = Router()


@router.chat_join_request()
async def handle_chat_join_request(
    request: ChatJoinRequest, 
    bot: Bot, 
    database: Database, 
    messages: dict[str, str], 
    logger: logging.Logger
) -> None:
    user = request.from_user
    channel_id = request.chat.id
    
    await database.upsert_user(user.id, user.username, user.first_name)
    
    if await database.is_banned(user.id) or not await database.is_channel_active(channel_id):
        await bot.decline_chat_join_request(channel_id, user.id)
        await database.log("application_declined", user.id, channel_id, "banned_or_inactive")
        return

    if await database.is_confirmed(user.id):
        try:
            await approve_with_retry(bot, channel_id, user.id)
            await database.log("application_auto_approved", user.id, channel_id, "already_confirmed")
            try:
                await bot.send_message(user.id, messages["approved"])
            except TelegramForbiddenError:
                logger.warning("automatic approval notification unavailable: user=%s channel=%s", user.id, channel_id)
            except Exception as exc:
                logger.exception("automatic approval notification failed: user=%s channel=%s", user.id, channel_id)
                await database.log("application_notification_failed", user.id, channel_id, str(exc))
        except Exception as exc:
            logger.exception("automatic approval failed: user=%s channel=%s", user.id, channel_id)
            await database.log("approval_error", user.id, channel_id, str(exc))
        return

    expires_at = utc_now() + timedelta(minutes=10)
    existing_application = await database.get_pending_application(user.id, channel_id)
    application_id = existing_application["id"] if existing_application else await database.create_application(user.id, channel_id, expires_at)
    channel_name = request.chat.username and f"@{request.chat.username}" or request.chat.title
    
    try:
        await bot.send_message(
            user.id,
            messages["confirmation"].format(channel=channel_name),
            reply_markup=confirmation_keyboard(application_id),
        )
        await database.log("application_created", user.id, channel_id, str(application_id))
        logger.info("join request created: application=%s user=%s channel=%s", application_id, user.id, channel_id)
        
    except TelegramForbiddenError:
        # Пользователь заблокировал бота. Он не сможет подтвердить заявку, поэтому отклоняем её.
        logger.warning("join request declined: user=%s channel=%s (bot was blocked by user)", user.id, channel_id)
        await bot.decline_chat_join_request(channel_id, user.id)
        await database.log("application_declined", user.id, channel_id, "bot_blocked")
        
    except Exception as e:
        # Страховка от других сетевых или неизвестных ошибок, чтобы не крашить обработку апдейта
        logger.error("join request send error: user=%s channel=%s error=%s", user.id, channel_id, repr(e))