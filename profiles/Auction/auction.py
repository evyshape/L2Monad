import random

from profiles.base import BaseProfile
from bot.clogger import log
import asyncio


class Auction(BaseProfile):
    def __init__(self, window_info, settings=None):
        super().__init__(window_info, settings=settings)

    def profile_version(self):
        return "1.0.0"

    def profile_name(self):
        return "Auction Rereger"

    async def main_loop(self):
        window_id = self.window_id
        try:
            x = await self.energo.is_on()
            if x:
                await self.energo.turn_off()
                await asyncio.sleep(1)

            rereged = await self.auction.reregister()

            if not rereged:
                log("Шось сломалось либо не смог перевыставить аук", window_id)

            if x:
                await asyncio.sleep(random.randint(1, 5))
                await self.energo.turn_on()
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