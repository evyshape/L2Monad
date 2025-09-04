from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.controller import ProfileController
from bot.utils import findAllWindows

controller = ProfileController()


def manage_menu_kb() -> InlineKeyboardMarkup:
    kb_buttons = []
    all_nicks = set(findAllWindows().keys()) | set(controller.bot_manager.bots.keys())

    for nick in all_nicks:
        running = controller.is_running(nick)
        status = "🟢" if running else "🔴"
        kb_buttons.append([
            InlineKeyboardButton(text=f"{status} {nick}",
                                 callback_data=f"manage_window_{nick}")
        ])

    kb_buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")])
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
                text=f"⏹ STOP {running_profile}",
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