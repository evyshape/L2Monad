from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import mss
import numpy as np

from bot.capture.backend import BackendUnavailable, CaptureBackend, Rect, Rgb
from bot.limits import pixel_semaphore, thread


_mss_local = threading.local()


def _thread_mss() -> mss.mss:
    sct = getattr(_mss_local, "sct", None)
    if sct is None:
        sct = mss.mss()
        _mss_local.sct = sct
    return sct


class MssBackend(CaptureBackend):
    name = "mss"

    def __init__(self):
        try:
            mss.mss()
        except Exception as e:
            raise BackendUnavailable(f"mss unavailable ({e})") from e
        self._pool = ThreadPoolExecutor(max_workers=thread, thread_name_prefix="mss")
        self._semaphore = pixel_semaphore

    def check_pixel(self, nick, x: int, y: int, w: int, h: int, rgb: Rgb, thr: int) -> bool:
        arr = self._grab_bgr(x, y, w, h)
        target = np.array(rgb, dtype=np.int16)
        diff = np.abs(arr.astype(np.int16) - target)
        return bool(np.any(np.all(diff <= thr, axis=-1)))

    async def wait_for_pixel(
        self,
        nick,
        x: int,
        y: int,
        w: int,
        h: int,
        rgb: Rgb,
        thr: int,
        timeout: float,
        poll: float = 0.02,
    ) -> bool:
        def _run() -> bool:
            sct = _thread_mss()
            monitor = {"left": x, "top": y, "width": w, "height": h}
            target = np.array(rgb, dtype=np.int16)
            deadline = time.monotonic() + max(0.0, timeout)
            while True:
                try:
                    shot = sct.grab(monitor)
                except Exception:
                    return False
                arr = np.array(shot)[:, :, :3][:, :, ::-1].astype(np.int16)
                if np.any(np.all(np.abs(arr - target) <= thr, axis=-1)):
                    return True
                if time.monotonic() >= deadline:
                    return False
                time.sleep(poll)

        loop = asyncio.get_running_loop()
        async with self._semaphore:
            return await loop.run_in_executor(self._pool, _run)

    def capture_region(self, nick, x: int, y: int, w: int, h: int) -> np.ndarray:
        return self._grab_rgb(x, y, w, h)

    async def capture_region_async(self, nick, x: int, y: int, w: int, h: int) -> np.ndarray:
        loop = asyncio.get_running_loop()
        async with self._semaphore:
            return await loop.run_in_executor(self._pool, self._grab_rgb, x, y, w, h)

    def monitors(self) -> List[Rect]:
        sct = _thread_mss()
        out: List[Rect] = []
        for m in sct.monitors[1:]:
            out.append((int(m["left"]), int(m["top"]), int(m["width"]), int(m["height"])))
        return out

    def _grab_bgr(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        sct = _thread_mss()
        monitor = {"left": x, "top": y, "width": w, "height": h}
        shot = sct.grab(monitor)
        return np.array(shot)[:, :, :3][:, :, ::-1]

    def _grab_rgb(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        return self._grab_bgr(x, y, w, h)
