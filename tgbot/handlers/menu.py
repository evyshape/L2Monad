from aiogram import Router, types
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from bot.controller import ProfileController
from bot.utils import findAllWindows
from tgbot.keyboards.menu import main_menu_kb, windows_menu_kb, window_back_kb
from tgbot.services.decorators import admin_only

router = Router()
controller = ProfileController()

@router.message(Command("menu"))
@admin_only
async def menu_command(message: types.Message):
    await message.answer("🏥 Главное меню:", reply_markup=main_menu_kb())

@router.callback_query()
@admin_only
async def menu_callback(callback: CallbackQuery):
    data = callback.data

    if data == "menu_notifications":
        await callback.answer("#todo", show_alert=True)

    elif data == "menu_windows":
        windows_info = findAllWindows()
        nicks = list(windows_info.keys())

        if not nicks:
            await callback.answer("❌ Нет доступных окон", show_alert=True)
            return

        await callback.message.edit_text(
            "Выбирай окно:",
            reply_markup=windows_menu_kb(nicks)
        )

    elif data == "menu_back":
        await callback.message.edit_text("🏥 Главное меню:", reply_markup=main_menu_kb())

    elif data.startswith("window_"):
        nick = data.split("_", 1)[1]
        runtime = controller.get_runtime_info(nick)

        if not runtime:
            await callback.answer(f"❌ Нет данных для окна {nick}\n❌ Возможно оно не запущено?", show_alert=True)
            return

        text = (
            f"📊 <b>{nick}</b>\n\n"
            f"🟢 Состояние: <code>{runtime.current_state}</code>\n\n"
            f"🎒 Стешей: <code>{runtime.stashing_count}</code>\n"
            f"💰 Закупов: <code>{runtime.buy_count}</code>\n"
            f"📦 Продаж: <code>{runtime.purc_count}</code>\n\n"
            f"⏱ Последний возврат на спот: <code>{runtime.last_return_spot}</code>\n" 
            f"🕒 Время когда нужно на спот: <code>{runtime.spot_time}</code>\n\n"
            f"⚔️ Попыток доджа: <code>{runtime.dodge_attempts}</code>\n"
            f"❌ Последний додж: <code>{runtime.last_dodge}</code>\n"
            f"✅ Последний успешный додж: <code>{runtime.last_succ_dodge}</code>\n\n"
            f"🏹 Колчан: <code>{runtime.has_quiver}</code>\n"
            f"🗺 Маппинг: <code>{runtime.last_mapping}</code>"
        )
        await callback.message.edit_text(text, reply_markup=window_back_kb(), parse_mode="HTML")
