from typing import Optional
from aiogram.types import InputFile, ReplyKeyboardMarkup, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from tgbot.config import config, notify_levels
from clogger import log

class Notifier:
    _levels = {
        "info": "ℹ️ INFO",
        "warning": "⚠️ WARNING",
        "error": "❌ ERROR",
        "trash": "🗑️ TRASH",
        "photo": "📷 PHOTO",
    }

    def __init__(self, bot):
        self.bot = bot

    async def send_notification(
        self,
        level: str,
        text: str,
        parse_mode: ParseMode | str = ParseMode.HTML,
        reply_markup: Optional[ReplyKeyboardMarkup | InlineKeyboardMarkup] = None,
        nickname: Optional[str] = None,
    ):
        if not notify_levels.get(level.lower(), False):
            return

        prefix = self._levels.get(level.lower(), "?")
        message_text = f"<tg-spoiler>{prefix}</tg-spoiler>\n"

        if nickname:
            message_text += f"<code>{nickname}</code>\n\n"

        message_text += f"<b>{text}</b>"

        for admin_id in config.ADMINS:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            except Exception as e:
                log(f"Ошибка отправки в тг | {admin_id} | {e}")

    async def send_photo(
        self,
        photo: str | InputFile,
        caption: Optional[str] = None,
        level: str = "photo",
        nickname: Optional[str] = None,
        parse_mode="HTML",
        reply_markup: Optional[ReplyKeyboardMarkup | InlineKeyboardMarkup] = None,
    ):
        if not notify_levels.get(level.lower(), False):
            return

        prefix = self._levels.get(level.lower(), "?")
        message_text = f"<tg-spoiler>{prefix}</tg-spoiler>\n"

        if nickname:
            message_text += f"<code>{nickname}</code>\n\n"

        if caption:
            message_text += f"<b>{caption}</b>"

        for admin_id in config.ADMINS:
            try:
                await self.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo,
                    caption=message_text if caption else None,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            except Exception as e:
                log(f"Ошибка отправки фото в тг | {admin_id} | {e}")
