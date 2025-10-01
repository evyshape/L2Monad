import asyncio
import datetime
import functools
import os
import time
import random
from collections import deque
import math

import mss
from aiogram.types import FSInputFile

from bot.clogger import log
from interception import inputs
from bot.limits import click_semaphore, swipe_semaphore, move_semaphore, max_swipes, curve
from bot.delays import CLICK_DELAY
from bot.constans import SCREENSHOT_DIR


def screenshot_window(window_info, tg: bool = False):
    window_id, window = next(iter(window_info.items()))
    x_pos, y_pos = window["Position"]
    width, height = map(int, window["Size"].split("x"))

    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{'send_tg_' if tg else ''}{window_id}_{now_str}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    with mss.mss() as sct:
        monitor = {"top": y_pos, "left": x_pos, "width": width, "height": height}
        sct_img = sct.grab(monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=filepath)

    if tg:
        return FSInputFile(filepath)
    return filepath

def curv(p0, p1, p2, steps=70):
    path = []
    for t in [i / steps for i in range(steps + 1)]:
        x = int((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0])
        y = int((1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])
        path.append((x, y))
    return path

def move_line(window_info, x_offset, y_offset, steps=55, delay=0.001):
    window_id, window = next(iter(window_info.items()))
    x_pos, y_pos = window["Position"]
    target_x = x_pos + x_offset
    target_y = y_pos + y_offset

    cur_x, cur_y = inputs.mouse_position()

    dx = (target_x - cur_x) / steps
    dy = (target_y - cur_y) / steps

    for i in range(steps):
        nx = int(cur_x + dx * (i + 1))
        ny = int(cur_y + dy * (i + 1))
        inputs.move_to(nx, ny)
        time.sleep(delay)

    inputs.move_to(target_x, target_y)


def move_human(window_info, x_offset, y_offset, curve=True):
    window_id, window = next(iter(window_info.items()))
    x_pos, y_pos = window["Position"]
    target_x = x_pos + x_offset
    target_y = y_pos + y_offset

    if not curve:
        inputs.move_to(target_x, target_y)
        return

    cur_x, cur_y = inputs.mouse_position()
    cp_x = cur_x + (target_x - cur_x) * random.uniform(0.3, 0.7) + random.randint(-50, 50)
    cp_y = cur_y + (target_y - cur_y) * random.uniform(0.3, 0.7) + random.randint(-50, 50)

    steps = random.randint(40, 55)
    path = curv((cur_x, cur_y), (cp_x, cp_y), (target_x, target_y), steps=steps)

    for i, (px, py) in enumerate(path):
        t = i / (len(path) - 1)
        adj_t = 0.5 * (1 - math.cos(math.pi * t))

        base_delay = 0.001
        delay = base_delay + (1 - adj_t) * random.uniform(0.0005, 0.001)

        j_x = px + random.randint(-1, 1)
        j_y = py + random.randint(-1, 1)

        inputs.move_to(j_x, j_y)
        time.sleep(delay)

    inputs.move_to(target_x, target_y)


def click_human(window_info, x_offset, y_offset, button="left"):
    move_human(window_info, x_offset, y_offset)
    time.sleep(random.uniform(0.05, 0.08))
    inputs.mouse_down(button)
    time.sleep(random.uniform(0.02, 0.04))
    inputs.mouse_up(button)
    return True

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
    time.sleep(0.03)
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

    async def swipe(self, window_info, points, delay_points=0.001, no_curve=False):
        done_event = asyncio.Event()
        await self._add_task(("swipe", window_info, points, delay_points, no_curve, done_event))
        await done_event.wait()

    async def wheel(self, window_info, points, direction: str = "up", times: int = 1, delay: float = 0.008):
        done_event = asyncio.Event()
        task = ("wheel", window_info, points, direction, times, delay, done_event)
        await self._add_task(task)
        await done_event.wait()

    async def key_press(self, key: str, fast=False, profile=None):
        done_event = asyncio.Event()
        task = ("key_press", key, done_event)
        if profile:
            await profile._activate()
        await self._add_task(task, fast)
        await done_event.wait()
        return True

    async def key_down(self, key: str, fast=False):
        done_event = asyncio.Event()
        task = ("key_down", key, done_event)
        await self._add_task(task, fast)
        await done_event.wait()

    async def key_up(self, key: str, fast=False):
        done_event = asyncio.Event()
        task = ("key_up", key, done_event)
        await self._add_task(task, fast)
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
                await asyncio.sleep(CLICK_DELAY)

        elif action == "move":
            _, window_info, x_offset, y_offset, done_event = task
            self.clear = True
            try:
                loop = asyncio.get_running_loop()
                async with move_semaphore:
                    await loop.run_in_executor(
                        None,
                        functools.partial(move_human if curve else move_mouse,
                                          window_info, x_offset, y_offset)
                    )
            except Exception as e:
                log(f"Ошибка движения мыши: {e}", self.tname)
            finally:
                self.clear = False
                done_event.set()
                await asyncio.sleep(0.2)

        elif action == "wheel":
            _, window_info, points, direction, times, delay, done_event = task
            self.clear = True
            try:
                loop = asyncio.get_running_loop()
                if points and len(points) > 0:
                    first_x, first_y = points[0]
                    await loop.run_in_executor(
                        None,
                        functools.partial(move_mouse, window_info, first_x, first_y)
                    )
                    await asyncio.sleep(0.07)

                for _ in range(times):
                    await loop.run_in_executor(None, functools.partial(inputs.scroll, direction))
                    await asyncio.sleep(delay)

            except Exception as e:
                log(f"Ошибка wheel: {e}", self.tname)
            finally:
                self.clear = False
                done_event.set()
                await asyncio.sleep(0.15)

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
            _, window_info, points, delay_points, no_curve, done_event = task
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
                        functools.partial(
                            move_line if no_curve else move_human,
                            window_info, first_x, first_y
                        )
                    )
                    await asyncio.sleep(0.05)

                    await loop.run_in_executor(None, functools.partial(inputs.mouse_down, "left"))

                    for x, y in points[1:]:
                        await loop.run_in_executor(
                            None,
                            functools.partial(
                                move_line if no_curve else move_human,
                                window_info, x, y
                            )
                        )
                        await asyncio.sleep(delay_points)

                    await loop.run_in_executor(None, functools.partial(inputs.mouse_up, "left"))

            except Exception as e:
                log(f"Ошибка swipe: {e}", self.tname)
            finally:
                self.clear = False
                done_event.set()
                await asyncio.sleep(0.06)

        elif action == "key_press":
            _, key, done_event = task
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None,
                                           functools.partial(inputs.press, key))
            except Exception as e:
                log(f"Ошибка key_press: {e}", self.tname)
            finally:
                done_event.set()
                await asyncio.sleep(0.01)

        elif action == "key_down":
            _, key, done_event = task
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None,
                                           functools.partial(inputs.key_down, key))
            except Exception as e:
                log(f"Ошибка key_down: {e}", self.tname)
            finally:
                done_event.set()
                await asyncio.sleep(0.02)

        elif action == "key_up":
            _, key, done_event = task
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None,
                                           functools.partial(inputs.key_up, key))
            except Exception as e:
                log(f"Ошибка key_up: {e}", self.tname)
            finally:
                done_event.set()
                await asyncio.sleep(0.01)


    async def _do_click(self, window_info, x_offset, y_offset, button):
        loop = asyncio.get_running_loop()
        async with click_semaphore:
            await loop.run_in_executor(
                None,
                functools.partial(click_human if curve else click_mouse,
                                  window_info, x_offset, y_offset, button)
            )
