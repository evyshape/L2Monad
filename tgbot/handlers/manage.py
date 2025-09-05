from aiogram import Router, F
from aiogram.types import CallbackQuery
from bot.controller import ProfileController
from bot.utils import findAllWindows
from tgbot.keyboards.manage import manage_menu_kb, window_profile_kb
from tgbot.keyboards.menu import main_menu_kb
from tgbot.services.decorators import admin_only

router = Router()
controller = ProfileController()

@router.callback_query(F.data == "menu_manage")
@admin_only
async def manage_main(callback: CallbackQuery):
    windows = list(findAllWindows().keys())
    if not windows:
        await callback.answer("❌ Нет доступных окон", show_alert=True)
        return

    await callback.message.edit_text(
        "⚙️ Выберите окно для управления:",
        reply_markup=manage_menu_kb()
    )

@router.callback_query(lambda c: c.data.startswith("manage_page_"))
@admin_only
async def manage_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await callback.message.edit_text(
        "⚙️ Выберите окно для управления:",
        reply_markup=manage_menu_kb(page)
    )


@router.callback_query(F.data.startswith("manage_window_"))
@admin_only
async def manage_window(callback: CallbackQuery):
    nick = callback.data.split("_", 2)[2]
    await callback.message.edit_text(
        f"🔩 Управление окном <b>{nick}</b>:",
        reply_markup=window_profile_kb(nick),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("start_"))
@admin_only
async def start_profile(callback: CallbackQuery):
    _, nick, profile_name = callback.data.split("_", 2)
    profile_cls = controller.profiles.get(profile_name)
    if not profile_cls:
        await callback.answer(f"❌ Профиль {profile_name} не найден", show_alert=True)
        return

    controller.start_windows(profile_cls, [nick])
    await callback.answer(f"✅ Запуск {profile_name} на {nick}")
    await callback.message.edit_reply_markup(reply_markup=window_profile_kb(nick))

@router.callback_query(F.data.startswith("stop_"))
@admin_only
async def stop_window(callback: CallbackQuery):
    nick = callback.data.split("_", 1)[1]
    controller.stop_windows([nick])
    await callback.answer(f"🛑 Остановка {nick}")
    await callback.message.edit_reply_markup(reply_markup=window_profile_kb(nick))

@router.callback_query(F.data == "menu_back")
@admin_only
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("🏥 Главное меню:", reply_markup=main_menu_kb())