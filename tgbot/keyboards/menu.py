from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Уведомления", callback_data="menu_notifications")],
            [InlineKeyboardButton(text="🤖 Окна", callback_data="menu_windows")],
            [InlineKeyboardButton(text="⚙️ Управление", callback_data="menu_manage")]
        ]
    )


def windows_menu_kb(nicks: list[str]) -> InlineKeyboardMarkup:
    kb_buttons = [[InlineKeyboardButton(text=nick, callback_data=f"window_{nick}")] for nick in nicks]
    kb_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)

def window_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад к списку окон", callback_data="menu_windows")]
        ]
    )
