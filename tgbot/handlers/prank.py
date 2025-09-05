from aiogram import Router
from aiogram.types import CallbackQuery
from tgbot.keyboards.prank import prank_kb
from tgbot.keyboards.screenshot import window_screenshot_kb
from tgbot.keyboards.menu import main_menu_kb
from tgbot.services.decorators import admin_only
from bot.controller import ProfileController
from tgbot.keyboards.windows import window_back_kb

router = Router()
controller = ProfileController()

# Stage1
@router.callback_query(lambda c: c.data.startswith("prank_start_") and "_1" in c.data)
@admin_only
async def prank_stage1(callback: CallbackQuery):
    nick = callback.data.split("_")[2]
    await callback.message.edit_text(
        f"🔎 Вы точно хотите закрыть окно {nick}?",
        reply_markup=prank_kb(nick, stage=1)
    )

# Stage2
@router.callback_query(lambda c: c.data.startswith("prank_start_") and "_2" in c.data)
@admin_only
async def prank_stage2(callback: CallbackQuery):
    nick = callback.data.split("_")[2]
    await callback.message.edit_text(
        f"☝️ Отлично! Теперь убедитесь еще раз...",
        reply_markup=prank_kb(nick, stage=2)
    )

# Stage3
@router.callback_query(lambda c: c.data.startswith("prank_start_") and "_3" in c.data)
@admin_only
async def prank_stage3(callback: CallbackQuery):
    nick = callback.data.split("_")[2]
    await callback.message.edit_text(
        "🔎 Отлично!\n😢 Правда жаль что ты не читаешь это сообщение...\n☝️ Теперь нужно выбрать крестик если ты действительно хочешь закрыть окно",
        reply_markup=prank_kb(nick, stage=3)
    )

@router.callback_query(lambda c: c.data.startswith("prank_start_") and "_done" in c.data)
@admin_only
async def prank_done(callback: CallbackQuery):
    nick = callback.data.split("_")[2]
    controller.close_window(nick)
    await callback.answer(f"🛑 Закрыл окно {nick}", show_alert=True)
    await callback.message.edit_text(
        f"🏥 Главное меню:",
        reply_markup=main_menu_kb()
    )

@router.callback_query(lambda c: c.data.startswith("prank_start_") and "_info" in c.data)
@admin_only
async def prank_info(callback: CallbackQuery):
    nick = callback.data.split("_")[2]
    await callback.answer(f"✅ Отменил закрытие окна")
    await window_info_cb(callback, nick)

async def window_info_cb(callback: CallbackQuery, nick: str):
    runtime = controller.get_runtime_info(nick)
    if not runtime:
        await callback.message.edit_text(
            f"❌ Нет данных для окна <b>{nick}</b>\n"
            f"❌ Возможно оно не запущено?",
            reply_markup=window_back_kb(),
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
