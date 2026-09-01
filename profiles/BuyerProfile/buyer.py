import asyncio

from bot.clogger import log

from profiles.base import BaseProfile


class Buyer(BaseProfile):
    def __init__(self, window_info, settings=None):
        super().__init__(window_info, settings=settings)

    def profile_version(self):
        return "1.0"

    def profile_name(self):
        return "Buyer"

    async def main_loop(self):
        window_id = self.window_id
        try:
            tp = await self.tp.safe_home()
            if tp:
                wait = await self.tp.wait_arrived()
                if wait:
                    stash_ok, shop_ok, buyer_ok = await self.town.visit_chain(check_loot=True)
                    if stash_ok or shop_ok or buyer_ok:
                        await self.tp.to_random_spot(self.settings.SPOT_OT, self.settings.SPOT_DO)
                    else:
                        log(f"Не смог закупиться", window_id)
            else:
                log(f"Не тпнулся?", window_id)

        except asyncio.CancelledError:
            log(f"Профиль остановлен вручную", window_id)
            raise

    async def on_stop(self):
        self.running = False
        window_id = self.window_id
        log("Stopped =(", window_id)
        await super().on_stop()
        for task in self._child_tasks:
            log("Ликвидировал дочерний таск", window_id)
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)

    def is_running(self):
        return self.running