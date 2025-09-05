from aiogram import Router, types
from aiogram.types import CallbackQuery
from bot.controller import ProfileController
from bot.utils import findAllWindows
from tgbot.keyboards.windows import windows_menu_kb, window_back_kb
from tgbot.keyboards.screenshot import window_screenshot_kb
from tgbot.keyboards.menu import main_menu_kb
from tgbot.services.decorators import admin_only

router = Router()
controller = ProfileController()

@router.callback_query(lambda c: c.data == "menu_windows")
@admin_only
async def windows_menu(callback: CallbackQuery):
    windows_info = findAllWindows()
    nicks = list(windows_info.keys())

    if not nicks:
        await callback.answer("❌ Нет доступных окон", show_alert=True)
        return

    await callback.message.edit_text(
        "Выбирай окно:",
        reply_markup=windows_menu_kb(nicks)
    )

@router.callback_query(lambda c: c.data.startswith("windows_page_"))
@admin_only
async def windows_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    windows_info = findAllWindows()
    nicks = list(windows_info.keys())

    if not nicks:
        await callback.answer("❌ Нет доступных окон", show_alert=True)
        return

    await callback.message.edit_text(
        "Выбирай окно:",
        reply_markup=windows_menu_kb(nicks, page=page)
    )


@router.callback_query(lambda c: c.data.startswith("window_"))
@admin_only
async def window_info(callback: CallbackQuery):
    nick = callback.data.split("_", 1)[1]
    runtime = controller.get_runtime_info(nick)

    if not runtime:
        await callback.message.edit_text(
            f"❌ Нет данных для окна <b>{nick}</b>\n"
            f"❌ Возможно оно не запущено?",
            reply_markup=window_back_kb(), # можно заменить на window_screenshot_kb(nick) чтоб скринить оффнутые окна но пох
            parse_mode="HTML"
        )
        return

    text = (
        f"📊 <b>{nick}</b>\n\n"
        f"🟢 Состояние: <code>{runtime.current_state}</code>\n\n"
        f"🎒 Стешей: <code>{runtime.stashing_count}</code>\n"
        f"💰 Закупов: <code>{runtime.buy_count}</code>\n"
        f"📦 Продаж: <code>{runtime.purc_count}</code>\n\n"
        f"⚖️ Перевес: <code>{runtime.overweight.value}%</code>\n\n"
        f"⏱ Последний возврат на спот: <code>{runtime.last_return_spot}</code>\n"
        f"🕒 Время когда нужно на спот: <code>{runtime.spot_time}</code>\n\n"
        f"⚔️ Попыток доджа: <code>{runtime.dodge_attempts}</code>\n"
        f"❌ Последний додж: <code>{runtime.last_dodge}</code>\n"
        f"✅ Последний успешный додж: <code>{runtime.last_succ_dodge}</code>\n\n"
        f"🏹 Колчан: <code>{runtime.has_quiver}</code>\n"
        f"🗺 Маппинг: <code>{runtime.last_mapping}</code>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=window_screenshot_kb(nick),
        parse_mode="HTML"
    )

@router.callback_query(lambda c: c.data == "menu_back")
@admin_only
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("🏥 Главное меню:", reply_markup=main_menu_kb())
