import asyncio
import random

from bot.clogger import log
from bot.delays import (
    DELAY_TELEPORT_TO_HOME,
    DELAY_WAIT_WAIT_TELEPORT,
    WAIT_BEFORE_TELEPORT_TO_SPOT,
)
from bot.methods.base import parseCBT
from bot.methods.game._base import GameAction


class Teleport(GameAction):

    async def safe_home(self) -> bool:
        targets = [
            parseCBT("home_scroll_button_energomode", profile=self.profile),
            parseCBT("home_scroll_button_no_energomode", profile=self.profile),
        ]

        tasks = [
            asyncio.create_task(self.profile.check_pixel(xy, rgb, timeout=5, thr=8))
            for xy, rgb in targets
        ]

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task, (xy, _) in zip(tasks, targets):
            if task in done and task.result() is True:
                for p in pending:
                    p.cancel()
                return await self.mouse.click(self.window_info, *xy, fast=True)

        for p in pending:
            p.cancel()

        log("Были либо в стане либо нет свитков, не тпнулся =(", self.window_id)
        self.profile.notify("error", "Чет могло жестко сломаться, не смогли тп в город")
        return False

    async def wait_arrived(self, need: int = 7, _lvlup_retries: int = 3) -> bool:
        xy1, rgb1 = parseCBT("zalupka_gui", profile=self.profile)
        thr = 36 if self.settings.REGION == "RU" else 12

        for retry in range(_lvlup_retries + 1):
            success = 0
            log(f"Сплю {DELAY_WAIT_WAIT_TELEPORT} сек. в вейт телепорте", self.window_id)
            await asyncio.sleep(DELAY_WAIT_WAIT_TELEPORT)

            if need != 1:
                log("чекаю инет ошибку...", self.window_id)
                if await self.profile.errors.has_ethernet1():
                    await self.profile.errors.close_ethernet1()
                    await asyncio.sleep(1)

            for i in range(need):
                log(f"{i+1}/{need} чекаю пиксель...", self.window_id)
                await asyncio.sleep(0.25)
                teleported = await self.profile.check_pixel(
                    xy1, rgb1, timeout=DELAY_TELEPORT_TO_HOME, thr=thr,
                )
                log(f"{i+1} teleported={teleported}", self.window_id)
                if teleported:
                    success += 1

            log(success, self.window_id)
            if success >= (need + 1) // 2:
                log(f"tped succ | {success}/{need}", self.window_id)
                return True

            lvlup = await self.profile.energo.check_lvl_up()
            if not lvlup:
                log(f"tped failed | {success}/{need}", self.window_id)
                return False
            log(f"lvl up детектнут, retry {retry+1}/{_lvlup_retries}", self.window_id)

        log(f"tped failed после {_lvlup_retries} lvlup-retry", self.window_id)
        return False

    async def to_random_spot(self, from_: int = 1, to_: int = 4, fast: bool = True) -> bool:

        async def ah() -> bool:
            await asyncio.sleep(0.15)
            await self.profile.energo.turn_on()
            await asyncio.sleep(0.05)

            if await self.profile.combat.is_autohunt_on():
                log("Автобой включен", self.window_id)
                self.runtime.update_last_return()
                self.profile.notify("trash", "Тпнулся на спот успешно")
                return True
            return False

        await asyncio.sleep(0.2)
        spot = random.randint(from_, to_)
        log(f"Пробую тпнуться на спот №{spot}", self.window_id)

        if not fast and await self.profile.energo.is_on():
            log("Был в энерго, вырубаю перед тп", self.window_id)
            await self.profile.energo.turn_off()

        await asyncio.sleep(WAIT_BEFORE_TELEPORT_TO_SPOT)

        steps = [
            "spot_teleport_call_button",
            f"spot_choice_{spot}",
            f"spot_accept_choice_{spot}",
        ]

        hunt = await self.profile.combat.toggle_autohunt()
        if not hunt:
            return False

        await asyncio.sleep(0.5)

        for key in steps:
            xy, rgb = parseCBT(key, profile=self.profile)
            if not await self.profile.check_pixel(xy, rgb, timeout=3):
                log(f"Не нашел {key} за 3 сек", self.window_id)
                return False
            x, y = xy
            if not await self.mouse.click(self.window_info, x, y):
                log(f"Не удалось нажать на {key} ({x}, {y})", self.window_id)
                return False
            await asyncio.sleep(random.uniform(0.2, 0.5))

        if not await self.wait_arrived(need=4):
            log("Недостаточно срабатываний залупки", self.window_id)
            return False

        log("Залупка найдена, включаю энерго", self.window_id)
        await asyncio.sleep(0.35)

        if await ah():
            return True

        if await self.profile.energo.is_on():
            rip, btn = await self.profile.combat.is_dead()
            if rip:
                log("Сдох, мдо?", self.window_id)
                return True
            log("Не сдох но стою без автобоя, чинюсь", self.window_id)
            await self.profile.energo.turn_off()
            await asyncio.sleep(3)
            await self.profile.combat.toggle_autohunt()
            await asyncio.sleep(1)
            if await ah():
                return True
        else:
            log("Почему окно не в энерго?", self.window_id)

        self.profile.notify_screenshot(
            "Кажись залип, не включился автобой?\n"
            "Перезапусти окно вручную и отправь фидбек разрабу"
        )
        return False

