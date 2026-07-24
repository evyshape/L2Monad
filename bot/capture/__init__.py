from __future__ import annotations

import ctypes
import sys
from typing import List, Optional

import numpy as np

from bot.capture.backend import (
    BackendUnavailable,
    CaptureBackend,
    Rect,
    Rgb,
    create_backend,
)

_backend: Optional[CaptureBackend] = None


def _ensure_dpi_aware():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def init(prefer: Optional[str] = None) -> str:
    global _backend
    _ensure_dpi_aware()
    _backend = create_backend(prefer)
    return _backend.name


def active() -> CaptureBackend:
    if _backend is None:
        init()
    assert _backend is not None
    return _backend


def backend_name() -> str:
    return active().name


def monitors() -> List[Rect]:
    return active().monitors()


def check_pixel_sync(x: int, y: int, w: int, h: int, rgb: Rgb, thr: int) -> bool:
    return active().check_pixel(x, y, w, h, rgb, thr)


async def wait_for_pixel(
    x: int,
    y: int,
    w: int,
    h: int,
    rgb: Rgb,
    thr: int,
    timeout: float,
    poll: float = 0.02,
) -> bool:
    return await active().wait_for_pixel(x, y, w, h, rgb, thr, timeout, poll)


async def capture_region(x: int, y: int, w: int, h: int) -> np.ndarray:
    return await active().capture_region_async(x, y, w, h)


__all__ = [
    "BackendUnavailable",
    "CaptureBackend",
    "Rect",
    "Rgb",
    "active",
    "backend_name",
    "capture_region",
    "check_pixel_sync",
    "init",
    "monitors",
    "wait_for_pixel",
]
