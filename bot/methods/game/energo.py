import asyncio
import math

from bot.clogger import log
from bot.delays import (
    DELAY_AFTER_CLICK_ENERGO,
    DELAY_CHECK_ENERGO,
    SLEEP_AFTER_UNBLOCK,
)
from bot.events.enums import MonitorType
from bot.methods.base import parseCBT
from bot.methods.game._base import GameAction


class Energo(GameAction):

    async def is_on(self) -> bool:
        xy, rgb = parseCBT("energomode_center_gui", profile=self.profile)
        if not await self.profile.check_pixel(xy, rgb, timeout=DELAY_CHECK_ENERGO):
            log("Не находимся в энерго", self.window_id)
            return False
        log("Находимся в энергорежиме", self.window_id)
        return True

    async def turn_on(self) -> bool:
        button_xy, _ = parseCBT("energo_mode_gui", profile=self.profile)
        button_x, button_y = button_xy
        window = self.window_info[self.window_id]
        width = window["Width"]
        height = window["Height"]

        await self.mouse.click(self.window_info, button_x, button_y)
        await asyncio.sleep(DELAY_AFTER_CLICK_ENERGO)
        await asyncio.sleep(0.1)

        center_x = width // 2
        center_y = height // 2

        if self.settings.PEACE_MODE:
            peace_xy, peace_rgb = parseCBT("peace_off", profile=self.profile)
            peace = await self.profile.check_pixel(peace_xy, peace_rgb, timeout=0.2, thr=5)
            if peace:
                await self.mouse.click(self.window_info, peace_xy[0], peace_xy[1])
                log("Врубил мирку, была выключена", self.window_id)
                await asyncio.sleep(0.15)

        await self.mouse.click(self.window_info, center_x, center_y)
        return True

    async def turn_off(self, ignore: bool = False) -> bool:
        window = self.window_info[self.window_id]
        width = window["Width"]
        height = window["Height"]

        running = self.profile.events_checker.get_running(self.window_id)
        health_was_on = MonitorType.HEALTH in running
        if health_was_on:
            self.profile.events_checker.stop_once(self.window_id, MonitorType.HEALTH)

        center_x = width // 2
        center_y = height // 2
        radius = 15

        points = []
        for i in range(7):
            angle = math.pi / 8 + 2 * math.pi * i / 5
            x = center_x + radius * math.cos(angle)
            y = center_y - radius * math.sin(angle)
            points.append((x, y))

        swipe_points = [points[0], points[2], points[0], points[5]]
        await self.mouse.swipe(self.window_info, swipe_points, delay_points=0.08)

        xy1, rgb1 = parseCBT("zalupka_gui", profile=self.profile)
        await asyncio.sleep(SLEEP_AFTER_UNBLOCK)
        if health_was_on:
            self.profile.events_checker.start_monitoring(
                self.window_id, self.profile, [MonitorType.HEALTH]
            )

        eth_err = await self.profile.errors.has_ethernet1()
        if eth_err:
            await self.profile.errors.close_ethernet1()
            await asyncio.sleep(3)

        thr = 17 if self.settings.REGION == "RU" else 2
        teleported = await self.profile.check_pixel(xy1, rgb1, timeout=10, thr=thr)
        if teleported or ignore:
            return True

        if await self.is_on():
            repeat_points = [
                (center_x, center_y),
                (center_x - 75, center_y - 50),
            ]
            await self.mouse.swipe(self.window_info, repeat_points, delay_points=0.2)
            await asyncio.sleep(0.2)

        await asyncio.sleep(SLEEP_AFTER_UNBLOCK)
        teleported = await self.profile.check_pixel(xy1, rgb1, timeout=3)
        if teleported:
            return True

        return False

    async def check_lvl_up(self) -> bool:
        need = ["lvl_up_black_2", "lvl_up_black"]
        results = [
            await self.profile.check_pixel(
                *parseCBT(lvl_name, profile=self.profile),
                timeout=0.3, wsize="1x1", thr=1,
            )
            for lvl_name in need
        ]

        if all(results):
            log("Лвл ап вылез, закрываю", self.window_id)
            xy_close, _ = parseCBT("lvl_up_close", profile=self.profile)
            await self.mouse.click(self.window_info, *xy_close)
            self.profile.notify("info", "Перс апнул лвл, будь во внимании и качни поинт!")
            await asyncio.sleep(1.3)
            return True

        log(f"Вероятно лвл апа не было {results}", self.window_id)
        return False

    async def has_quiver(self) -> bool | None:
        if not await self.is_on():
            return None
        xy1, rgb1 = parseCBT("q_quiver", profile=self.profile)
        quiver = await self.profile.check_pixel(xy1, rgb1, timeout=2, thr=2, wsize="1x1")
        return not quiver
