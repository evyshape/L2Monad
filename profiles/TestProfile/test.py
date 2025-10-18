from bot.windows.runtime import RuntimeData
from profiles.base import BaseProfile
from bot.methods.other import MouseEvents
from bot.methods.game import check_disconnect, connect_to_server, energo_mode, get_npc_positions
from bot.events.checker import EventsChecker
from bot.events.enums import MonitorType, PRIORITIES
from bot.clogger import log
import asyncio
from typing import Optional


class Test(BaseProfile):
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
        return "2.2.8"

    def profile_name(self):
        return "Test gamno"

    async def main_loop(self):
        window_id, window = next(iter(self.window_info.items()))
        try:
            #self.events_checker.start_monitoring(window_id, self,
            #                                     monitors=[MonitorType.ERROR])

            #while True:
            #    await asyncio.sleep(0.1)
            #    pass

            npc = await get_npc_positions(self)
            log(npc, window_id)

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

        if etype == "error":
            pass

    def send_event(self, event: dict) -> None:
        window_id = next(iter(self.window_info))
        etype = event.get("type")
        priority = PRIORITIES.get(MonitorType(etype), 999)
        self._event_queue.put_nowait((priority, event))
        log(f"Ивент {etype} добавлен в очередь с приоритетом {priority}", window_id)

    def is_running(self):
        return self.running