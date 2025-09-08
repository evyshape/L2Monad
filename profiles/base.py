import asyncio
from asyncio import Queue
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Union

import mss
import numpy as np

from bot.clogger import log
from bot.limits import pixel_semaphore
from bot.windows.base import BaseSettings, default_values
from bot.windows.runtime import RuntimeData


class BaseProfile(ABC):
    def __init__(self, window_info: Dict[str, Dict], settings: BaseSettings | None = None):
        self.window_info = window_info
        self.running = True
        self._task: asyncio.Task | None = None
        self.event_queue: Queue = Queue()
        self._event_task: asyncio.Task | None = None
        self.tname = "-BaseProfile-"
        self.settings = settings or BaseSettings(**default_values)
        self.runtime_data = RuntimeData(current_state="null")
        self._sct = mss.mss()

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

    async def on_start(self) -> None:
        """
        Тут должно быть то, что будет выполняться при старте профиля
        Обязательно должен быть вызов main_loop так как там основная логика профиля
        """
        from bot.events.events import EventsManager
        self.running = True
        window_id = next(iter(self.window_info))

        EventsManager.register(window_id, self)
        self._event_task = asyncio.create_task(self._event_listener())

        try:
            await self.main_loop()
        except asyncio.CancelledError:
            log(f"Профиль остановлен вручную", window_id)
            raise
        finally:
            self.running = False
            if self._event_task:
                self._event_task.cancel()
                await asyncio.gather(self._event_task, return_exceptions=True)
            log(f"main_loop завершился", window_id)

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
        try:
            while True:
                event = await self.event_queue.get()
                await self.handle_event(event)
        except asyncio.CancelledError:
            log(f"[{self.tname}] Остановил слушалку")
        finally:
            log(f"[{self.tname}] Слушалка стопнулась")

    async def check_pixel(self, xy: Tuple[int, int],
                          rgb: Union[Tuple[int, int, int], str],
                          timeout: float = 0.2,
                          thr: float = 2,
                          wsize: str = "2x2") -> bool:

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

        start_time = asyncio.get_event_loop().time()

        async with pixel_semaphore:
            while asyncio.get_event_loop().time() - start_time < timeout:
                monitor = {"left": adjusted_x, "top": adjusted_y, "width": width, "height": height}
                screenshot = np.array(self._sct.grab(monitor))

                screenshot_rgb = screenshot[..., :3][:, :, ::-1]

                diff = np.abs(screenshot_rgb - np.array(rgb))
                if np.all(diff <= thr, axis=-1).any():
                    return True

                await asyncio.sleep(0.01)

        return False

    def is_running(self) -> bool:
        """
        Проверяет, активен ли бот (по self.running)
        """
        return self.running