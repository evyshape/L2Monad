import asyncio
from profiles.base import BaseProfile
from bot.methods.other import MouseEvents
from bot.methods.game import claim_mail, check_energo_mode, energo_mode, claim_daily, \
    claim_achiv, claim_clan, claim_battle_pass, claim_donate_shop
from clogger import log
from bot.windows.runtime import RuntimeData

class Rewards(BaseProfile):
    def __init__(self, window_info, settings=None):
        super().__init__(window_info, settings=settings)
        self.mouse = MouseEvents()
        self._child_tasks = []
        self.runtime_data = RuntimeData(current_state="afk")

    def profile_version(self):
        return "1.0"

    def profile_name(self):
        return "Rewards"

    async def main_loop(self):
        window_id = next(iter(self.window_info))

        try:
            claimed_daily = await claim_daily(self)
            if claimed_daily:
                log(f"Дейлик успешно собран", window_id)
            else:
                log(f"Нет новых дейликов или не удалось собрать", window_id)

            claimed_mail = await claim_mail(self)
            if claimed_mail:
                log(f"Почта успешно собрана", window_id)
            else:
                log(f"Нет новой почты или не удалось собрать", window_id)

            claimed_achiv = await claim_achiv(self)
            if claimed_achiv:
                log(f"Ачивы успешно собраны", window_id)
            else:
                log(f"Нет новых ачивок или не удалось собрать", window_id)

            claimed_clan = await claim_clan(self)
            if claimed_clan:
                log(f"Клан успешно собран", window_id)
            else:
                log(f"Нет новых донатов в клан или не удалось вдонить", window_id)

            claimed_bp = await claim_battle_pass(self)
            if claimed_bp:
                log(f"Пасс успешно собран", window_id)
            else:
                log(f"Не смог собрать пасс", window_id)

            claimed_shop = await claim_donate_shop(self)
            if claimed_shop:
                log(f"Шоп успешно собран", window_id)
            else:
                log(f"Не смог собрать шоп", window_id)

            if not await check_energo_mode(self):
                energomode = await energo_mode(self, "on")

            await asyncio.sleep(1)

        except asyncio.CancelledError:
            log(f"Профиль остановлен вручную", window_id)
            raise

    async def on_stop(self):
        await super().on_stop()
        for task in self._child_tasks:
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)
