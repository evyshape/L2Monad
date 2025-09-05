from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def window_screenshot_kb(nick: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Скриншот", callback_data=f"screenshot_{nick}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_windows")]
        ]
    )

def delete_screenshot_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Скрыть", callback_data=f"delete_screenshot")]
        ]
    )