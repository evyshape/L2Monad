import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from tgbot.config import config
from tgbot.services.notifier import Notifier
from tgbot.handlers.start import router as start_router
from tgbot.handlers.menu import router as menu_router
from tgbot.handlers.manage import router as manage_router
from tgbot.services.setup import setup_bot
from clogger import log

class TgBot:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.loop = asyncio.get_event_loop()

            if config.STATE is False:
                log(
                    f"TG offed | L2Monad",
                    context="TG"
                )
                return cls._instance

            request_kwargs = {}
            if config.proxy_url:
                request_kwargs["proxy"] = config.proxy_url

            cls._instance.bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode="HTML"),
                **request_kwargs
            )
            asyncio.run_coroutine_threadsafe(
                setup_bot(cls._instance.bot),
                cls._instance.loop
            )
            cls._instance.dp = Dispatcher()
            cls._instance.dp.include_router(manage_router)
            cls._instance.dp.include_router(menu_router)
            cls._instance.dp.include_router(start_router)
            cls._instance.notifier = Notifier(cls._instance.bot)
            log(
                f"TG started successfully | L2Monad",
                context="TG"
            )

        return cls._instance

    def send_notification(self, *args, **kwargs):
        if config.STATE is True:
            asyncio.run_coroutine_threadsafe(
                self.notifier.send_notification(*args, **kwargs),
                self.loop
            )

    def start_polling(self):
        if config.STATE is True:
            asyncio.run_coroutine_threadsafe(
                self.dp.start_polling(self.bot),
                self.loop
            )