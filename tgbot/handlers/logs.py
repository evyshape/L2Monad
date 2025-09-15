from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile
from tgbot.keyboards.logs import main_logs_kb
from tgbot.keyboards.screenshot import delete_screenshot_kb
from tgbot.services.decorators import admin_only
from bot.utils import getLogs
import os

router = Router()


@router.message(Command("logs"))
@admin_only
async def logs_command(message: types.Message):
    await message.answer("📑 Доступные логи:", reply_markup=main_logs_kb())


@router.callback_query(F.data.startswith("logs_page_"))
@admin_only
async def logs_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await callback.message.edit_text(
        "📑 Доступные логи:",
        reply_markup=main_logs_kb(page)
    )


@router.callback_query(F.data.startswith("open_log_"))
@admin_only
async def open_log(callback: CallbackQuery):
    filename = callback.data.split("open_log_", 1)[1]

    logs = getLogs()
    en = next((l for l in logs if l["Name"] == filename), None)

    if not en:
        await callback.answer("❌ Файл не найден", show_alert=True)
        return

    p = en["Path"]
    if not os.path.exists(p):
        await callback.answer("❌ Файл отсутствует", show_alert=True)
        return

    preview = []
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            preview = lines[-8:] if len(lines) > 8 else lines
    except Exception as e:
        preview = [f"⚠️ Ошибка: {e}"]

    preview_t = "".join(preview).strip() + "\n"

    await callback.message.answer_document(FSInputFile(p), caption=f"📄 <b>{filename}</b>\n<pre>{preview_t}</pre>", parse_mode="HTML", reply_markup=delete_screenshot_kb())
    await callback.answer()
