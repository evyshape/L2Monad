import asyncio
import requests
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from tgbot.config import config
from tgbot.services.notifier import Notifier
from tgbot.handlers import all_routers
from tgbot.services.setup import setup_bot
from bot.clogger import log

class TgBot:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.loop = asyncio.get_running_loop()

            if config.STATE is False:
                log(
                    f"TG offed | L2Monad",
                    context="TG"
                )
                return cls._instance

            s = None
            if config.proxy_url:
                try:
                    proxies = {"http": config.proxy_url, "https": config.proxy_url}
                    resp = requests.get(
                        "https://api.telegram.org",
                        proxies=proxies,
                        timeout=5
                    )
                    if resp.status_code == 200:
                        log(f"Proxy: {resp.status_code}")
                        s = AiohttpSession(proxy=config.proxy_url)
                    else:
                        log(f"Proxy FAIL: {resp.status_code}")
                        config.PROXY_HOST = None

                except Exception as e:
                    log(f"Proxy ERROR: {e}")
                    config.PROXY_HOST = None

            cls._instance.bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode="HTML"),
                session=s,
            )
            asyncio.run_coroutine_threadsafe(
                setup_bot(cls._instance.bot),
                cls._instance.loop
            )
            cls._instance.dp = Dispatcher()
            for r in all_routers:
                cls._instance.dp.include_router(r)
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

    def send_pic(self, *args, **kwargs):
        if config.STATE is True:
            asyncio.run_coroutine_threadsafe(
                self.notifier.send_photo(*args, **kwargs),
                self.loop
            )

    def start_polling(self):
        if config.STATE is True:
            asyncio.run_coroutine_threadsafe(
                self.dp.start_polling(self.bot),
                self.loop
            )