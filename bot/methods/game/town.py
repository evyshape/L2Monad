import asyncio
import json
import random
from typing import Dict, Optional

from bot.clogger import log
from bot.delays import (
    DELAY_CHECK_NPC_POSITIONS,
    THR_CHECK_NPC_POSITIONS,
)
from bot.methods.base import parseCBT
from bot.events.enums import Region
from bot.methods.game._base import GameAction


class Town(GameAction):

    async def find_npcs(self, thr: int = THR_CHECK_NPC_POSITIONS,
                        retries: int = 2) -> Optional[Dict[str, str]]:
        npc_batches = [[2, 3]]
        if await self.profile.errors.has_ethernet1():
            await self.profile.errors.close_ethernet1()
            await asyncio.sleep(0.7)

        await self.profile.energo.check_lvl_up()

        await self.mouse.wheel(
            self.window_info,
            [(30, 100)],
            direction="up",
            times=10,
        )

        # todo if not floran:
        # for attempt in range(1, retries + 1):
        #     log(f"Попытка {attempt}/{retries} получить позиции нпс", self.window_id)
        #
        #     found_j = None
        #
        #     for batch in npc_batches:
        #         async def check_npc(j):
        #             xy, rgb = parseCBT(f"npc_list_{j}", profile=self.profile)
        #             result = await self.profile.check_pixel(
        #                 xy, rgb,
        #                 timeout=DELAY_CHECK_NPC_POSITIONS,
        #                 thr=thr, wsize="1x1",
        #             )
        #             return j if result else None
        #
        #         results = await asyncio.gather(*(check_npc(j) for j in batch))
        #         found_j = min([r for r in results if r is not None], default=None)
        #
        #         if found_j:
        #             break
        #
        #     if found_j:
        #         log(f"Детектнул позиции, {found_j}", self.window_id)
        #         if found_j == 2:
        #             npc_mapping = {"stash": "npc_list_2", "shop": "npc_list_1", "buyer": "npc_list_4"}
        #         elif found_j == 3:
        #             npc_mapping = {"stash": "npc_list_3", "shop": "npc_list_1", "buyer": "npc_list_5"}
        #
        #         self.runtime.update_last_mapping(npc_mapping)
        #         log(f"NPC mapping: {json.dumps(npc_mapping, indent=4)}", self.window_id)
        #         await self.mouse.wheel(
        #             self.window_info,
        #             [[random.randint(141, 246), random.randint(50, 139)]],
        #             direction="down",
        #             times=15,
        #         )
        #         return npc_mapping
        #
        #     await asyncio.sleep(0.3)

        #log(f"get_npc_positions false, не обнаружил npc за {retries} попыток, пробую прокруткой", self.window_id)
        for _ in range(2):
            await self.mouse.wheel(
                self.window_info,
                [(30, 100)],
                direction="down",
                times=15,
            )
            await asyncio.sleep(random.uniform(0.1, 0.3))

        await asyncio.sleep(random.uniform(0.1, 0.3))
        if self.settings.REGION == Region.RU:
            for _ in range(1):
                await self.mouse.wheel(self.window_info, [(38, 104)], direction="up", times=9)
                await asyncio.sleep(0.25)
            return {"stash": "npc_list_3", "shop": "npc_list_1", "buyer": "npc_list_5"}

        elif self.settings.REGION == Region.JP:
            for _ in range(1):
                await self.mouse.wheel(self.window_info, [(38, 104)], direction="up", times=7)
                await asyncio.sleep(0.25)
            return {"stash": "npc_list_3", "shop": "npc_list_1", "buyer": "npc_list_5"}

        return None

    async def is_in(self) -> tuple[bool, dict | None]:
        timeout = 50
        loop = asyncio.get_running_loop()
        start_time = loop.time()
        log(f"Начал проверять в городе ли я, таймаут: {timeout}", self.window_id)

        if await self.profile.errors.has_ethernet1():
            await self.profile.errors.close_ethernet1()
            await asyncio.sleep(1)

        while loop.time() - start_time < timeout:
            xy, rgb = parseCBT("white_cube_in_minimap", profile=self.profile)
            log("Чекаю белый кубик на мапе", self.window_id)
            if xy is None or rgb is None:
                return False, None

            result = await self.profile.check_pixel(xy, rgb, timeout=1)
            if result:
                log("Белый кубик найден, открываю список нпс", self.window_id)
                xy_btn, _ = parseCBT("npc_list_in_town", profile=self.profile)
                if xy_btn is None:
                    return False, None

                x, y = xy_btn
                click_result = await self.mouse.click(self.window_info, x, y)
                if click_result:
                    log("Открыл список нпс, получаю позиции", self.window_id)
                    await asyncio.sleep(0.03)
                    allNPC = await self.find_npcs()
                    if allNPC:
                        log("Нахожусь в городе, список нпс открыт", self.window_id)
                        return True, allNPC
            else:
                log("Белого кубика не было, карты нет. чекаю позиции в тупую", self.window_id)
                allNPC = await self.find_npcs()
                if allNPC:
                    log("Список нпс уже открыт, мы в городе", self.window_id)
                    return True, allNPC

                rip, btn = await self.profile.combat.is_dead()
                if rip:
                    log("Умер прямо в момент тпшки в город, ресаюсь", self.window_id)
                    res = await self.profile.combat.respawn()
                    if res:
                        await asyncio.sleep(1.2)
                        allNPC = await self.find_npcs()
                        if allNPC:
                            log("Список нпс уже открыт, мы в городе", self.window_id)
                            return True, allNPC
                        self.profile.notify_screenshot("Кажись залипли, #важно")
                        log("Не нашел нпс, верну False", self.window_id)
                        return False, None

                log("Все условия не пройдены, жесть", self.window_id)

            await asyncio.sleep(0.5)

        log("Не удалось определить, в городе ли мы =( (ТАЙМАУТ ТИПО ИСТЕК)", self.window_id)
        return False, None

    async def buy_in_shop(self, in_town=None, npcs=None,
                          check_loot: bool = False) -> tuple[bool, bool, dict]:
        self.runtime.update_buy()
        if in_town is None or npcs is None:
            in_town, npcs = await self.is_in()

        if not npcs:
            return False, None, None

        if 'shop' not in npcs or npcs['shop'] == "no_data":
            return False, in_town, npcs

        xy, rgb = parseCBT(npcs['shop'], profile=self.profile)
        if xy is None:
            return False, in_town, npcs

        if check_loot and self.settings.BUY_LOOT_TOWN:
            try_to_buy = await self.buy_loot(skip=True)
            if try_to_buy:
                log("Успешно выкупил шмотки пока пробегал в городе!", self.window_id)

        await self.mouse.click(self.window_info, *xy)

        xy_btn1, rgb_btn1 = parseCBT("npc_shop_button_1", profile=self.profile)
        if xy_btn1 is None:
            return False, in_town, npcs

        for _ in range(200):
            if await self.profile.check_pixel(xy_btn1, rgb_btn1, timeout=0.1):
                await asyncio.sleep(0.45)
                await self.mouse.click(self.window_info, *xy_btn1)
                break
            await asyncio.sleep(0.05)
        else:
            return False, in_town, npcs

        xy_btn2, rgb_btn2 = parseCBT("npc_shop_button_2", profile=self.profile)
        if xy_btn2 is None:
            return False, in_town, npcs

        if await self.profile.check_pixel(xy_btn2, rgb_btn2, timeout=1.5):
            await self.mouse.click(self.window_info, *xy_btn2)

            xy_no_adena, rgb_no_adena = parseCBT("npc_shop_button_no_adena", profile=self.profile)
            if xy_no_adena:
                for _ in range(5):
                    if await self.profile.check_pixel(xy_no_adena, rgb_no_adena, timeout=0.1):
                        xy_quit, _ = parseCBT("npc_global_quit_button", profile=self.profile)
                        xy_ok, rgb_ok = parseCBT("npc_shop_button_no_adena_confirm", profile=self.profile)
                        if xy_ok and await self.profile.check_pixel(xy_ok, rgb_ok, timeout=1):
                            await self.mouse.click(self.window_info, *xy_ok)
                            await asyncio.sleep(0.25)
                            await self.mouse.click(self.window_info, *xy_quit)
                        return True, in_town, npcs
                    await asyncio.sleep(0.1)

        xy_btn3, rgb_btn3 = parseCBT("npc_shop_button_3", profile=self.profile)
        if xy_btn3 and await self.profile.check_pixel(xy_btn3, rgb_btn3, timeout=1.5):
            await self.mouse.click(self.window_info, *xy_btn3)

        xy_quit, rgb_quit = parseCBT("npc_global_quit_button", profile=self.profile)
        if xy_quit and await self.profile.check_pixel(xy_quit, rgb_quit, timeout=4):
            await self.mouse.click(self.window_info, *xy_quit)
            await asyncio.sleep(0.25)
            return True, in_town, npcs

        return False, in_town, npcs

    async def go_stash(self, in_town=None, npcs=None) -> tuple[bool, bool, dict]:
        log("Старт go_stash", self.window_id)
        self.runtime.update_stashing()

        if in_town is None or npcs is None:
            log("чекаю нпс", self.window_id)
            in_town, npcs = await self.is_in()
            log(f"in_town: {in_town}, npcs: {npcs}", self.window_id)

        if not npcs:
            return False, None, None

        if 'stash' not in npcs or npcs['stash'] == "no_data":
            log("стеш не найден", self.window_id)
            return False, in_town, npcs

        xy, rgb = parseCBT(npcs['stash'], profile=self.profile)
        if xy is None:
            log("корды стеша не нашел", self.window_id)
            return False, in_town, npcs

        log(f"клик по стешу {xy}", self.window_id)
        await self.mouse.click(self.window_info, *xy)

        stash_buttons = ["npc_stash_button_1", "npc_stash_button_2"]
        for i, button in enumerate(stash_buttons):
            xy_btn, rgb_btn = parseCBT(button, profile=self.profile)
            if xy_btn is None:
                log(f"корды {button} не нашел", self.window_id)
                if i == 0:
                    return False, in_town, npcs
                continue

            if i == 0:
                log(f"жду {button}...", self.window_id)
                for _ in range(200):
                    if await self.profile.check_pixel(xy_btn, rgb_btn, timeout=0.2, thr=7):
                        await asyncio.sleep(0.45)
                        log(f"клик по {button} в {xy_btn}", self.window_id)
                        await self.mouse.click(self.window_info, *xy_btn)
                        break
                    await asyncio.sleep(0.05)
                else:
                    log(f"таймаут {button}", self.window_id)
                    return False, in_town, npcs
            else:
                if await self.profile.check_pixel(xy_btn, rgb_btn, timeout=1.5):
                    log(f"клац {button} в {xy_btn}", self.window_id)
                    await self.mouse.click(self.window_info, *xy_btn)
                else:
                    log(f"кнопка {button} не появилась", self.window_id)

        xy_quit, rgb_quit = parseCBT("npc_global_quit_button", profile=self.profile)
        if xy_quit and await self.profile.check_pixel(xy_quit, rgb_quit, timeout=4):
            log(f"клацнул выход {xy_quit}", self.window_id)
            await self.mouse.click(self.window_info, *xy_quit)
            await asyncio.sleep(0.25)
            log("завершил функу", self.window_id)
            return True, in_town, npcs

        log("не завершил функу", self.window_id)
        return False, in_town, npcs

    async def sell_to_buyer(self, in_town=None, npcs=None) -> tuple[bool, bool, dict]:
        log("Старт sell_buyer", self.window_id)
        self.runtime.update_purc()

        if in_town is None or npcs is None:
            log("чекаю нпс", self.window_id)
            in_town, npcs = await self.is_in()
            log(f"in_town: {in_town}, npcs: {npcs}", self.window_id)

        if not npcs:
            return False, None, None

        if 'buyer' not in npcs or npcs['buyer'] == "no_data":
            log("скуп не найден", self.window_id)
            return False, in_town, npcs

        xy, rgb = parseCBT(npcs['buyer'], profile=self.profile)
        if xy is None:
            return False, in_town, npcs

        log(f"клик по скупу {xy}", self.window_id)
        await self.mouse.click(self.window_info, *xy)

        buyer_buttons = ["npc_buyer_button_1", "npc_buyer_button_2", "npc_buyer_button_3"]
        for i, button in enumerate(buyer_buttons):
            xy_btn, rgb_btn = parseCBT(button, profile=self.profile)
            if xy_btn is None:
                log(f"корды {button} не нашел", self.window_id)
                if i == 0:
                    return False, in_town, npcs
                continue

            if i == 0:
                log(f"жду {button}...", self.window_id)
                for _ in range(200):
                    if await self.profile.check_pixel(xy_btn, rgb_btn, timeout=0.1):
                        await asyncio.sleep(0.45)
                        log(f"клик по {button} в {xy_btn}", self.window_id)
                        await self.mouse.click(self.window_info, *xy_btn)
                        break
                    await asyncio.sleep(0.05)
                else:
                    log(f"таймаут {button}", self.window_id)
                    return False, in_town, npcs
            else:
                if await self.profile.check_pixel(xy_btn, rgb_btn, timeout=1.5):
                    log(f"клац {button} в {xy_btn}", self.window_id)
                    await self.mouse.click(self.window_info, *xy_btn)
                else:
                    log(f"кнопка {button} не появилась", self.window_id)

        xy_quit, rgb_quit = parseCBT("npc_global_quit_button", profile=self.profile)
        if xy_quit and await self.profile.check_pixel(xy_quit, rgb_quit, timeout=4):
            log(f"клацнул выход {xy_quit}", self.window_id)
            await self.mouse.click(self.window_info, *xy_quit)
            await asyncio.sleep(0.25)
            log("завершил функу", self.window_id)
            return True, in_town, npcs

        log("не завершил функу", self.window_id)
        return False, in_town, npcs

    async def buy_loot(self, skip: bool = False, clr: bool = True) -> bool:
        if not skip:
            if await self.profile.energo.is_on():
                ok = await self.profile.energo.turn_off()
                if not ok:
                    await asyncio.sleep(1)
                    ok = await self.profile.energo.turn_off()
                if not ok:
                    return False
        else:
            await asyncio.sleep(0.1)

        xy, rgb = parseCBT("krest_after_respawn", profile=self.profile)
        if clr is False:
            rgb = "no"
        if not await self.profile.check_pixel(xy, rgb, timeout=1.5):
            return False

        await self.mouse.click(self.window_info, xy[0], xy[1])
        await asyncio.sleep(0.5)

        xy, rgb = parseCBT("respawn_icon_in_gui", profile=self.profile)
        if not await self.profile.check_pixel(xy, rgb, timeout=2):
            xy_select_all, rgb_select_all = parseCBT("respawn_select_all", profile=self.profile)
            if await self.profile.check_pixel(xy_select_all, rgb_select_all, timeout=1):
                await self.mouse.click(self.window_info, xy_select_all[0], xy_select_all[1])
                await asyncio.sleep(0.5)
                xy_delete_exp, rgb_delete_exp = parseCBT("delete_exp", profile=self.profile)
                if await self.profile.check_pixel(xy_delete_exp, rgb_delete_exp, timeout=2):
                    await self.mouse.click(self.window_info, xy_delete_exp[0], xy_delete_exp[1])
                    await asyncio.sleep(0.3)
                    xy_yes, rgb_yes = parseCBT("delete_all_yes", profile=self.profile)
                    if await self.profile.check_pixel(xy_yes, rgb_yes, timeout=2):
                        await self.mouse.click(self.window_info, xy_yes[0], xy_yes[1])
                        await asyncio.sleep(0.1)
                        xy_exit, _ = parseCBT("respawn_exit_gui_button", profile=self.profile)
                        await self.mouse.click(self.window_info, xy_exit[0], xy_exit[1])
                        await asyncio.sleep(0.2)
                        return False
                    return False
            return False

        async def do_buy():
            xy_monetka, rgb_monetka = parseCBT("monetka_respawn", profile=self.profile)
            for _ in range(3):
                if await self.profile.check_pixel(xy_monetka, rgb_monetka, timeout=1):
                    break
                await self.mouse.click(self.window_info, xy_monetka[0], xy_monetka[1])
                await asyncio.sleep(0.4)

            buyyed = 0
            for i in range(1, 5):
                key = f"respawn_monetka_exp_{i}"
                xy_k, rgb_k = parseCBT(key, profile=self.profile)
                if await self.profile.check_pixel(xy_k, rgb_k, timeout=0.5):
                    await self.mouse.click(self.window_info, xy_k[0], xy_k[1])
                    buyyed += 1
                    await asyncio.sleep(0.1)

            if buyyed == 4:
                await asyncio.sleep(0.5)
                xy_k, rgb_k = parseCBT("respawn_monetka_exp_1", profile=self.profile)
                if await self.profile.check_pixel(xy_k, rgb_k, timeout=1):
                    await self.mouse.click(self.window_info, xy_k[0], xy_k[1])
                    await asyncio.sleep(0.1)

            xy_b, rgb_b = parseCBT("respawn_buy_gui_button", profile=self.profile)
            if await self.profile.check_pixel(xy_b, rgb_b, timeout=2):
                await self.mouse.click(self.window_info, xy_b[0], xy_b[1])
                await asyncio.sleep(0.3)
            else:
                return False

            xy_a, rgb_a = parseCBT("respawn_accept_buy_gui_button", profile=self.profile)
            if await self.profile.check_pixel(xy_a, rgb_a, timeout=2):
                await self.mouse.click(self.window_info, xy_a[0], xy_a[1])
                await asyncio.sleep(0.4)
                return True

            return False

        await do_buy()
        xy_items, _ = parseCBT("respawn_items", profile=self.profile)
        if xy_items is None:
            return False
        await self.mouse.click(self.window_info, xy_items[0], xy_items[1])
        await asyncio.sleep(0.5)
        await do_buy()
        xy_exit, _ = parseCBT("respawn_exit_gui_button", profile=self.profile)
        if xy_exit is None:
            return False
        await self.mouse.click(self.window_info, xy_exit[0], xy_exit[1])
        await asyncio.sleep(0.3)
        await self.profile.energo.check_lvl_up()
        return True
