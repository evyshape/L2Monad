from bot.methods.base import parseCBT


class GameAction:
    def __init__(self, profile):
        self.profile = profile

    @property
    def window_id(self) -> str:
        return self.profile.window_id

    @property
    def window_info(self) -> dict:
        return self.profile.window_info

    @property
    def mouse(self):
        return self.profile.mouse

    @property
    def settings(self):
        return self.profile.settings

    @property
    def runtime(self):
        return self.profile.runtime_data

    async def has(self, tag: str, *, timeout: float = 0.2, thr: float = 3,
                  wsize: str = "2x2") -> bool:
        xy, rgb = parseCBT(tag, profile=self.profile)
        if xy is None:
            return False
        return await self.profile.check_pixel(xy, rgb, timeout=timeout, thr=thr, wsize=wsize)

    async def click(self, tag: str) -> bool:
        xy, _ = parseCBT(tag, profile=self.profile)
        if xy is None:
            return False
        await self.mouse.click(self.window_info, *xy)
        return True

    async def wait_and_click(self, tag: str, *, timeout: float = 5, thr: float = 3,
                             wsize: str = "2x2") -> bool:
        xy, rgb = parseCBT(tag, profile=self.profile)
        if xy is None:
            return False
        if await self.profile.check_pixel(xy, rgb, timeout=timeout, thr=thr, wsize=wsize):
            await self.mouse.click(self.window_info, *xy)
            return True
        return False