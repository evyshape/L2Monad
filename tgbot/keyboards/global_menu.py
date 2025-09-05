from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.controller import ProfileController

controller = ProfileController()

def global_menu_kb() -> InlineKeyboardMarkup:
    kb_buttons = []

    kb_buttons.append([
        InlineKeyboardButton(text="🚨 STOP ВСЕ 🚨", callback_data="global_stop_all")
    ])

    for profile_name in controller.profiles.keys():
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"➡️ {profile_name}",
                callback_data=f"global_start_all_{profile_name}"
            )
        ])

    kb_buttons.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_back")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)
