from __future__ import annotations

import asyncio
import logging
import time
from typing import List

import numpy as np

from bot.capture.backend import BackendUnavailable, CaptureBackend, Rect, Rgb

_log = logging.getLogger(__name__)


class RustBackend(CaptureBackend):
    name = "rust"

    def __init__(self, prefer: str | None = None):
        try:
            import capture_rs
        except ImportError as e:
            raise BackendUnavailable(f"capture_rs module not installed ({e})") from e

        self._mod = capture_rs
        try:
            self._active = capture_rs.init(prefer)
        except RuntimeError as e:
            self._active = capture_rs.backend_name()
        self.name = f"rust:{self._active}"
        self._err_count = 0
        self._last_err_log = 0.0

        mons = self.monitors()
        _log.info("capture_rs backend=%s monitors=%s", self._active, mons)

        if mons:
            mx, my, mw, mh = mons[0]
            try:
                self._mod.check_pixel(mx + mw // 2, my + mh // 2, 1, 1, 0, 0, 0, 255)
                _log.info("capture_rs health check OK")
            except Exception as e:
                _log.warning("capture_rs health check FAILED: %s", e)

    def _log_error(self, func: str, e: Exception):
        self._err_count += 1
        now = time.monotonic()
        if self._err_count <= 5 or (now - self._last_err_log) > 10.0:
            _log.warning("capture_rs.%s failed (#%d): %s", func, self._err_count, e)
            self._last_err_log = now

    def check_pixel(self, x: int, y: int, w: int, h: int, rgb: Rgb, thr: int) -> bool:
        r, g, b = rgb
        last = None
        for attempt in range(3):
            try:
                return self._mod.check_pixel(x, y, w, h, int(r), int(g), int(b), int(thr))
            except Exception as e:
                last = e
                if attempt < 2:
                    time.sleep(0.1)
        self._log_error("check_pixel", last)
        return False

    async def wait_for_pixel(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        rgb: Rgb,
        thr: int,
        timeout: float,
        poll: float = 0.02,
    ) -> bool:
        r, g, b = rgb
        timeout_ms = max(0, int(timeout * 1000))
        poll_ms = max(1, int(poll * 1000))
        loop = asyncio.get_running_loop()
        last = None
        for attempt in range(3):
            try:
                return await loop.run_in_executor(
                    None,
                    self._mod.wait_for_pixel,
                    x, y, w, h,
                    int(r), int(g), int(b),
                    int(thr),
                    timeout_ms,
                    poll_ms,
                )
            except Exception as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(0.1)
        self._log_error("wait_for_pixel", last)
        return False

    def capture_region(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        last = None
        for attempt in range(3):
            try:
                raw = self._mod.capture_region(x, y, w, h)
                arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 4))
                return np.ascontiguousarray(arr[:, :, 2::-1])
            except Exception as e:
                last = e
                if attempt < 2:
                    time.sleep(0.1)
        self._log_error("capture_region", last)
        return np.zeros((h, w, 3), dtype=np.uint8)

    def monitors(self) -> List[Rect]:
        return list(self._mod.monitors())
