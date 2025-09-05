from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import random

def prank_kb(nick: str, stage: int = 1) -> InlineKeyboardMarkup:
    if stage == 1:
        return InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ Да", callback_data=f"prank_start_{nick}_2"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"prank_start_{nick}_info")
            ]]
        )

    elif stage == 2:
        total_buttons = 5
        correct_index = random.randint(0, total_buttons - 1)
        row = []
        for i in range(total_buttons):
            if i == correct_index:
                row.append(InlineKeyboardButton(text="✅", callback_data=f"prank_start_{nick}_3"))
            else:
                row.append(InlineKeyboardButton(text="❌", callback_data=f"prank_start_{nick}_info"))
        return InlineKeyboardMarkup(inline_keyboard=[row])

    elif stage == 3:
        total_buttons = 50
        wrong_index = random.randint(0, total_buttons - 1)
        inline_buttons = []
        row = []
        for i in range(total_buttons):
            if i == wrong_index:
                row.append(InlineKeyboardButton(text="✅", callback_data=f"prank_start_{nick}_info"))
            else:
                row.append(InlineKeyboardButton(text="❌", callback_data=f"prank_start_{nick}_done"))
            if len(row) == 5:
                inline_buttons.append(row)
                row = []
        if row:
            inline_buttons.append(row)
        return InlineKeyboardMarkup(inline_keyboard=inline_buttons)
