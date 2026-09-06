from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards import main_menu


router = Router()


@router.message(CommandStart())
async def start(message: Message, messages: dict[str, str], admin_id: int) -> None:
    await message.answer(messages["welcome"], reply_markup=main_menu(message.from_user.id == admin_id))


@router.message(lambda message: message.text == "📢 Наши каналы")
async def show_channels(message: Message, messages: dict[str, str], channels: list, admin_id: int) -> None:
    links = "\n".join(f"• {channel.link}" for channel in channels) or "Список пока пуст."
    await message.answer(
        messages["channels"].format(channels=links),
        reply_markup=main_menu(message.from_user.id == admin_id),
    )


@router.message(lambda message: message.text == "📞 Контакты")
async def show_contacts(message: Message, messages: dict[str, str], admin_id: int) -> None:
    await message.answer(
        messages["contacts"],
        reply_markup=main_menu(message.from_user.id == admin_id),
    )
