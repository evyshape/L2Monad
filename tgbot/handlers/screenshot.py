from aiogram import Router
from aiogram.types import CallbackQuery
from tgbot.services.decorators import admin_only
from bot.utils import findAllWindows
from bot.methods.other import screenshot_window
from tgbot.keyboards.windows import window_back_kb

router = Router()

@router.callback_query(lambda c: c.data.startswith("screenshot_"))
@admin_only
async def take_screenshot(callback: CallbackQuery):
    from tgbot.bot import TgBot
    bot_instance = TgBot()
    nick = callback.data.split("_", 1)[1]
    windows_info = findAllWindows()

    if nick not in windows_info:
        await callback.message.edit_text(
            f"❌ Нет данных для окна <b>{nick}</b>",
            reply_markup=window_back_kb(),
            parse_mode="HTML"
        )
        return

    photo = screenshot_window({nick: windows_info[nick]}, tg=True)
    bot_instance.send_pic(photo=photo, caption="Скриншот готов!", parse_mode="HTML", nickname=nick)
    await callback.answer("✅", show_alert=False)
