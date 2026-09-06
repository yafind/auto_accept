from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [KeyboardButton(text="📢 Наши каналы"), KeyboardButton(text="📞 Контакты")]
    if is_admin:
        buttons.append(KeyboardButton(text="🛠 Команды админа"))
    return ReplyKeyboardMarkup(
        keyboard=[buttons],
        resize_keyboard=True,
    )


def confirmation_keyboard(application_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Я не бот", callback_data=f"approve:{application_id}")]]
    )
