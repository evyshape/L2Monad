from bot.windows.runtime import RuntimeData
from profiles.base import BaseProfile
from bot.methods.other import MouseEvents, screenshot_window
from bot.methods.game import autohunt, buy_in_shop, energo_mode, \
    PartyDungeon, check_energo_mode, safe_tp, check_autohunt, check_rip, wait_teleport, \
    teleport_to_random_spot
from tgbot.keyboards.screenshot import delete_screenshot_kb
from bot.events.checker import EventsChecker
from bot.events.enums import MonitorType, PRIORITIES
from bot.misc import *
from bot.clogger import log
import asyncio
from typing import Optional


class Dungeon(BaseProfile):
    def __init__(self, window_info, settings=None):
        from tgbot.bot import TgBot
        super().__init__(window_info, settings=settings)
        self.events_checker = EventsChecker()
        self.mouse = MouseEvents()
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._event_worker_task: Optional[asyncio.Task] = None
        self._current_event_task: Optional[asyncio.Task] = None
        self._child_tasks = []
        self.tgbot = TgBot()
        self.runtime_data = RuntimeData(current_state="null")

    def profile_version(self):
        return "1.0.0"

    def profile_name(self):
        return "Party Dungeon"

    async def main_loop(self):
        window_id, window = next(iter(self.window_info.items()))
        try:
            flaged = False
            energo = await check_energo_mode(self)
            if energo:
                flaged = True
                #await energo_mode(self, "off")
                await asyncio.sleep(0.1)

            await safe_tp(self)
            await asyncio.sleep(1.5)
            await wait_teleport(self)
            dungeon = PartyDungeon(self)
            await dungeon.open_dungeon()
            await asyncio.sleep(1.5)
            xy = await dungeon.find_dungeon()
            if not xy:
                log("Не нашел данжик, выхожу", window_id)
                await dungeon.wait_and_click("main_menu_gui")
                await asyncio.sleep(1)

                if NEED_BACK_TO_SPOT_PARTY_DUNGEON:
                    to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
                    if to_spot:
                        return True
                    return False

                if flaged:
                    await energo_mode(self, "on")
                    return False

            started = await dungeon.start_dungeon(xy)
            if started:
                await autohunt(self)
                to_back = await dungeon.no_limit() # энерго включено клики в dungeon.cliks
                self.events_checker.start_monitoring(window_id, self, monitors=[MonitorType.DEATH])
                log(to_back, window_id)
                while True:
                    hunt = await check_autohunt(self)
                    log(hunt, window_id)
                    if not hunt:
                        self.events_checker.stop_monitoring(window_id)
                        rip, btn = await check_rip(self)
                        if rip:
                            log("Анлука, помер во время пати данжа. оффаюсь", window_id)
                            return

                        break

                    await asyncio.sleep(10)

                log("Успешно пробежал пати данжик закуплюсь и оффаюсь", window_id)
                if await check_energo_mode(self):
                    await energo_mode(self, "off", ignore=True)
                    await asyncio.sleep(1)

                    if self.settings.TELEGRAM_NOTIFIES:
                        screenn = screenshot_window(self.window_info, tg=True)
                        self.tgbot.send_pic(
                            photo=screenn,
                            caption=f"Закачал пати данжик, закуплюсь и оффнусь =)",
                            parse_mode="HTML",
                            nickname=window_id,
                            reply_markup=delete_screenshot_kb()
                        )

                await self.mouse.click(self.window_info, 200, 100)

                await dungeon.to_start()
                await dungeon.party_leave()

                ok, in_town, npcs = await buy_in_shop(self)
                log(f"ok={ok}, town={in_town}", window_id)

                if NEED_BACK_TO_SPOT_PARTY_DUNGEON:
                    to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
                    if to_spot:
                        return True
                    return False

                if not await check_energo_mode(self):
                    await energo_mode(self, "on", ignore=True)
                    await asyncio.sleep(1)

                if ok:
                    return True

                return False

        except asyncio.CancelledError:
            log("Профиль остановлен вручную", window_id)
            raise

    async def on_stop(self):
        for task in self._child_tasks:
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)
        await super().on_stop()

    async def _event_worker(self) -> None:
        window_id = next(iter(self.window_info))
        while self.running:
            priority, event = await self._event_queue.get()

            if self._current_event_task and not self._current_event_task.done():
                log(f"Отмена / {priority}", window_id)
                self._current_event_task.cancel()
                try:
                    await self._current_event_task
                except asyncio.CancelledError:
                    pass

            self._current_event_task = asyncio.create_task(self._process_event(event))

            try:
                await self._current_event_task
            except asyncio.CancelledError:
                log("Обработка прервана, чини", window_id)

            self._event_queue.task_done()

    async def _process_event(self, event: dict) -> None:
        window_id = next(iter(self.window_info))
        etype = event.get("type")
        desc = event.get("desc")
        log(f"Обработка: {etype} ({desc})", window_id)

        if etype == "death":
            log("_Анлука, помер во время пати данжа. оффаюсь", window_id)
            return

    def send_event(self, event: dict) -> None:
        window_id = next(iter(self.window_info))
        etype = event.get("type")
        priority = PRIORITIES.get(MonitorType(etype), 999)
        self._event_queue.put_nowait((priority, event))
        log(f"Ивент {etype} добавлен в очередь с приоритетом {priority}", window_id)

    def is_running(self):
        return self.running