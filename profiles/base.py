import asyncio
import contextlib
from asyncio import Queue
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Union, Any, List, Optional

import numpy as np
import pygetwindow as gw
from screeninfo import get_monitors
from bot import capture
from bot.clogger import log
from bot.windows.base import BaseSettings, default_values
from bot.alchemy.alch_cons import ALCH_REZ
from bot.alchemy.alch_utils import alch_rects
from bot.windows.runtime import RuntimeData
from bot.events.enums import BotState

import ctypes

HWND_BOTTOM = 1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SetWindowPos = ctypes.windll.user32.SetWindowPos

class BaseProfile(ABC):
    def __init__(self, window_info: Dict[str, Dict], settings: BaseSettings | None = None):
        from bot.events.checker import EventsChecker
        from bot.methods.other import MouseEvents

        self.window_info = window_info
        self.running = True
        self._task: asyncio.Task | None = None
        self.events_checker = EventsChecker()
        self.event_queue: Queue = Queue(maxsize=64)
        self._event_task: asyncio.Task | None = None
        self.tname = "-BaseProfile-"
        self.settings = settings or BaseSettings(**default_values)
        self.runtime_data = RuntimeData(current_state=BotState.NULL)
        self._saved_pos = None
        self._window_id = next(iter(window_info))
        self._child_tasks: List[asyncio.Task] = []
        self.mouse = MouseEvents()
        self._tgbot_cache = None

        from bot.methods.game.errors import ErrorHandler
        from bot.methods.game.energo import Energo
        from bot.methods.game.teleport import Teleport
        from bot.methods.game.combat import Combat
        from bot.methods.game.town import Town
        from bot.methods.game.claims import Claims
        from bot.methods.game.auction import Auction
        from bot.methods.game.scheduler import Scheduler

        self.errors = ErrorHandler(self)
        self.energo = Energo(self)
        self.tp = Teleport(self)
        self.combat = Combat(self)
        self.town = Town(self)
        self.claims = Claims(self)
        self.auction = Auction(self)
        self.scheduler = Scheduler(self)

    @property
    def window_id(self) -> str:
        return self._window_id

    @property
    def tgbot(self):
        if self._tgbot_cache is None:
            try:
                from tgbot.bot import TgBot
                self._tgbot_cache = TgBot()
            except Exception:
                return None
        return self._tgbot_cache

    def notify(self, level: str, text: str) -> None:
        if not getattr(self.settings, "TELEGRAM_NOTIFIES", False):
            return
        tg = self.tgbot
        if tg is None:
            return
        tg.send_notification(level=level, text=text, nickname=self.window_id)

    def notify_screenshot(self, caption: str, level: str = "warning") -> None:
        if not getattr(self.settings, "TELEGRAM_NOTIFIES", False):
            return
        tg = self.tgbot
        if tg is None:
            return

        from bot.methods.other import screenshot_window
        from tgbot.keyboards.screenshot import delete_screenshot_kb
        screen = screenshot_window(self.window_info, tg=True)
        tg.send_pic(
            photo=screen,
            caption=caption,
            parse_mode="HTML",
            nickname=self.window_id,
            reply_markup=delete_screenshot_kb(),
        )

    @contextlib.asynccontextmanager
    async def paused_monitors(self, restart_with: Optional[list] = None):
        """
        на время блока стопаются все мониторы для этого окна,
        после блока перезапускаются (self.get_monitors если есть).
        """

        self.events_checker.stop_monitoring(self.window_id)
        try:
            yield
        finally:
            if restart_with is None:
                monitors = getattr(self, "get_monitors", None)
            else:
                monitors = restart_with
            if monitors:
                self.events_checker.start_monitoring(
                    self.window_id, self, monitors=monitors
                )

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
            #log(f"Профиль остановлен вручную", window_id)
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
        self.event_queue = Queue(maxsize=64)

        try:
            capture.release(self._window_id)
        except Exception:
            pass

    async def _save_pos(self):
        window_id, window = next(iter(self.window_info.items()))
        try:
            win = gw.getWindowsWithTitle(window['Title'])[0]
            self._saved_pos = (win.left, win.top, win.width, win.height)
        except Exception as e:
            log(f"Ошибка при сохранении позиции: {e}", window_id)

    async def _resize(self, width: int, height: int, left: int, top: int):
        window_id, window = next(iter(self.window_info.items()))
        try:
            win = gw.getWindowsWithTitle(window['Title'])[0]
            win.resizeTo(width, height)
            win.moveTo(left, top)

            if width == 400 and height == 225:
                SetWindowPos(
                    win._hWnd,
                    HWND_BOTTOM,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )
            else:
                try:
                    win.activate()
                except Exception:
                    pass

            window['Width'] = win.width
            window['Height'] = win.height
            window['Position'] = (win.left, win.top)
            window['Size'] = f"{win.width}x{win.height}"

        except Exception as e:
            log(f"Ошибка при ресайзе: {e}", window_id)

    async def smart_resize(self):
        window_id, window = next(iter(self.window_info.items()))
        try:
            await self._save_pos()

            #info = get_monitorss()
            #log(json.dumps(info, indent=4, ensure_ascii=False), window_id)

            monitors = get_monitors()

            win_w, win_h = map(int, ALCH_REZ.split("x"))
            cell_w = win_w
            cell_h = win_h + 40

            for idx, monitor in reversed(list(enumerate(monitors))):
                cols = monitor.width // cell_w
                rows = monitor.height // cell_h

                candidates = []
                for r in range(rows):
                    for c in range(cols):
                        x = monitor.x + c * cell_w
                        y = monitor.y + r * cell_h + 40
                        candidates.append((x, y))

                l2wins = [w for w in gw.getAllWindows() if "Lineage" in w.title]
                exr = [(w.left, w.top, w.width, w.height) for w in l2wins]

                pos = None
                for (cx, cy) in candidates:
                    candidate_rect = (cx, cy, win_w, win_h)
                    if not any(alch_rects(candidate_rect, r) for r in exr):
                        pos = (cx, cy)
                        break

                if pos:
                    log(
                        f"Нашёл местечко на монике #{idx + 1} ({monitor.width}x{monitor.height})",
                        window_id
                    )
                    new_left, new_top = pos
                    await self._resize(win_w, win_h, new_left, new_top)
                    return True

            log("Свободного места не нашлось вовсе =(", window_id)
            return None

        except Exception as e:
            log(f"Ошибка при smart_resize: {e}", window_id)

    async def _activate(self) -> bool:
        window_id, window = next(iter(self.window_info.items()))
        try:
            win = gw.getWindowsWithTitle(window['Title'])[0]
            try:
                win.activate()
            except Exception:
                ctypes.windll.user32.SetForegroundWindow(win._hWnd)
            return True
        except Exception as e:
            log(f"Не удалось активнуть: {e}", window_id)
            return False

    def send_event(self, event: Any) -> None:
        """
        Добавляет событие в очередь профиля, может быть 2 сразу и более
        """
        if self.running:
            try:
                self.event_queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    self.event_queue.get_nowait()
                    self.event_queue.put_nowait(event)
                except Exception:
                    pass

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
                try:
                    await self.handle_event(event)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    log(f"[{self.tname}] Ошибка в handle_event: {e}")
        except asyncio.CancelledError:
            log(f"[{self.tname}] Остановил слушалку")

    async def check_pixel(self, xy: Tuple[int, int],
                          rgb: Union[Tuple[int, int, int], str], timeout: float = 0.2,
                          thr: float = 2, wsize: str = "2x2") -> bool:

        if rgb == "no":
            return True

        try:
            width, height = map(int, wsize.lower().split('x'))
        except Exception:
            width, height = 2, 2

        window = self.window_info[self._window_id]
        abs_x = xy[0] + window['Position'][0]
        abs_y = xy[1] + window['Position'][1]

        return await capture.wait_for_pixel(
            self._window_id,
            abs_x, abs_y, width, height,
            (int(rgb[0]), int(rgb[1]), int(rgb[2])),
            int(thr),
            float(timeout),
        )

    async def capture_multy(
        self,
        rects: List[Tuple[int, int, int, int]]

    ) -> List[np.ndarray]:

        window = self.window_info[self._window_id]
        px, py = window['Position']
        abs_rects = [(x + px, y + py, w, h) for x, y, w, h in rects]
        nick = self._window_id
        try:
            return await capture.capture_regions(nick, abs_rects)
        except Exception:
            async def _one(x: int, y: int, w: int, h: int) -> np.ndarray:
                try:
                    return await capture.capture_region(nick, x, y, w, h)
                except Exception:
                    return np.zeros((h, w, 3), dtype=np.uint8)
            return await asyncio.gather(*(_one(x, y, w, h) for x, y, w, h in abs_rects))

    def is_running(self) -> bool:
        """
        Проверяет, активен ли бот (по self.running)
        """
        return self.running