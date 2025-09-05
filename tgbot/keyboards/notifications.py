from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from tgbot.config import config

def notifications_menu_kb() -> InlineKeyboardMarkup:
    kb_buttons = []
    for level, enabled in config.NOTIFY_LEVELS.items():
        text = f"{'🔔' if enabled else '🔕'} {level.capitalize()}"
        kb_buttons.append([InlineKeyboardButton(text=text, callback_data=f"notify_{level}")])
    kb_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)
