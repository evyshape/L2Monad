import random

from profiles.base import BaseProfile
from bot.methods.other import MouseEvents
from bot.methods.game import auction_rereg, energo_mode, check_energo_mode
from bot.clogger import log
import asyncio


class Auction(BaseProfile):
    def __init__(self, window_info, settings=None):
        from tgbot.bot import TgBot
        super().__init__(window_info, settings=settings)
        self.mouse = MouseEvents()
        self._child_tasks = []
        self.tgbot = TgBot()

    def profile_version(self):
        return "1.0.0"

    def profile_name(self):
        return "Auction Rereger"

    async def main_loop(self):
        window_id = next(iter(self.window_info))
        try:
            x = await check_energo_mode(self)
            if x:
                await energo_mode(self, "off")
                await asyncio.sleep(1)

            rereged = await auction_rereg(self)

            if not rereged:
                log("Шось сломалось либо не смог перевыставить аук", window_id)

            if x:
                await asyncio.sleep(random.randint(1, 5))
                await energo_mode(self, "on")
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            log("Профиль остановлен вручную", window_id)
            raise

    async def on_stop(self):
        for task in self._child_tasks:
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)
        await super().on_stop()

    def is_running(self):
        return self.running