from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from tgbot.utils.pagination import paginate, navigation

def windows_menu_kb(nicks: list[str], page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    kb_buttons = []

    page_items, total_pages = paginate(nicks, page=page, per_page=per_page)

    for i in range(0, len(page_items), 2):
        row = [InlineKeyboardButton(text=page_items[i], callback_data=f"window_{page_items[i]}")]
        if i + 1 < len(page_items):
            row.append(InlineKeyboardButton(text=page_items[i+1], callback_data=f"window_{page_items[i+1]}"))
        kb_buttons.append(row)

    nav_row = navigation(page, total_pages, prefix="windows_page")
    if nav_row:
        kb_buttons.append(nav_row)

    kb_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)



def window_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_windows")]
        ]
    )
