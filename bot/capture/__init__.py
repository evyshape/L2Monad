from __future__ import annotations

import ctypes
import sys
from typing import List, Optional, Sequence, Tuple

import numpy as np

from bot.capture.backend import (
    BackendUnavailable,
    CaptureBackend,
    Rect,
    Rgb,
    create_backend,
)
from bot.capture.hwnd import (
    find_cef_hwnds,
    get_window_rect,
    hwnd_is_valid,
    resolve_hwnd,
)

_backend: Optional[CaptureBackend] = None


def init(prefer: Optional[str] = None) -> str:
    global _backend
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


def check_pixel_sync(
    nick: Optional[str],
    x: int,
    y: int,
    w: int,
    h: int,
    rgb: Rgb,
    thr: int,
) -> bool:
    return active().check_pixel(nick, x, y, w, h, rgb, thr)


async def wait_for_pixel(
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
    return await active().wait_for_pixel(nick, x, y, w, h, rgb, thr, timeout, poll)


async def capture_region(
    nick: Optional[str],
    x: int,
    y: int,
    w: int,
    h: int,
) -> np.ndarray:
    return await active().capture_region_async(nick, x, y, w, h)


async def capture_regions(
    nick: Optional[str],
    rects: Sequence[Tuple[int, int, int, int]],
) -> List[np.ndarray]:
    return await active().capture_regions_async(nick, rects)


def release(nick: Optional[str]) -> None:
    if _backend is None:
        return
    try:
        _backend.release(nick)
    except Exception:
        pass


__all__ = [
    "BackendUnavailable",
    "CaptureBackend",
    "Rect",
    "Rgb",
    "active",
    "backend_name",
    "capture_region",
    "capture_regions",
    "check_pixel_sync",
    "find_cef_hwnds",
    "get_window_rect",
    "hwnd_is_valid",
    "init",
    "monitors",
    "release",
    "resolve_hwnd",
    "wait_for_pixel",
]
