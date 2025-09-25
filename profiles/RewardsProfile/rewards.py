import asyncio

from bot.clogger import log

from profiles.base import BaseProfile
from bot.methods.other import MouseEvents
from bot.methods.game import (
    claim_mail,
    check_energo_mode,
    energo_mode,
    claim_daily,
    claim_achiv,
    claim_clan,
    claim_alliance,
    claim_battle_pass,
    claim_donate_shop,
)
from bot.windows.runtime import RuntimeData
from bot.misc import *


class Rewards(BaseProfile):
    def __init__(self, window_info, settings=None):
        from tgbot.bot import TgBot
        super().__init__(window_info, settings=settings)
        self.mouse = MouseEvents()
        self._child_tasks = []
        self.runtime_data = RuntimeData(current_state="afk")
        self.tgbot = TgBot()

    def profile_version(self):
        return "1.0"

    def profile_name(self):
        return "Rewards"

    async def main_loop(self):
        window_id = next(iter(self.window_info))

        rewards = {
            "Дейлик": (NEED_CLAIM_DAILY, claim_daily),
            "Почта": (NEED_CLAIM_MAIL, claim_mail),
            "Ачивы": (NEED_CLAIM_ACHIV, claim_achiv),
            "Клан": (NEED_CLAIM_CLAN, claim_clan),
            "Альянс": (NEED_CLAIM_ALI, claim_alliance),
            "Пасс": (NEED_CLAIM_BATTLE_PASS, claim_battle_pass),
            "Шоп": (NEED_CLAIM_DONATE_SHOP, claim_donate_shop),
        }

        try:
            for name, (need_claim, func) in rewards.items():
                if need_claim:
                    claimed = await func(self)
                    if claimed:
                        log(f"{name} успешно собран", window_id)
                    else:
                        log(f"Нет новых {name.lower()} или не удалось собрать",
                            window_id)

            if not await check_energo_mode(self):
                await energo_mode(self, "on")

            self.tgbot.send_notification(
                level="info",
                text="Успешно собрал награды",
                nickname=window_id,
            )

            await asyncio.sleep(1)

        except asyncio.CancelledError:
            log(f"Профиль остановлен вручную", window_id)
            raise

    async def on_stop(self):
        self.running = False
        await super().on_stop()
        for task in self._child_tasks:
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)

    def is_running(self) -> bool:
        return self.running