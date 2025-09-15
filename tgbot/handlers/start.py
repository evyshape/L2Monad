from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from tgbot.config import config
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    admins = config.ADMINS

    if message.from_user.id in admins:
        text = (
            "👋 Привет\n\n"
            "Доступные команды:\n"
            "• /menu — попасть в меню\n"
            "• /logs — управление логами"
        )
        await message.answer(text=text, parse_mode="HTML")

    else:
        text = (
            "👋 Здарова работяга!\n\n"
            "Ты попал в бота для <b>Lineage 2M</b> ⚔️\n\n"
            "Этот проект полностью <b>бесплатный</b> и <b>опенсурсный</b>. "
            "Если хочешь такого же бота — просто скачай и пользуйся.\n\n"
            "На текущий момент он умеет:\n"
            "• Автозакуп банок и сосок\n"
            "• Додж пвп, ответ пвп\n"
            "• Контроль перевеса, контроль хп, контроль банок\n"
            "• Удобное GUI + Telegram бот\n"
            "• Несколько профилей, многозадачность\n"
            "• Гибкие расписания (почта, награды, аук)\n"
            "• Обновление прямо из GUI\n\n"
            "📌 Всё ещё в активной разработке, функционал расширяется, скачать и ознакомиться можно по кнопке ниже!"
            "\n\n(если ты пользователь, то ты забыл указать свой айди в tg.ini)"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📥 Скачать",
                                      url="https://github.com/evyshape/L2Monad")]
            ]
        )

        await message.answer(text=text, parse_mode="HTML", reply_markup=keyboard)
