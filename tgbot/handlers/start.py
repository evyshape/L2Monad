from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from tgbot.services.decorators import admin_only

router = Router()


@router.message(Command("start"))
@admin_only
async def cmd_start(message: Message):
    await message.answer("zdarova")
