from profiles.base import BaseProfile
from bot.methods.other import MouseEvents
from bot.methods.game import buy_in_shop, safe_tp, check_energo_mode, \
    energo_mode, wait_teleport, sell_buyer, go_stash, teleport_to_random_spot
from clogger import log
import asyncio
from bot.windows.runtime import RuntimeData

class Buyer(BaseProfile):
    def __init__(self, window_info, settings=None):
        super().__init__(window_info, settings=settings)
        self.mouse = MouseEvents()  # мышильда
        self._child_tasks = []
        self.runtime_data = RuntimeData(current_state="null")

    def profile_version(self):
        return "1.0"

    def profile_name(self):
        return "Buyer"

    async def main_loop(self):
        window_id = next(iter(self.window_info))
        try:
            tp = await safe_tp(self)
            if tp:
                wait = await wait_teleport(self)
                if wait:
                    result0 = await go_stash(self)
                    result1 = await buy_in_shop(self)
                    result2 = await sell_buyer(self)
                    if result0:
                        log(f"{result0}", window_id)
                        await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
                    else:
                        log(f"Не смог закупиться", window_id)
            else:
                log(f"Не тпнулся?", window_id)

        except asyncio.CancelledError:
            log(f"Профиль остановлен вручную", window_id)
            raise

    async def on_stop(self):
        window_id = next(iter(self.window_info))
        log("Stopped =(", window_id)
        await super().on_stop()
        for task in self._child_tasks:
            log("Ликвидировал дочерний таск", window_id)
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)