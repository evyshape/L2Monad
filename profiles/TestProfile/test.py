from profiles.base import BaseProfile
from bot.methods.other import MouseEvents
from bot.methods.game import buy_loot
from clogger import log
import asyncio
from bot.windows.runtime import RuntimeData

class Test(BaseProfile):
    def __init__(self, window_info, settings=None):
        super().__init__(window_info, settings=settings)
        self.mouse = MouseEvents()  # мышильда
        self._child_tasks = []
        self.runtime_data = RuntimeData(current_state="null")

    def profile_version(self):
        return "2.2.8"

    def profile_name(self):
        return "Test gamno"

    async def main_loop(self):
        window_id = next(iter(self.window_info))
        try:
            result = await buy_loot(self)
            if result:
                log(result)

        except asyncio.CancelledError:
            log(f"Профиль остановлен вручную, оу ноу...", window_id)
            raise

    async def on_stop(self):
        await super().on_stop()
        for task in self._child_tasks:
            log("Ликвидировал дочерний таск")
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)