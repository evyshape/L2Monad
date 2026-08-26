from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple


_HWND_CACHE_TTL = 5.0
_hwnd_cache: Dict[str, Tuple[int, float]] = {}
_hwnd_cache_lock = threading.Lock()


def resolve_hwnd(nick: str) -> Optional[int]:
    if sys.platform != "win32":
        return None
    now = time.monotonic()
    with _hwnd_cache_lock:
        cached = _hwnd_cache.get(nick)
    if cached is not None and (now - cached[1]) < _HWND_CACHE_TTL:
        try:
            if ctypes.windll.user32.IsWindow(int(cached[0])):
                return int(cached[0])
        except Exception:
            pass
        with _hwnd_cache_lock:
            _hwnd_cache.pop(nick, None)
    try:
        from bot.utils import findAllWindows
    except Exception:
        return None
    try:
        windows = findAllWindows()
    except Exception:
        return None
    info = windows.get(nick)
    if not info:
        return None
    hwnd = info.get("ID")
    if not hwnd:
        return None
    try:
        if not ctypes.windll.user32.IsWindow(int(hwnd)):
            return None
    except Exception:
        return None
    hwnd = int(hwnd)
    with _hwnd_cache_lock:
        _hwnd_cache[nick] = (hwnd, now)
    return hwnd


def hwnd_is_valid(hwnd: Optional[int]) -> bool:
    if not hwnd or sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.user32.IsWindow(int(hwnd)))
    except Exception:
        return False


def get_window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    if sys.platform != "win32":
        return None
    try:
        r = wt.RECT()
        if not ctypes.windll.user32.GetWindowRect(int(hwnd), ctypes.byref(r)):
            return None
        return (int(r.left), int(r.top), int(r.right - r.left), int(r.bottom - r.top))
    except Exception:
        return None


def find_cef_hwnds() -> List[Tuple[int, str]]:
    if sys.platform != "win32":
        return []
    user32 = ctypes.windll.user32
    EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    out: List[Tuple[int, str]] = []

    def _cb(hwnd, _lparam):
        cls_buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, cls_buf, 64)
        if cls_buf.value != "CEFCLIENT":
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or ""
        if "index.html?type=live" in title:
            out.append((int(hwnd), title))
        return True

    try:
        user32.EnumWindows(EnumWindowsProc(_cb), 0)
    except Exception:
        return []
    return out
