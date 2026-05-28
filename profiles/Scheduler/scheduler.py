import asyncio

from bot.clogger import log
from profiles.base import BaseProfile


class Scheduler(BaseProfile):

    def profile_version(self):
        return "1.0.0"

    def profile_name(self):
        return "Scheduler"

    async def main_loop(self):
        try:
            log("Запуск Scheduler профиля", self.window_id)

            #if await self.energo.is_on():
            #    await self.energo.turn_off()

            await self.tp.safe_home()
            await self.tp.wait_arrived()

            sch = self.scheduler

            if not await sch.wait_and_click("main_menu_gui", timeout=7):
                log("Не открыл главное меню", self.window_id)
                self.notify("error", "Scheduler: не открыл главное меню")
                return

            if not await sch.wait_and_click("schedule_menu", timeout=5):
                log("Не нашёл schedule_menu", self.window_id)
                self.notify("error", "Scheduler: schedule_menu не найден")
                return

            await asyncio.sleep(1)

            if not await sch.wait_and_click("schedule_start", timeout=5):
                log("Не смог запустить schedule", self.window_id)
                self.notify("error", "Scheduler: schedule_start не нажалась")
                return

            log("Schedule запущен, жду 15 сек до включения энерго", self.window_id)
            await asyncio.sleep(30)

            await self.energo.turn_on()
            log("Энерго включён, профиль завершён", self.window_id)
            self.notify("info", "Расписание запущено, энерго включён")

        except asyncio.CancelledError:
            log("Scheduler остановлен вручную", self.window_id)
            raise
