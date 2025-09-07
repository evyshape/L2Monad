from profiles.base import BaseProfile
from bot.methods.other import MouseEvents
from bot.methods.game import get_npc_positions
from bot.clogger import log
import asyncio


class Test(BaseProfile):
    def __init__(self, window_info, settings=None):
        from tgbot.bot import TgBot
        super().__init__(window_info, settings=settings)
        self.mouse = MouseEvents()
        self._child_tasks = []
        self.tgbot = TgBot()

    def profile_version(self):
        return "2.2.8"

    def profile_name(self):
        return "Test gamno"

    async def main_loop(self):
        window_id = next(iter(self.window_info))
        try:
            ggggg = await get_npc_positions(self)

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