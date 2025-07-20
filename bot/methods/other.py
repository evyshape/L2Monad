import asyncio
import functools
import time
from collections import deque
from clogger import log
from interception import inputs
from bot.limits import click_semaphore, swipe_semaphore, move_semaphore, max_swipes

def move_mouse(window_info, x_offset, y_offset):
    window_id, window = next(iter(window_info.items()))
    x_pos, position_y = window["Position"]
    abs_x = x_pos + x_offset
    abs_y = position_y + y_offset
    inputs.move_to(abs_x, abs_y)
    time.sleep(0.01)

def click_mouse(window_info, x_offset, y_offset, button="left"):
    window_id, window = next(iter(window_info.items()))
    x_pos, position_y = window["Position"]
    abs_x = x_pos + x_offset
    abs_y = position_y + y_offset
    inputs.move_to(abs_x, abs_y)
    time.sleep(0.05)
    inputs.mouse_down(button)
    time.sleep(0.01)
    inputs.mouse_up(button)
    return True

class MouseEvents:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            log("Создал мышь")
            cls._instance = super(MouseEvents, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return

        log("Инициализировал созданную мышь!")
        inputs.auto_capture_devices(keyboard=True, mouse=True)

        self.normal_queue = deque()
        self.fast_queue = deque()
        self.queue_not_empty = asyncio.Condition()

        self.clear = False
        self.wtask = asyncio.create_task(self._worker_loop())
        self._initialized = True
        self.tname = "-MouseEvents-"
        log("Готов к кликам и движениям", self.tname)

    async def click(self, window_info, x_offset, y_offset, button="left", fast=False):
        done_event = asyncio.Event()
        task = ("click", window_info, x_offset, y_offset, button, done_event)
        await self._add_task(task, fast)
        await done_event.wait()
        return True

    async def move_to(self, window_info, x_offset, y_offset):
        done_event = asyncio.Event()
        await self._add_task(("move", window_info, x_offset, y_offset, done_event))
        await done_event.wait()

    async def mouse_down(self, button="left"):
        done_event = asyncio.Event()
        await self._add_task(("mouse_down", button, done_event))
        await done_event.wait()

    async def mouse_up(self, button="left"):
        done_event = asyncio.Event()
        await self._add_task(("mouse_up", button, done_event))
        await done_event.wait()

    async def swipe(self, window_info, points, delay_points=0.1):
        done_event = asyncio.Event()
        await self._add_task(("swipe", window_info, points, delay_points, done_event))
        await done_event.wait()

    def get_tasks(self):
        fast_names = [task[0] for task in self.fast_queue]
        normal_names = [task[0] for task in self.normal_queue]
        log(f"Обычных задач: {len(self.normal_queue)}, срочных задач: {len(self.fast_queue)}", self.tname)
        log(f"Текущие задачи в очереди: {fast_names + normal_names}", self.tname)

    async def _add_task(self, task, fast=False):
        async with self.queue_not_empty:
            if fast:
                self.fast_queue.append(task)
            else:
                self.normal_queue.append(task)
            self.queue_not_empty.notify()

    async def _worker_loop(self):
        while True:
            async with self.queue_not_empty:
                while not self.fast_queue and not self.normal_queue:
                    await self.queue_not_empty.wait()

                batch = []

                while self.fast_queue and len(batch) < 999:
                    batch.append(self.fast_queue.popleft())

                while self.normal_queue and len(batch) < 999:
                    batch.append(self.normal_queue.popleft())

            i = 0
            length = len(batch)

            while i < length:
                task = batch[i]
                action = task[0]

                if action == "swipe":
                    j = i
                    while j < length and batch[j][0] == "swipe":
                        j += 1

                    swipe_count = j - i
                    to_do = min(swipe_count, max_swipes)

                    for k in range(to_do):
                        await self._process_task(batch[i + k])

                    for k in range(to_do, swipe_count):
                        await self._add_task(batch[i + k])
                    i = j
                else:
                    await self._process_task(task)
                    i += 1

    async def _process_task(self, task):
        action = task[0]

        if action == "click":
            _, window_info, x_offset, y_offset, button, done_event = task
            self.clear = True
            try:
                await self._do_click(window_info, x_offset, y_offset, button)
            except Exception as e:
                log(f"[MouseEvents] Ошибка клика: {e}")
            finally:
                self.clear = False
                done_event.set()
                await asyncio.sleep(0.14)

        elif action == "move":
            _, window_info, x_offset, y_offset, done_event = task
            self.clear = True
            try:
                loop = asyncio.get_running_loop()
                async with move_semaphore:
                    await loop.run_in_executor(
                        None,
                        functools.partial(move_mouse, window_info, x_offset, y_offset)
                    )
            except Exception as e:
                log(f"Ошибка движения мыши: {e}", self.tname)
            finally:
                self.clear = False
                done_event.set()
                await asyncio.sleep(0.2)

        elif action == "mouse_down":
            _, button, done_event = task
            self.clear = True
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    functools.partial(inputs.mouse_down, button)
                )
            except Exception as e:
                log(f"Ошибка mouse_down: {e}", self.tname)
            finally:
                self.clear = False
                done_event.set()
                await asyncio.sleep(0.03)

        elif action == "mouse_up":
            _, button, done_event = task
            self.clear = True
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    functools.partial(inputs.mouse_up, button)
                )
            except Exception as e:
                log(f"Ошибка mouse_up: {e}", self.tname)
            finally:
                self.clear = False
                done_event.set()
                await asyncio.sleep(0.03)

        elif action == "swipe":
            _, window_info, points, delay_points, done_event = task
            self.clear = True
            try:
                loop = asyncio.get_running_loop()
                async with swipe_semaphore:
                    if not points:
                        done_event.set()
                        return

                    first_x, first_y = points[0]
                    await loop.run_in_executor(
                        None,
                        functools.partial(move_mouse, window_info, first_x, first_y)
                    )
                    await asyncio.sleep(0.08)

                    await loop.run_in_executor(None, functools.partial(inputs.mouse_down, "left"))

                    for x, y in points[1:]:
                        await loop.run_in_executor(
                            None,
                            functools.partial(move_mouse, window_info, x, y)
                        )
                        await asyncio.sleep(delay_points)

                    await loop.run_in_executor(None, functools.partial(inputs.mouse_up, "left"))

            except Exception as e:
                log(f"Ошибка swipe: {e}", self.tname)
            finally:
                self.clear = False
                done_event.set()
                await asyncio.sleep(0.09)

    async def _do_click(self, window_info, x_offset, y_offset, button):
        loop = asyncio.get_running_loop()
        async with click_semaphore:
            await loop.run_in_executor(
                None,
                functools.partial(click_mouse, window_info, x_offset, y_offset, button)
            )
