import asyncio
import threading
import time
from typing import List, Optional, Tuple

import cv2
import mss
import numpy as np
from screeninfo import get_monitors

from bot.clogger import log

FRAME_INTERVAL = 1 / 30
FIRST_FRAME_TIMEOUT = 5.0


class FrameStore:

    _instance: Optional["FrameStore"] = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._init()
                cls._instance = inst
        return cls._instance

    def _init(self):
        self.tname = "-FrameStore-"
        self._monitors: List[dict] = []
        self._current: List[Optional[np.ndarray]] = []
        self._previous: List[Optional[np.ndarray]] = []
        self._frame_lock = threading.Lock()
        self._waiters: List[Tuple[asyncio.AbstractEventLoop, asyncio.Event]] = []
        self._waiters_lock = threading.Lock()
        self._stop = threading.Event()
        self._first_frame = threading.Event()

        self._refresh_monitors()

        self._thread = threading.Thread(target=self._run, daemon=True, name="FrameStore")
        self._thread.start()

        if self._first_frame.wait(FIRST_FRAME_TIMEOUT):
            log(
                f"Запущен | мониторов: {len(self._monitors)} | "
                f"интервал: {FRAME_INTERVAL * 1000:.0f}мс",
                self.tname,
            )
        else:
            log(
                "Не отдал первый кадр вовремя, очко",
                self.tname,
                level="WARNING",
            )

    def _refresh_monitors(self):
        monitors = []
        for i, m in enumerate(get_monitors()):
            monitors.append({
                "left": m.x,
                "top": m.y,
                "width": m.width,
                "height": m.height,
            })
            log(f"Монитор {i}: {m.width}x{m.height} @ ({m.x}, {m.y})", self.tname)

        if not monitors:
            log("не нашёл ни одного монитора", self.tname, level="ERROR")

        with self._frame_lock:
            self._monitors = monitors
            self._current = [None] * len(monitors)
            self._previous = [None] * len(monitors)

    def _run(self):
        with mss.mss() as sct:
            while not self._stop.is_set():
                t0 = time.perf_counter()
                any_new = False

                with self._frame_lock:
                    monitors = list(self._monitors)

                for i, mon in enumerate(monitors):
                    try:
                        shot = sct.grab(mon)
                        frame = cv2.cvtColor(np.asarray(shot), cv2.COLOR_BGRA2RGB)
                        with self._frame_lock:
                            if i < len(self._current):
                                self._previous[i] = self._current[i]
                                self._current[i] = frame
                        any_new = True
                    except Exception as e:
                        log(f"grab монитора {i} {mon}: {e}", self.tname, level="ERROR")

                if any_new:
                    if not self._first_frame.is_set():
                        self._first_frame.set()
                    self._notify_waiters()

                elapsed = time.perf_counter() - t0
                #log(f"{elapsed * 1000:.1f}мс", self.tname, level="INFO")
                sleep_for = FRAME_INTERVAL - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)

    def _notify_waiters(self):
        with self._waiters_lock:
            if not self._waiters:
                return
            waiters = self._waiters
            self._waiters = []
        for loop, ev in waiters:
            try:
                loop.call_soon_threadsafe(ev.set)
            except Exception:
                pass

    def get_frame_event(self) -> asyncio.Event:
        loop = asyncio.get_running_loop()
        ev = asyncio.Event()
        with self._waiters_lock:
            self._waiters.append((loop, ev))
        return ev

    def _find_monitor(self, abs_x: int, abs_y: int) -> Tuple[int, Optional[dict]]:
        with self._frame_lock:
            monitors = list(self._monitors)
        for i, m in enumerate(monitors):
            if (m["left"] <= abs_x < m["left"] + m["width"]
                    and m["top"] <= abs_y < m["top"] + m["height"]):
                return i, m
        return -1, None

    def get_region(self, abs_x: int, abs_y: int, w: int, h: int) -> Optional[np.ndarray]:
        idx, mon = self._find_monitor(abs_x, abs_y)
        if idx < 0:
            return None

        with self._frame_lock:
            if idx >= len(self._current):
                return None
            frame = self._current[idx]

        if frame is None:
            return None

        rx = abs_x - mon["left"]
        ry = abs_y - mon["top"]
        fh, fw = frame.shape[:2]
        x2 = min(rx + w, fw)
        y2 = min(ry + h, fh)
        rx = max(rx, 0)
        ry = max(ry, 0)
        if rx >= x2 or ry >= y2:
            return None
        return frame[ry:y2, rx:x2]

    def stop(self):
        self._stop.set()


def frame_store() -> FrameStore:
    return FrameStore()
