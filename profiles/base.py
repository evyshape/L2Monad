import asyncio
from asyncio import Queue
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Union
import mss
import numpy as np
from bot.limits import pixel_semaphore
from clogger import log
from bot.windows.base import BaseSettings, default_values
from bot.windows.runtime import RuntimeData

class BaseProfile(ABC):
    def __init__(self, window_info: Dict[str, Dict], settings: BaseSettings | None = None):
        self.window_info = window_info
        self.running = False
        self._task: asyncio.Task | None = None
        self.event_queue: Queue = Queue()
        self._event_task: asyncio.Task | None = None
        self.tname = "-BaseProfile-"
        self.settings = settings or BaseSettings(**default_values)
        self.runtime_data = RuntimeData(current_state="null")

    @property
    @abstractmethod
    def profile_name(self) -> str:
        """
        Строка с названием профиля
        """
        pass

    @property
    @abstractmethod
    def profile_version(self) -> str:
        """
        Строка с версией профиля
        """
        pass

    @abstractmethod
    async def main_loop(self) -> None:
        """
        Основная логика бота должна быть тут - в каждом профиле ОБЯЗАТЕЛЬНА
        Можно пхать как бесконечные циклы так и конечные, каждое окно независимо
        """
        pass

    async def on_start(self) -> asyncio.Task:
        """
        Тут должно быть то, что будет выполняться при старте профиля
        Обязательно должен быть вызов main_loop так как там основная логика профиля
        """
        from bot.events.events import EventsManager
        self.running = True
        window_id = next(iter(self.window_info))
        #log(f"Стартанул профиль", window_id)

        EventsManager.register(window_id, self)

        self._event_task = asyncio.create_task(self._event_listener())
        self._task = asyncio.create_task(self.main_loop())
        return self._task

    async def on_stop(self) -> None:
        """
        Тут должно быть то, что будет происходить при выключении профиля у конкретного окна.
        Можно допилить уведу в тг/включение звука/звонок на телефон/письмо на емейл
        """
        from bot.events.events import EventsManager
        self.running = False
        window_id = next(iter(self.window_info))
        #log(f"Останавливаю профиль", window_id)

        EventsManager.unregister(window_id)

        tasks = [self._task] if self._task else []

        if self._event_task:
            self._event_task.cancel()
            tasks.append(self._event_task)

        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        self.event_queue = Queue()

    def send_event(self, event: Any) -> None:
        """
        Добавляет событие в очередь профиля, может быть 2 сразу и более
        """
        if self.running:
            self.event_queue.put_nowait(event)

    async def handle_event(self, event: Any) -> None:
        """
        Обработка событий, надо прописывать ВО ВСЕХ ПРОФИЛЯХ где нужны ивенты
        """
        window_id = next(iter(self.window_info))
        log(f"Обработчик события: {event}", window_id)

    async def _event_listener(self) -> None:
        """
        Асинхронный обработчик
        """
        while self.running:
            try:
                event = await self.event_queue.get()
                await self.handle_event(event)
            except asyncio.CancelledError:
                break

    async def check_pixel(self, xy: Tuple[int, int],
                          rgb: Union[Tuple[int, int, int], str], timeout: float = 0.2,
                          thr: float = 2, wsize: str = "2x2") -> bool:
        """
        Проверка цвета пикселя, для каждого окна своя, юзать через обьект профиля
        """
        loop = asyncio.get_running_loop()

        def blocking_check():
            wait_time = 0.05
            if rgb == "no":
                return True

            try:
                width, height = map(int, wsize.lower().split('x'))
            except Exception:
                width, height = 2, 2  # fallback

            window_id, window = next(iter(self.window_info.items()))
            left, top = window['Position']

            adjusted_x = xy[0] + left
            adjusted_y = xy[1] + top

            start_time = time.time()

            with mss.mss() as sct:
                while time.time() - start_time < timeout:
                    monitor = {"left": adjusted_x, "top": adjusted_y, "width": width,
                               "height": height}
                    screenshot = np.array(sct.grab(monitor))

                    for y in range(height):
                        for x in range(width):
                            pixel_color = screenshot[y, x][:3][::-1]  # BGR to RGB
                            diff = np.abs(pixel_color - rgb)
                            if np.all(diff <= thr):
                                return True

                    time.sleep(wait_time)
            return False

        async with pixel_semaphore:
            return await loop.run_in_executor(None, blocking_check)

    def is_running(self) -> bool:
        """
        Проверяет, активен ли бот (по self.running)
        """
        return self.running