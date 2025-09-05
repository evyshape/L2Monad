from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.controller import ProfileController

controller = ProfileController()
num_emoji = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟","1️⃣1️⃣","1️⃣2️⃣","1️⃣3️⃣","1️⃣4️⃣","1️⃣5️⃣"]

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

def batch_kb(profile_name: str, max_buttons: int) -> InlineKeyboardMarkup:
    limit = min(max_buttons, 15)
    buttons = []
    row = []
    for i in range(limit):
        emoji = num_emoji[i]
        row.append(InlineKeyboardButton(text=emoji, callback_data=f"batch_{profile_name}_{i+1}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_global")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)