from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from bot.capture.backend import BackendUnavailable, CaptureBackend, Rect, Rgb
from bot.capture.hwnd import hwnd_is_valid, resolve_hwnd

_log = logging.getLogger(__name__)


class _CaptureEntry:
    __slots__ = ("cap", "hwnd", "backend", "created_at", "unhealthy_since", "per_window")

    def __init__(self, cap: Any, hwnd: Optional[int], backend: str, per_window: bool):
        self.cap = cap
        self.hwnd = hwnd
        self.backend = backend
        self.created_at = time.monotonic()
        self.unhealthy_since: Optional[float] = None
        self.per_window = per_window


class RustBackend(CaptureBackend):
    name = "rust"

    _MONITOR_KEY = "__monitor__"
    _UNHEALTHY_RECREATE_AFTER = 1.5

    def __init__(self, prefer: str | None = "wgc"):
        try:
            import capture_rs
        except ImportError as e:
            raise BackendUnavailable(f"capture_rs module not installed ({e})") from e

        if not hasattr(capture_rs, "Capture"):
            raise BackendUnavailable(
                "capture_rs missing Capture class; rebuild capture_rs.pyd"
            )

        self._mod = capture_rs

        env_prefer = os.environ.get("L2M_CAPTURE_BACKEND")
        if env_prefer:
            env_prefer = env_prefer.strip().lower() or None
        self._prefer = env_prefer if env_prefer else (prefer or "wgc")

        self._captures: Dict[str, _CaptureEntry] = {}
        self._lock = threading.RLock()
        self._err_count = 0
        self._last_err_log = 0.0

        monitor_entry = self._create_capture(nick=None, hwnd=None, allow_fallback=False)
        if monitor_entry is None:
            raise BackendUnavailable("capture_rs monitor-mode init failed")
        self._captures[self._MONITOR_KEY] = monitor_entry
        self.name = f"rust:{monitor_entry.backend}"

        mons = self.monitors()
        _log.info(
            "capture_rs backend=%s prefer=%s monitors=%s",
            monitor_entry.backend, self._prefer, mons,
        )

        if mons:
            mx, my, mw, mh = mons[0]
            try:
                monitor_entry.cap.check_pixel(mx + mw // 2, my + mh // 2, 1, 1, 0, 0, 0, 255)
                _log.info("capture_rs health check OK")
            except Exception as e:
                _log.warning("capture_rs health check FAILED: %s", e)

    def _create_capture(
        self,
        nick: Optional[str],
        hwnd: Optional[int],
        allow_fallback: bool = True,
    ) -> Optional[_CaptureEntry]:
        prefer = self._prefer
        try:
            if hwnd is not None and nick is not None:
                cap = self._mod.Capture(prefer=prefer, hwnd=int(hwnd), nick=str(nick))
            elif hwnd is not None:
                cap = self._mod.Capture(prefer=prefer, hwnd=int(hwnd))
            else:
                cap = self._mod.Capture(prefer=prefer)
            backend_name = "unknown"
            try:
                backend_name = cap.backend_name()
            except Exception:
                pass
            per_window = backend_name in ("wgc_window", "wgc_registry")
            if hwnd is not None and not per_window:
                _log.info(
                    "capture_rs: nick=%s hwnd=%s fell back to %s (not per-window)",
                    nick, hex(hwnd) if hwnd else None, backend_name,
                )
            else:
                _log.info(
                    "capture_rs: created Capture nick=%s hwnd=%s backend=%s",
                    nick, hex(hwnd) if hwnd else None, backend_name,
                )
            return _CaptureEntry(cap=cap, hwnd=hwnd, backend=backend_name, per_window=per_window)
        except Exception as e:
            _log.warning(
                "capture_rs: create Capture nick=%s hwnd=%s failed: %s",
                nick, hex(hwnd) if hwnd else None, e,
            )
            if hwnd is not None and allow_fallback:
                _log.info("capture_rs: falling back to monitor-mode for nick=%s", nick)
                return None
            return None

    def _monitor_capture(self) -> _CaptureEntry:
        return self._captures[self._MONITOR_KEY]

    def _get_capture(self, nick: Optional[str]) -> _CaptureEntry:
        if nick is None:
            return self._monitor_capture()
        with self._lock:
            entry = self._captures.get(nick)
            if entry is not None:
                if entry.per_window:
                    if not hwnd_is_valid(entry.hwnd):
                        _log.info(
                            "capture_rs: nick=%s hwnd=%s no longer valid; recreating",
                            nick, hex(entry.hwnd) if entry.hwnd else None,
                        )
                        entry = None
                    else:
                        healthy = True
                        try:
                            healthy = bool(entry.cap.is_healthy)
                        except Exception:
                            healthy = False
                        if not healthy:
                            now = time.monotonic()
                            if entry.unhealthy_since is None:
                                entry.unhealthy_since = now
                            elif (now - entry.unhealthy_since) >= self._UNHEALTHY_RECREATE_AFTER:
                                _log.info(
                                    "capture_rs: nick=%s Capture unhealthy for %.1fs; recreating",
                                    nick, now - entry.unhealthy_since,
                                )
                                entry = None
                        else:
                            entry.unhealthy_since = None
                if entry is not None:
                    return entry

            hwnd = resolve_hwnd(nick)
            if hwnd is None:
                _log.warning(
                    "capture_rs: nick=%s hwnd not found; using monitor Capture", nick,
                )
                return self._monitor_capture()

            new_entry = self._create_capture(nick=nick, hwnd=hwnd, allow_fallback=True)
            if new_entry is None:
                return self._monitor_capture()
            self._captures[nick] = new_entry
            return new_entry

    def _log_error(self, func: str, e: Exception):
        self._err_count += 1
        now = time.monotonic()
        if self._err_count <= 5 or (now - self._last_err_log) > 10.0:
            _log.warning("capture_rs.%s failed (#%d): %s", func, self._err_count, e)
            self._last_err_log = now

    def check_pixel(
        self,
        nick: Optional[str],
        x: int,
        y: int,
        w: int,
        h: int,
        rgb: Rgb,
        thr: int,
    ) -> bool:
        r, g, b = rgb
        entry = self._get_capture(nick)
        try:
            return bool(entry.cap.check_pixel(x, y, w, h, int(r), int(g), int(b), int(thr)))
        except Exception as e:
            self._log_error("check_pixel", e)
            if entry.per_window and nick is not None:
                try:
                    mon = self._monitor_capture()
                    return bool(mon.cap.check_pixel(x, y, w, h, int(r), int(g), int(b), int(thr)))
                except Exception as e2:
                    self._log_error("check_pixel(monitor fallback)", e2)
            return False

    async def wait_for_pixel(
        self,
        nick: Optional[str],
        x: int,
        y: int,
        w: int,
        h: int,
        rgb: Rgb,
        thr: int,
        timeout: float,
        poll: float = 0.02,
    ) -> bool:
        entry = self._get_capture(nick)
        r, g, b = rgb
        deadline = time.monotonic() + max(0.0, float(timeout))
        poll_s = max(0.005, float(poll))
        while True:
            try:
                if bool(entry.cap.check_pixel(x, y, w, h, int(r), int(g), int(b), int(thr))):
                    return True
            except Exception as e:
                self._log_error("wait_for_pixel", e)
                if entry.per_window and nick is not None:
                    try:
                        mon = self._monitor_capture()
                        if bool(mon.cap.check_pixel(x, y, w, h, int(r), int(g), int(b), int(thr))):
                            return True
                    except Exception as e2:
                        self._log_error("wait_for_pixel(monitor fallback)", e2)
                        return False
            if time.monotonic() >= deadline:
                return False
            await asyncio.sleep(poll_s)

    def capture_region(
        self,
        nick: Optional[str],
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> np.ndarray:
        entry = self._get_capture(nick)
        try:
            try:
                frame = entry.cap.latest_frame(x, y)
            except Exception:
                frame = None
            if frame is not None:
                try:
                    raw = frame.region(x, y, w, h)
                    arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 4))
                    return np.ascontiguousarray(arr[:, :, 2::-1])
                except Exception:
                    pass
            raw = entry.cap.capture_region(x, y, w, h)
            arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 4))
            return np.ascontiguousarray(arr[:, :, 2::-1])
        except Exception as e:
            self._log_error("capture_region", e)
            if entry.per_window and nick is not None:
                try:
                    mon = self._monitor_capture()
                    raw = mon.cap.capture_region(x, y, w, h)
                    arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 4))
                    return np.ascontiguousarray(arr[:, :, 2::-1])
                except Exception as e2:
                    self._log_error("capture_region(monitor fallback)", e2)
            return np.zeros((h, w, 3), dtype=np.uint8)

    def capture_regions(
        self,
        nick: Optional[str],
        rects: Sequence[Tuple[int, int, int, int]],
    ) -> List[np.ndarray]:
        rects = list(rects)
        if not rects:
            return []
        entry = self._get_capture(nick)
        try:
            blobs = entry.cap.capture_regions(rects)
            out: List[np.ndarray] = []
            for (x, y, w, h), raw in zip(rects, blobs):
                if raw is None or len(raw) != w * h * 4:
                    out.append(np.zeros((h, w, 3), dtype=np.uint8))
                    continue
                arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 4))
                out.append(np.ascontiguousarray(arr[:, :, 2::-1]))
            return out
        except Exception as e:
            self._log_error("capture_regions", e)
        return [self.capture_region(nick, x, y, w, h) for x, y, w, h in rects]

    def monitors(self) -> List[Rect]:
        try:
            return list(self._monitor_capture().cap.monitors())
        except Exception:
            return []

    def latest_age_ms(self, nick: Optional[str], x: int, y: int) -> Optional[int]:
        try:
            entry = self._get_capture(nick)
            return entry.cap.latest_frame_age_ms(x, y)
        except Exception:
            return None

    def stats(self, nick: Optional[str] = None) -> dict:
        try:
            entry = self._get_capture(nick)
            return dict(entry.cap.stats())
        except Exception:
            return {}

    def release(self, nick: Optional[str]) -> None:
        if nick is None or nick == self._MONITOR_KEY:
            return
        with self._lock:
            entry = self._captures.pop(nick, None)
        if entry is not None:
            _log.info("capture_rs: released Capture for nick=%s", nick)

    def origin(self, nick: Optional[str]) -> Optional[Tuple[int, int]]:
        try:
            entry = self._get_capture(nick)
            return entry.cap.origin()
        except Exception:
            return None
