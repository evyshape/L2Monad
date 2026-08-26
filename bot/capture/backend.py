from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence, Tuple

import numpy as np


Rgb = Tuple[int, int, int]
Rect = Tuple[int, int, int, int]


class CaptureBackend(ABC):
    name: str

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def capture_region(
        self,
        nick: Optional[str],
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> np.ndarray:
        raise NotImplementedError

    @abstractmethod
    def monitors(self) -> List[Rect]:
        raise NotImplementedError

    async def capture_region_async(
        self,
        nick: Optional[str],
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> np.ndarray:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.capture_region, nick, x, y, w, h
        )

    def capture_regions(
        self,
        nick: Optional[str],
        rects: Sequence[Tuple[int, int, int, int]],
    ) -> List[np.ndarray]:
        return [self.capture_region(nick, x, y, w, h) for x, y, w, h in rects]

    async def capture_regions_async(
        self,
        nick: Optional[str],
        rects: Sequence[Tuple[int, int, int, int]],
    ) -> List[np.ndarray]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.capture_regions, nick, list(rects)
        )

    def release(self, nick: Optional[str]) -> None:
        return None


class BackendUnavailable(RuntimeError):
    pass


def create_backend(prefer: Optional[str] = None) -> CaptureBackend:
    if prefer in (None, "auto"):
        order = ("rust", "mss")
    elif prefer in ("rust", "mss"):
        order = (prefer,)
    else:
        raise ValueError(f"unknown backend '{prefer}'; expected 'auto', 'rust', or 'mss'")

    errors: list[str] = []
    for name in order:
        try:
            if name == "rust":
                from bot.capture.rust_backend import RustBackend

                return RustBackend()
            if name == "mss":
                from bot.capture.mss_backend import MssBackend

                return MssBackend()
        except BackendUnavailable as e:
            errors.append(f"{name}: {e}")
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")

    raise BackendUnavailable("no capture backend available: " + " | ".join(errors))
