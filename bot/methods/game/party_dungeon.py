import asyncio

import numpy as np

from bot.clogger import log
from bot.constans import PARTY_DUNGEON_CONS
from bot.methods.base import parseCBT
from bot.events.enums import Region
from bot.methods.game._base import GameAction


class PartyDungeon(GameAction):

    def __init__(self, profile):
        super().__init__(profile)
        self.button_name = "autohunt_no_limit"
        self.states = 4
        self.clicks = None
        self.region = profile.settings.REGION

    async def wait_and_click(self, tag, *, timeout: float = 5, thr: float = 2,
                             wsize: str = "2x2") -> bool:
        return await super().wait_and_click(tag, timeout=timeout, thr=thr, wsize=wsize)

    async def _detect(self) -> bool:
        xy, rgb = parseCBT(self.button_name, profile=self.profile)
        return await self.profile.check_pixel(xy, rgb, timeout=0.3, thr=30, wsize="1x1")

    async def _click_button(self, button_name):
        xy, _ = parseCBT(button_name, profile=self.profile)
        x, y = xy
        await self.mouse.click(self.window_info, x, y)

    async def no_limit(self, max_clicks: int = 8) -> int:
        log("no_limit: старт", self.window_id)
        count = 0
        await self._click_button("energo_mode_gui")

        while count < max_clicks:
            if await self._detect():
                self.clicks = count
                log(f"no_limit: детект на клике {count}", self.window_id)
                await self.mouse.click(self.window_info, 200, 100)
                await asyncio.sleep(0.2)
                return count

            await self._click_button(self.button_name)
            count += 1
            await asyncio.sleep(0.2)

        self.clicks = count
        log("no_limit: max_clicks исчерпан", self.window_id)
        return count

    async def to_start(self) -> int:
        if self.clicks is None:
            log("to_start: clicks=None, скипаю", self.window_id)
            return 0
        needed = (self.states - self.clicks) % self.states
        log(f"to_start: needed={needed}", self.window_id)
        await self._click_button("energo_mode_gui")
        await asyncio.sleep(2)
        for _ in range(needed):
            await self._click_button(self.button_name)
            await asyncio.sleep(0.2)

        await self.wait_and_click("main_menu_gui")
        await asyncio.sleep(0.2)
        return needed

    async def open_dungeon(self):
        r1 = await self.wait_and_click("main_menu_gui")
        r2 = await self.wait_and_click("dungeon_button_menu")
        r3 = await self.wait_and_click("party_dungeon_button")
        if all([r1, r2, r3]):
            log("open_dungeon: ок", self.window_id)
            return True
        log(f"open_dungeon: fail main={r1} dungeon={r2} tab={r3}", self.window_id)
        return False

    async def party_create(self):
        log("party_create: старт", self.window_id)
        xy, rgb = parseCBT("white_cube_in_minimap", profile=self.profile)
        result = await self.profile.check_pixel(xy, rgb, timeout=1, thr=30)
        if not result:
            log("party_create: тыкаю npc_list", self.window_id)
            await self.wait_and_click("npc_list_in_town")
            await asyncio.sleep(2)

        r1 = await self.wait_and_click("party_group")
        await asyncio.sleep(1)
        r2 = await self.wait_and_click("party_settings")
        r3 = await self.wait_and_click("party_dungeon_create_button")
        r4 = await self.wait_and_click("party_close")
        await asyncio.sleep(1.5)
        r5 = await self.wait_and_click("party_close")
        if all([r1, r2, r3, r4]):
            log("party_create: ок", self.window_id)
            return True

        log(f"party_create: fail group={r1} settings={r2} create={r3} close1={r4} close2={r5}", self.window_id)
        return False

    async def party_leave(self):
        log("party_leave: старт", self.window_id)
        await asyncio.sleep(2)
        xy, rgb = parseCBT("white_cube_in_minimap", profile=self.profile)
        result = await self.profile.check_pixel(xy, rgb, timeout=1, thr=30)
        if not result:
            log("party_leave: тыкаю npc_list", self.window_id)
            await self.wait_and_click("npc_list_in_town")
            await asyncio.sleep(2.5)

        await asyncio.sleep(2)
        r1 = await self.wait_and_click("party_leave_1")
        await asyncio.sleep(2)
        r2 = await self.wait_and_click("party_leave_2")
        await asyncio.sleep(1)
        if all([r1, r2]):
            log("party_leave: ок", self.window_id)
            return True

        log(f"party_leave: fail step1={r1} step2={r2}", self.window_id)
        return False

    async def find_dungeon(self, max_scrolls=3, scrolls=15, thr=2):
        cfg = PARTY_DUNGEON_CONS.get(self.region, PARTY_DUNGEON_CONS[Region.RU])

        x_need = cfg["x"]
        y_start, y_end = cfg["scroll"]
        needs = np.array(
            [list(map(int, c.split(","))) for c in cfg["need"]],
            dtype=np.int16,
        )

        for attempt in range(max_scrolls):
            rect = (x_need, y_start, 1, y_end - y_start + 1)
            imgs = await self.profile.capture_multy([rect])
            img = imgs[0][:, :, :3]
            column = img[:, 0, :].astype(np.int16)
            diffs = np.abs(column[:, None, :] - needs)
            row_match = np.any(np.all(diffs <= thr, axis=-1), axis=-1)
            match_idx = np.where(row_match)[0]
            if len(match_idx):
                y_pix = y_start + int(match_idx[0])
                log(f"find_dungeon: нашёл на попытке {attempt+1}, y={y_pix}", self.window_id)
                return (x_need, y_pix)

            pos = (x_need, (y_start + y_end) // 2)
            await self.mouse.wheel(self.window_info, [pos],
                                   direction="down", times=scrolls)

        log("find_dungeon: не нашёл", self.window_id)
        return None

    async def click_portal(self, thr=15, attempts=5, delay=1.3):
        cfg = PARTY_DUNGEON_CONS.get(self.region, PARTY_DUNGEON_CONS[Region.RU])

        xy_str, color_str = cfg["portal"]
        x_range, y_str = xy_str.split(",")
        x_start, x_end = map(int, x_range.split("-"))
        y = int(y_str.strip())

        target = np.array(list(map(int, color_str.split(","))), dtype=np.int16)
        rect = (x_start, y, x_end - x_start, 1)

        for attempt in range(attempts):
            imgs = await self.profile.capture_multy([rect])
            img = imgs[0][:, :, :3]
            row = img[0, :, :].astype(np.int16)
            diffs = np.abs(row - target)
            mask = np.all(diffs <= thr, axis=-1)
            indices = np.where(mask)[0]
            if len(indices):
                x_pix = x_start + int(indices[-1])
                log(f"click_portal: клик по x={x_pix}", self.window_id)
                await self.mouse.click(self.window_info, x_pix, y)
                await asyncio.sleep(0.2)
                return True

            await asyncio.sleep(delay)

        log(f"click_portal: не нашёл за {attempts} попыток", self.window_id)
        return False

    async def start_dungeon(self, xy):
        if not xy:
            log("start_dungeon: xy пустой", self.window_id)
            return False

        log(f"start_dungeon: старт xy={xy}", self.window_id)
        await self.mouse.click(self.window_info, xy[0], xy[1])
        await asyncio.sleep(0.1)
        await self.wait_and_click("party_dungeon_join")
        await asyncio.sleep(1)
        hard = int(self.settings.PARTY_DUNGEON_HARD)
        log(f"start_dungeon: сложность {hard}", self.window_id)
        await self.wait_and_click(f"party_dungeon_hard_{hard}")
        await self.wait_and_click("party_dungeon_join2")
        await asyncio.sleep(1.5)
        portal = await self.click_portal()
        if portal:
            await self.wait_and_click("party_dungeon_join3")
            await asyncio.sleep(1)
            await self.profile.tp.wait_arrived(5)
            log("start_dungeon: ок", self.window_id)
            return True

        log("start_dungeon: портал не найден", self.window_id)
        return False
