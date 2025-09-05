from aiogram import Router, types
from aiogram.filters import Command
from tgbot.keyboards.menu import main_menu_kb
from tgbot.services.decorators import admin_only

router = Router()

@router.message(Command("menu"))
@admin_only
async def menu_command(message: types.Message):
    await message.answer("🏥 Главное меню:", reply_markup=main_menu_kb())
