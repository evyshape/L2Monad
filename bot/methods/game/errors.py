import asyncio
import random

from bot.clogger import log
from bot.delays import SLEEP_AFTER_CONNECT
from bot.methods.base import parseCBT
from bot.methods.game._base import GameAction


class ErrorHandler(GameAction):

    async def has_ethernet2(self) -> bool:
        triggers = [
            "error_disconnect_to_menu_with_err_trigger1",
            "error_disconnect_to_menu_with_err_trigger2",
            "error_disconnect_to_menu_with_err_trigger3",
            "error_disconnect_to_menu_with_err_trigger4",
        ]

        async def check(cbt: str) -> bool:
            xy, rgb = parseCBT(cbt, profile=self.profile)
            return await self.profile.check_pixel(xy, rgb, timeout=2, thr=1)

        total = 0
        for _ in range(5):
            results = await asyncio.gather(*(check(t) for t in triggers))
            if all(results):
                total += 1
                if total > 4:
                    log("Детектнул error_disconnect_to_menu_with_err =(", self.window_id)
                    return True
            await asyncio.sleep(3)

        return False

    async def close_ethernet2(self) -> bool:
        await asyncio.sleep(2)
        log("Пробую закрыть инет2 ошибку", self.window_id)
        xy, rgb = parseCBT("error_disconnect_to_menu_with_err", self.profile)
        if await self.profile.check_pixel(xy, rgb, timeout=2, thr=1):
            await self.mouse.click(self.window_info, xy[0], xy[1])
            await asyncio.sleep(1)
            return True
        return False

    async def has_ethernet1(self) -> bool:
        triggers = [
            "error_ethernet_1_trigger1",
            "error_ethernet_1_trigger2",
            "error_ethernet_1_trigger3",
            "error_ethernet_1_trigger4",
        ]

        async def check(cbt: str) -> bool:
            xy, rgb = parseCBT(cbt, profile=self.profile)
            return await self.profile.check_pixel(xy, rgb, timeout=0.2, thr=1)

        total = 0
        for _ in range(2):
            results = await asyncio.gather(*(check(t) for t in triggers))
            if all(results):
                total += 1
                if total > 1:
                    log("Детектнул error_ethernet_1 =(", self.window_id)
                    return True
            await asyncio.sleep(0.2)

        return False

    async def close_ethernet1(self) -> bool:
        await asyncio.sleep(2)
        log("Пробую закрыть инет ошибку", self.window_id)
        xy, rgb = parseCBT("error_ethernet_1", self.profile)
        if await self.profile.check_pixel(xy, rgb, timeout=2, thr=1):
            await self.mouse.click(self.window_info, xy[0], xy[1])
            await asyncio.sleep(1)
            return True
        return False

    async def is_disconnected(self) -> bool:
        triggers = [
            "error_disconnect_to_menu_trigger1",
            "error_disconnect_to_menu_trigger2",
            "error_disconnect_to_menu_trigger3",
            "error_disconnect_to_menu_trigger4",
        ]

        async def check(cbt: str) -> bool:
            xy, rgb = parseCBT(cbt, profile=self.profile)
            return await self.profile.check_pixel(xy, rgb, timeout=3, thr=0)

        total = 0
        for _ in range(5):
            results = await asyncio.gather(*(check(t) for t in triggers))
            if all(results):
                total += 1
                if total > 4:
                    log("Детектнул error_disconnect_to_menu, нас дисконектнуло =(", self.window_id)
                    return True
            await asyncio.sleep(3)

        return False

    async def connect(self) -> bool:
        await asyncio.sleep(4)
        xy, rgb = parseCBT("error_disconnect_to_menu", self.profile)
        await self.mouse.click(self.window_info, xy[0], xy[1])
        await asyncio.sleep(8)
        await self.mouse.click(self.window_info, xy[0], xy[1])
        await asyncio.sleep(2)
        await self.mouse.click(self.window_info, xy[0], xy[1])

        xy, rgb = parseCBT("enter_to_server", self.profile)
        found = None
        for _ in range(7):
            found = await self.profile.check_pixel(xy, rgb, timeout=3, wsize="2x2")
            if found:
                break
            await asyncio.sleep(1.5)

        if found:
            log("Пробую конект к серверу, загрузился к выбору персов", self.window_id)
            await asyncio.sleep(random.uniform(1, 2))
            await self.mouse.click(self.window_info, xy[0], xy[1])
            await asyncio.sleep(SLEEP_AFTER_CONNECT)
            log("Законектился на сервер", self.window_id)
            return True

        log("Шото страшное и необработанное =(", self.window_id)
        return False
