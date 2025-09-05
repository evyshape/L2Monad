from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.controller import ProfileController
from bot.utils import findAllWindows
from tgbot.utils.pagination import paginate, navigation

controller = ProfileController()

def manage_menu_kb(page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    kb_buttons = []
    all_nicks = sorted(set(findAllWindows().keys()) | set(controller.bot_manager.bots.keys()))

    page_items, total_pages = paginate(all_nicks, page, per_page)

    for i in range(0, len(page_items), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=f"{'🟢' if controller.is_running(page_items[i]) else '🔴'} {page_items[i]}",
            callback_data=f"manage_window_{page_items[i]}"
        ))
        if i + 1 < len(page_items):
            row.append(InlineKeyboardButton(
                text=f"{'🟢' if controller.is_running(page_items[i+1]) else '🔴'} {page_items[i+1]}",
                callback_data=f"manage_window_{page_items[i+1]}"
            ))
        kb_buttons.append(row)

    nav_row = navigation(page, total_pages, prefix="manage_page")
    if nav_row:
        kb_buttons.append(nav_row)

    kb_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)


def window_profile_kb(nick: str) -> InlineKeyboardMarkup:
    kb_buttons = []
    running = controller.is_running(nick)

    if running:
        running_profile = None
        for profile_name in controller.profiles.keys():
            bot = controller.bot_manager.get_bot(nick)
            if bot and bot.__class__.__name__ == profile_name:
                running_profile = profile_name
                break

        kb_buttons.append([
            InlineKeyboardButton(
                text=f"🚫 STOP | {running_profile}",
                callback_data=f"stop_{nick}"
            )
        ])
    else:
        for profile_name in controller.profiles.keys():
            kb_buttons.append([
                InlineKeyboardButton(
                    text=f"⚪ {profile_name}",
                    callback_data=f"start_{nick}_{profile_name}"
                )
            ])
    kb_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_manage")])
    return InlineKeyboardMarkup(inline_keyboard=kb_buttons)