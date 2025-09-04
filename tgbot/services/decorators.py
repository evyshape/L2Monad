from functools import wraps
from aiogram.types import Message
from tgbot.config import config


def admin_only(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id not in config.ADMINS:
            await message.answer("🚫 Тiкай з села")
            return
        return await handler(message, *args, **kwargs)

    return wrapper

def only_on(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not config.STATE:
            return
        return await func(*args, **kwargs)
    return wrapper