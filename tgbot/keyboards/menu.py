from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌏 Глобальное", callback_data="menu_global")],
            [InlineKeyboardButton(text="🤖 Окна", callback_data="menu_windows")],
            [InlineKeyboardButton(text="⚙️ Управление", callback_data="menu_manage")],
            [InlineKeyboardButton(text="🔔 Уведомления", callback_data="menu_notifications")]
        ]
    )
