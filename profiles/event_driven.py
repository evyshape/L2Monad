import asyncio
from typing import Optional

from bot.clogger import log
from bot.events.enums import MonitorType, PRIORITIES
from profiles.base import BaseProfile


class EventDrivenProfile(BaseProfile):

    EVENT_HANDLERS: dict = {}

    def __init__(self, window_info, settings=None):
        super().__init__(window_info, settings=settings)
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._event_worker_task: Optional[asyncio.Task] = None
        self._current_event_task: Optional[asyncio.Task] = None
        self._event_counter: int = 0

    async def _event_worker(self) -> None:
        while self.running:
            priority, _seq, event = await self._event_queue.get()

            if self._current_event_task and not self._current_event_task.done():
                log(f"Отмена / {priority}", self.window_id)
                self._current_event_task.cancel()
                try:
                    await self._current_event_task
                except asyncio.CancelledError:
                    pass

            self._current_event_task = asyncio.create_task(self._process_event(event))

            try:
                await self._current_event_task
            except asyncio.CancelledError:
                log("Обработка прервана, чини", self.window_id)
            except Exception as e:
                log(f"Ошибка обработки: {e}", self.window_id)
                monitors = getattr(self, "get_monitors", None)
                if monitors:
                    self.events_checker.start_monitoring(self.window_id, self, monitors=monitors)

            self._event_queue.task_done()

    async def _process_event(self, event: dict) -> None:
        etype = event.get("type")
        desc = event.get("desc")
        if desc:
            log(f"Обработка: {etype} ({desc})", self.window_id)
        else:
            log(f"Обработка: {etype}", self.window_id)

        if etype == "error" and desc is not None:
            await self.handle_error(desc)
            return

        handler_name = self.EVENT_HANDLERS.get(etype)
        if handler_name is None:
            log(f"Шось страшное и необработанное: {etype}", self.window_id)
            return

        await getattr(self, handler_name)()

    async def handle_error(self, desc):
        log(f"Необработанный error event: {desc}", self.window_id)

    def send_event(self, event: dict) -> None:
        if not self.running:
            return
        etype = event.get("type")
        priority = PRIORITIES.get(MonitorType(etype), 999)
        self._event_counter += 1
        self._event_queue.put_nowait((priority, self._event_counter, event))
        log(f"Ивент {etype} добавлен в очередь с приоритетом {priority}", self.window_id)

    def is_running(self):
        return self.running
