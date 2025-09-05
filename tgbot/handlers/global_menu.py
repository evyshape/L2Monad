from aiogram import Router, types
from tgbot.keyboards.global_menu import global_menu_kb
from tgbot.services.decorators import admin_only
from bot.controller import ProfileController
from bot.utils import findAllWindows

router = Router()
controller = ProfileController()

def get_text():
    all_nicks = sorted(set(findAllWindows().keys()) | set(controller.bot_manager.bots.keys()))
    active_count = sum(1 for n in all_nicks if controller.is_running(n))
    inactive_count = len(all_nicks) - active_count
    return (
        f"🌏 Глобал управление:\n\n"
        f"🟢 Активные окна: {active_count}\n"
        f"🔴 Неактивные окна: {inactive_count}\n\n"
        "Выбирай нужное действие:"
    )

@router.callback_query(lambda c: c.data == "menu_global")
@admin_only
async def show_global_menu(call: types.CallbackQuery):
    text = get_text()
    await call.message.edit_text(
        text,
        reply_markup=global_menu_kb()
    )
    await call.answer()

@router.callback_query(lambda c: c.data == "global_stop_all")
@admin_only
async def global_stop(call: types.CallbackQuery):
    all_nicks = sorted(set(findAllWindows().keys()) | set(controller.bot_manager.bots.keys()))
    active_nicks = [n for n in all_nicks if controller.is_running(n)]

    if not active_nicks:
        await call.answer("⚠️ Нет активных окон для остановки!", show_alert=False)
        return

    controller.stop_windows(active_nicks)
    await call.answer(f"⛔ Остановлено {len(active_nicks)} активных окон!", show_alert=False)

    text = get_text()
    await call.message.edit_text(text, reply_markup=global_menu_kb())

@router.callback_query(lambda c: c.data.startswith("global_start_all_"))
@admin_only
async def global_start_profile(call: types.CallbackQuery):
    profile_name = call.data.replace("global_start_all_", "")
    profile_class = controller.profiles.get(profile_name)
    if not profile_class:
        await call.answer("⚠️ Профиль не найден!", show_alert=False)
        return

    all_nicks = sorted(set(findAllWindows().keys()) | set(controller.bot_manager.bots.keys()))
    inactive_nicks = [n for n in all_nicks if not controller.is_running(n)]

    if not inactive_nicks:
        await call.answer(f"⚠️ Нет неактивных окон для запуска! ({len(all_nicks)})", show_alert=False)
        return

    controller.start_windows(profile_class, inactive_nicks)
    await call.answer(f"✅ Профиль {profile_name} запущен в {len(inactive_nicks)} окнах", show_alert=False)
    text = get_text()
    await call.message.edit_text(text, reply_markup=global_menu_kb())

@router.callback_query(lambda c: c.data == "menu_back")
@admin_only
async def back_to_menu(call: types.CallbackQuery):
    from tgbot.keyboards.menu import main_menu_kb
    await call.message.edit_text("🏥 Главное меню:", reply_markup=main_menu_kb())
    await call.answer()
