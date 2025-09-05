from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def window_screenshot_kb(nick: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Скриншот", callback_data=f"screenshot_{nick}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_windows")]
        ]
    )
