from typing import List
from aiogram.types import InlineKeyboardButton

def paginate(items: List[str], page: int = 0, per_page: int = 8):
    total_pages = (len(items) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    return items[start:end], total_pages


def navigation(page: int, total_pages: int, prefix: str) -> list[InlineKeyboardButton]:
    if page > 0:
        prev_button = InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_{page-1}")
    else:
        prev_button = InlineKeyboardButton(text=" ", callback_data="ignore")

    page_button = InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="ignore")

    if page + 1 < total_pages:
        next_button = InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_{page+1}")
    else:
        next_button = InlineKeyboardButton(text=" ", callback_data="ignore")

    return [prev_button, page_button, next_button]