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
        if cls._instance is not None:
            return cls._instance

        inst = super().__new__(cls)
        inst.loop = asyncio.get_running_loop()
        inst.bot = None
        inst.dp = None
        inst.notifier = None

        if config.STATE is False:
            log(f"TG offed | L2Monad", context="TG")
            cls._instance = inst
            return inst

        try:
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

            inst.bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode="HTML"),
                session=s,
            )
            asyncio.run_coroutine_threadsafe(setup_bot(inst.bot), inst.loop)
            inst.dp = Dispatcher()
            for r in all_routers:
                inst.dp.include_router(r)
            inst.notifier = Notifier(inst.bot)
            log(f"TG started successfully | L2Monad", context="TG")
        except Exception as e:
            log(f"TG init FAILED: {e} | L2Monad", context="TG", level="ERROR")
            config.STATE = False

        cls._instance = inst
        return inst

    def send_notification(self, *args, **kwargs):
        if config.STATE is True and self.notifier is not None:
            asyncio.run_coroutine_threadsafe(
                self.notifier.send_notification(*args, **kwargs),
                self.loop
            )

    def send_pic(self, *args, **kwargs):
        if config.STATE is True and self.notifier is not None:
            asyncio.run_coroutine_threadsafe(
                self.notifier.send_photo(*args, **kwargs),
                self.loop
            )

    def start_polling(self):
        if config.STATE is True and self.dp is not None and self.bot is not None:
            fut = asyncio.run_coroutine_threadsafe(
                self.dp.start_polling(self.bot),
                self.loop
            )
            fut.add_done_callback(self._polling_done)

    def _polling_done(self, fut):
        try:
            exc = fut.exception()
            if exc:
                log(f"TG polling died: {exc}", context="TG", level="ERROR")
        except Exception:
            pass