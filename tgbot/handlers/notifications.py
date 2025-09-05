from aiogram import Router
from aiogram.types import CallbackQuery
from tgbot.keyboards.notifications import notifications_menu_kb
from tgbot.keyboards.menu import main_menu_kb
from tgbot.services.decorators import admin_only
from tgbot.config import config, save_notify

router = Router()

@router.callback_query(lambda c: c.data == "menu_notifications")
@admin_only
async def notifications_menu(callback: CallbackQuery):
    await callback.message.edit_text("🔔 Настройки уведомлений:", reply_markup=notifications_menu_kb())

@router.callback_query(lambda c: c.data.startswith("notify_"))
@admin_only
async def toggle_notification(callback: CallbackQuery):
    level = callback.data.split("_", 1)[1].lower()
    config.NOTIFY_LEVELS[level] = not config.NOTIFY_LEVELS.get(level, True)

    save_notify(config.NOTIFY_LEVELS)

    await callback.message.edit_text(
        "🔔 Настройки уведомлений:",
        reply_markup=notifications_menu_kb()
    )

@router.callback_query(lambda c: c.data == "menu_back")
@admin_only
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("🏥 Главное меню:", reply_markup=main_menu_kb())
