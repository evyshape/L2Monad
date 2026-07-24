import asyncio

from bot.clogger import log

from profiles.base import BaseProfile
from bot.windows.runtime import RuntimeData
from bot.events.enums import BotState, NotifyLevel


class Rewards(BaseProfile):
    def __init__(self, window_info, settings=None):
        super().__init__(window_info, settings=settings)
        self.runtime_data = RuntimeData(current_state=BotState.AFK)

    def profile_version(self):
        return "1.0"

    def profile_name(self):
        return "Rewards"

    async def main_loop(self):
        rewards = [
            (self.settings.NEED_CLAIM_DAILY, "Дейлик", self.claims.daily),
            (self.settings.NEED_CLAIM_MAIL, "Почта", self.claims.mail),
            (self.settings.NEED_CLAIM_ACHIV, "Ачивы", self.claims.achievements),
            (self.settings.NEED_CLAIM_CLAN, "Клан", self.claims.clan),
            (self.settings.NEED_CLAIM_ALI, "Альянс", self.claims.alliance),
            (self.settings.NEED_CLAIM_BATTLE_PASS, "Пасс", self.claims.battle_pass),
            (self.settings.NEED_CLAIM_DONATE_SHOP, "Шоп", self.claims.donate_shop),
        ]

        try:
            for need_claim, name, func in rewards:
                if need_claim:
                    if await func():
                        log(f"{name} успешно собран", self.window_id)
                    else:
                        log(f"Нет новых {name.lower()} или не удалось собрать",
                            self.window_id)

            if not await self.energo.is_on():
                await self.energo.turn_on()

            self.notify(NotifyLevel.INFO, "Успешно собрал награды")

            await asyncio.sleep(1)

        except asyncio.CancelledError:
            log(f"Профиль остановлен вручную", self.window_id)
            raise

    async def on_stop(self):
        self.running = False
        await super().on_stop()
        for task in self._child_tasks:
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)

    def is_running(self) -> bool:
        return self.running
