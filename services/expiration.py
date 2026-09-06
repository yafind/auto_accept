import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError  # <-- Добавили импорты

from database import Database
from services.approval import notify_admin


async def expiration_loop(bot: Bot, database: Database, admin_id: int, messages: dict[str, str], logger: logging.Logger) -> None:
    while True:
        for application in await database.pending_expired():
            try:
                await bot.decline_chat_join_request(application["channel_id"], application["user_id"])
                
                # Если отклонение прошло успешно, выполняем стандартную логику
                if await database.expire_application(application["id"]):
                    try:
                        await bot.send_message(application["user_id"], messages["expired"])
                    except Exception:
                        pass  # Игнорируем ошибку отправки, если пользователь заблокировал бота
                    
                    await database.log("application_expired", application["user_id"], application["channel_id"])
                    await notify_admin(
                        bot, admin_id, 
                        f"⏱ Заявка истекла\n👤 ID: {application['user_id']}\n📢 Канал: {application['channel_id']}"
                    )
                    
            except TelegramBadRequest as e:
                # Заявка уже была обработана (принята/отклонена/отменена пользователем)
                if "HIDE_REQUESTER_MISSING" in str(e) or "REQUEST_ID_INVALID" in str(e) or "CHAT_JOIN_REQUEST_JOIN_MISSING" in str(e):
                    logger.warning(
                        "Заявка уже отсутствует в Telegram, принудительно завершаем в БД: user=%s channel=%s",
                        application["user_id"], application["channel_id"]
                    )
                    # КРИТИЧЕСКИ ВАЖНО: удаляем заявку из pending, чтобы разорвать бесконечный цикл
                    await database.expire_application(application["id"])
                else:
                    logger.exception("expiration failed (BadRequest): %s", e)
                    
            except TelegramForbiddenError:
                # Бота удалили из канала или заблокировали
                logger.warning(
                    "Нет прав в канале %s, принудительно завершаем заявку в БД", 
                    application["channel_id"]
                )
                await database.expire_application(application["id"])
                
            except Exception as exc:
                logger.exception("expiration failed: %s", exc)
                
        await asyncio.sleep(30)