from datetime import timedelta
import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery

from database import Database, parse_datetime, utc_now
from services.approval import approve_with_retry, notify_admin


router = Router()


@router.callback_query(lambda query: query.data and query.data.startswith("approve:"))
async def approve_request(query: CallbackQuery, bot: Bot, database: Database, messages: dict[str, str], admin_id: int, logger: logging.Logger) -> None:
    application_id = int(query.data.split(":", 1)[1])
    application = await database.get_application(application_id)
    if not application:
        await query.answer(messages["already_processed"], show_alert=True)
        return
    if query.from_user.id != application["user_id"]:
        await database.log("foreign_button_click", query.from_user.id, application["channel_id"], str(application_id))
        await notify_admin(bot, admin_id, f"🚫 Попытка обойти капчу\n👤 ID: {query.from_user.id}\n📋 Заявка: {application_id}")
        await query.answer(messages["foreign_click"], show_alert=True)
        return
    if application["status"] != "pending" or utc_now() >= parse_datetime(application["expires_at"]):
        await query.answer(messages["already_processed"], show_alert=True)
        return
    if utc_now() - parse_datetime(application["created_at"]) < timedelta(seconds=3):
        await query.answer(messages["too_early"], show_alert=True)
        return
    if await database.is_banned(application["user_id"]):
        await query.answer(messages["already_processed"], show_alert=True)
        return

    claimed = await database.claim_application(application_id)
    if not claimed:
        await query.answer(messages["already_processed"], show_alert=True)
        return
    try:
        await approve_with_retry(bot, application["channel_id"], application["user_id"])
        if await database.approve_application(application_id):
            await database.mark_confirmed(application["user_id"])
            await database.log("application_approved", application["user_id"], application["channel_id"], str(application_id))
            applicant_notified = True

            try:
                await bot.send_message(application["user_id"], messages["approved"])
            except TelegramForbiddenError as exc:
                applicant_notified = False
                logger.warning(
                    "approval notification unavailable: application=%s user=%s",
                    application_id,
                    application["user_id"],
                )
                await database.log(
                    "application_notification_failed",
                    application["user_id"],
                    application["channel_id"],
                    f"forbidden: {exc}",
                )
            except Exception as exc:
                applicant_notified = False
                logger.exception("approval notification failed: application=%s", application_id)
                await database.log(
                    "application_notification_failed",
                    application["user_id"],
                    application["channel_id"],
                    str(exc),
                )

            await query.message.edit_reply_markup(reply_markup=None)
            try:
                notification_note = "" if applicant_notified else "\n⚠️ Уведомление пользователю не доставлено"
                await notify_admin(
                    bot,
                    admin_id,
                    f"✅ Заявка одобрена{notification_note}\n👤 ID: {application['user_id']}\n📢 Канал: {application['channel_id']}",
                )
            except Exception as exc:
                logger.exception("approval admin notification failed: application=%s", application_id)
                await database.log(
                    "admin_notification_failed",
                    application["user_id"],
                    application["channel_id"],
                    str(exc),
                )
                await query.answer(messages["approved"])
    except Exception as exc:
        await database.release_application(application_id)
        logger.exception("approval failed: %s", exc)
        await database.log("approval_error", application["user_id"], application["channel_id"], str(exc))
        await notify_admin(bot, admin_id, f"❌ Ошибка одобрения\n📋 Заявка: {application_id}\n{exc}")
        await query.answer("Не удалось обработать заявку. Попробуйте позже.", show_alert=True)
