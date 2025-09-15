from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from tgbot.utils.pagination import paginate, navigation
from bot.utils import getLogs


def main_logs_kb(page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    kb_buttons = []
    all_logs = [log["Name"] for log in getLogs()]
    page_items, total_pages = paginate(all_logs, page, per_page)

    for i in range(0, len(page_items), 2):
        row = [
            InlineKeyboardButton(
                text=page_items[i],
                callback_data=f"open_log_{page_items[i]}"
            )
        ]
        if i + 1 < len(page_items):
            row.append(
                InlineKeyboardButton(
                    text=page_items[i + 1],
                    callback_data=f"open_log_{page_items[i + 1]}"
                )
            )
        kb_buttons.append(row)

    nav_row = navigation(page, total_pages, prefix="logs_page")
    if nav_row:
        kb_buttons.append(nav_row)

    kb_buttons.append([InlineKeyboardButton(text="🗑️ Скрыть", callback_data=f"delete_screenshot")])
    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)
