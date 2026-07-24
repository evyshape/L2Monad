import asyncio

from bot.clogger import log
from bot.delays import DELAY_AUTOHUNT_CHECK, THR_CHECK_AUTOHUNT
from bot.methods.base import parseCBT
from bot.methods.game._base import GameAction


class Combat(GameAction):

    async def toggle_autohunt(self) -> bool:
        button_xy, _ = parseCBT("auto_combat_mode_gui", profile=self.profile)
        if button_xy is None:
            return False
        button_x, button_y = button_xy
        click = await self.mouse.click(self.window_info, button_x, button_y)
        return bool(click)

    async def is_autohunt_on(self) -> bool:
        xy1, rgb1 = parseCBT("auto_combat_ON", profile=self.profile)
        success = 0
        await asyncio.sleep(0.05)

        for _ in range(2):
            await asyncio.sleep(0.1)
            teleported = await self.profile.check_pixel(
                xy1, rgb1, timeout=DELAY_AUTOHUNT_CHECK,
                thr=THR_CHECK_AUTOHUNT, wsize="3x4",
            )
            if teleported:
                success += 1

        if success >= 1:
            log("hunt succ", self.window_id)
            return True
        log("no hunt", self.window_id)
        return False

    async def respawn(self) -> bool:
        self.profile.notify("warning", "Пробую воскресить чара")

        respawn_variants = (
            "respawn_village_1", "respawn_village_2", "respawn_village_3",
            "check_death_penalty_1", "check_death_penalty_2", "check_death_penalty_3",
        )

        async def find_btn(timeout=0.5):
            parsed = [(parseCBT(tag, profile=self.profile)) for tag in respawn_variants]
            valid = [(xy, rgb) for xy, rgb in parsed if xy is not None]
            if not valid:
                return None
            results = await asyncio.gather(*(
                self.profile.check_pixel(xy, rgb, timeout=timeout)
                for xy, rgb in valid
            ))
            for (xy, _), found in zip(valid, results):
                if found:
                    return xy
            return None

        emode = await self.profile.energo.is_on()

        xy = await find_btn(timeout=0.5)

        if xy is None and emode:
            await self.profile.energo.turn_off(ignore=True)
            await asyncio.sleep(2)
            xy = await find_btn(timeout=2)

        if xy is None:
            log("Не нашёл кнопку респавна", self.window_id)
            return False

        await self.mouse.click(self.window_info, xy[0], xy[1], fast=True)
        await asyncio.sleep(8)
        if emode and not await self.profile.energo.is_on():
            await self.profile.energo.turn_on()
            await asyncio.sleep(1)
        return True

    async def is_dead(self) -> tuple[bool, str]:
        rips = {
            "you_were_killed_energomode": [
                "you_were_killed_energomode_1",
                "you_were_killed_energomode_2",
                "you_were_killed_energomode_3",
            ],
            "check_death_penalty": [
                "check_death_penalty_1",
                "check_death_penalty_2",
                "check_death_penalty_3",
            ],
            "respawn_village": [
                "respawn_village_1",
                "respawn_village_2",
                "respawn_village_3",
            ],
        }

        async def check(cbt: str) -> bool:
            xy, rgb = parseCBT(cbt, profile=self.profile)
            return await self.profile.check_pixel(xy, rgb, timeout=0.65, thr=4)

        for key, cbts in rips.items():
            results = await asyncio.gather(*(check(cbt) for cbt in cbts))
            if all(results):
                log(f"Детектнул {key}", self.window_id)
                return True, cbts[1]

        return False, ""

    async def has_adena(self) -> bool:
        xy, rgb = parseCBT("monetka_gui", profile=self.profile)
        return await self.profile.check_pixel(xy, rgb, timeout=1, thr=7, wsize="2x2")
