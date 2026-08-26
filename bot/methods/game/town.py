import asyncio
import json
import random
from typing import Dict, Optional

from bot.clogger import log
from bot.delays import (
    DELAY_CHECK_NPC_POSITIONS,
    THR_CHECK_NPC_POSITIONS,
)
from bot.cbt import CBT_JP_PARSED, CBT_RU_PARSED
from bot.methods.base import parseCBT
from bot.events.enums import Region
from bot.methods.game._base import GameAction


class Town(GameAction):

    async def _wait_pixel(self, tag, deadline=10.0, thr=None):
        xy, rgb = parseCBT(tag, profile=self.profile)
        if xy is None:
            return None
        kw = {"timeout": deadline}
        if thr is not None:
            kw["thr"] = thr
        return xy if await self.profile.check_pixel(xy, rgb, **kw) else None

    async def _wait_all(self, tags, deadline=10.0, thr=None):
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        while loop.time() - t0 < deadline:
            results = await asyncio.gather(*(
                self._wait_pixel(t, deadline=0.3, thr=thr) for t in tags
            ))
            if all(r is not None for r in results):
                return results[0]
            await asyncio.sleep(0.2)
        return None

    async def _smart_click(self, tag, next_tag, wait=10.0, verify=2.0, reclicks=1, pre=0.45, thr=None, anchors=()):
        xy = await self._wait_all([tag] + list(anchors), deadline=wait, thr=thr)
        if xy is None:
            return False, None
        for attempt in range(reclicks + 1):
            if attempt == 0 and pre > 0:
                await asyncio.sleep(pre)
            await self.mouse.click(self.window_info, *xy)
            if next_tag is None:
                return True, xy
            if await self._wait_pixel(next_tag, deadline=verify):
                return True, xy
            if attempt < reclicks:
                log(f"{tag}: клик не сработал, реклик {attempt+1}/{reclicks}", self.window_id)
        return False, xy

    async def is_floran(self, thr: int = 14, need: int = 4) -> bool:
        in_energo = await self.profile.energo.is_on()
        prefix = "floran_energo_" if in_energo else "floran_no_energo_"
        cbt = CBT_RU_PARSED if self.settings.REGION == Region.RU else CBT_JP_PARSED

        specs = []
        rects = []
        i = 1
        while True:
            tag = f"{prefix}{i}"
            if tag not in cbt:
                break
            xy, rgb = cbt[tag]
            if xy is None:
                break
            specs.append((xy, rgb))
            rects.append((xy[0], xy[1], 1, 1))
            i += 1

        if not specs:
            return False

        imgs = await self.profile.capture_multy(rects)

        matched = 0
        for (xy, rgb), img in zip(specs, imgs):
            r, g, b = int(img[0, 0, 0]), int(img[0, 0, 1]), int(img[0, 0, 2])
            if max(abs(r - rgb[0]), abs(g - rgb[1]), abs(b - rgb[2])) <= thr:
                matched += 1

        floran = matched >= need
        log(f"is_floran: {floran} ({matched}/{len(specs)})", self.window_id)
        return floran

    async def find_npcs(self, thr: int = THR_CHECK_NPC_POSITIONS,
                        retries: int = 2, floran: Optional[bool] = None) -> Optional[Dict[str, str]]:
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

        if floran is None:
            floran = await self.is_floran()
        if floran:
            up_times = 5
        elif self.settings.REGION == Region.RU:
            up_times = 7
        elif self.settings.REGION == Region.JP:
            up_times = 5
        else:
            return None

        await self.mouse.wheel(self.window_info, [(38, 104)], direction="up", times=up_times)
        await asyncio.sleep(0.05)
        return {"stash": "npc_list_3", "shop": "npc_list_1", "buyer": "npc_list_5"}

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

            result = await self.profile.check_pixel(xy, rgb, timeout=1, thr=30)
            is_ru = self.settings.REGION == Region.RU
            if result:
                log("Белый кубик найден", self.window_id)
                xy_btn, _ = parseCBT("npc_list_in_town", profile=self.profile)
                if xy_btn is None:
                    return False, None

                floran = await self.is_floran() if is_ru else False
                x, y = xy_btn
                click_result = await self.mouse.click(self.window_info, x, y)
                if click_result:
                    log("Открыл список нпс, получаю позиции", self.window_id)
                    await asyncio.sleep(0.03)
                    allNPC = await self.find_npcs(floran=floran)
                    if allNPC:
                        log("Нахожусь в городе, список нпс открыт", self.window_id)
                        return True, allNPC
            else:
                log("Белого кубика не было", self.window_id)
                if is_ru:
                    xy_btn, _ = parseCBT("npc_list_in_town", profile=self.profile)
                    if xy_btn is None:
                        return False, None
                    x, y = xy_btn
                    await self.mouse.click(self.window_info, x, y)
                    await asyncio.sleep(0.4)
                    floran = await self.is_floran()
                    await self.mouse.click(self.window_info, x, y)
                    await asyncio.sleep(0.4)
                    allNPC = await self.find_npcs(floran=floran)
                else:
                    allNPC = await self.find_npcs(floran=False)
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
        log("buy_in_shop: старт", self.window_id)
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

        ok, xy_b1 = await self._smart_click(
            "npc_shop_button_1", "npc_shop_button_2",
            wait=120.0, verify=3.0, thr=10,
            anchors=("npc_shop_anchor_1", "npc_shop_anchor_2", "npc_shop_anchor_3"),
        )
        if not ok:
            if xy_b1 is None:
                log("buy_in_shop: button_1 не появилась, меню не открылось", self.window_id)
            else:
                log("buy_in_shop: button_1 клацнул но button_2 не появилась", self.window_id)
            return False, in_town, npcs

        xy_b2 = await self._wait_pixel("npc_shop_button_2", deadline=1.0)
        if xy_b2 is not None:
            await asyncio.sleep(0.45)
            await self.mouse.click(self.window_info, *xy_b2)

            xy_na = await self._wait_pixel("npc_shop_button_no_adena", deadline=0.5)
            if xy_na is not None:
                log("buy_in_shop: всплыло no_adena окно", self.window_id)
                xy_ok = await self._wait_pixel("npc_shop_button_no_adena_confirm", deadline=1.0)
                if xy_ok is not None:
                    await self.mouse.click(self.window_info, *xy_ok)
                    await asyncio.sleep(0.25)
                xy_q = await self._wait_pixel("npc_global_quit_button", deadline=2.0)
                if xy_q is not None:
                    await self.mouse.click(self.window_info, *xy_q)
                log("buy_in_shop: OK (через no_adena)", self.window_id)
                return True, in_town, npcs

        xy_b3 = await self._wait_pixel("npc_shop_button_3", deadline=3.0)
        if xy_b3 is not None:
            await asyncio.sleep(0.45)
            await self.mouse.click(self.window_info, *xy_b3)
            await asyncio.sleep(0.3)
            await self.mouse.click(self.window_info, *xy_b3)

        xy_q = await self._wait_pixel("npc_global_quit_button", deadline=4.0)
        if xy_q is not None:
            await self.mouse.click(self.window_info, *xy_q)
            await asyncio.sleep(0.25)
            log("buy_in_shop: OK", self.window_id)
            return True, in_town, npcs

        log("buy_in_shop: quit не найден, меню видимо залипло", self.window_id)
        return False, in_town, npcs

    async def go_stash(self, in_town=None, npcs=None) -> tuple[bool, bool, dict]:
        log("go_stash: старт", self.window_id)
        self.runtime.update_stashing()

        if in_town is None or npcs is None:
            in_town, npcs = await self.is_in()

        if not npcs:
            return False, None, None

        if 'stash' not in npcs or npcs['stash'] == "no_data":
            return False, in_town, npcs

        xy, rgb = parseCBT(npcs['stash'], profile=self.profile)
        if xy is None:
            return False, in_town, npcs

        await self.mouse.click(self.window_info, *xy)

        xy_b1 = await self._wait_all(
            ("npc_stash_button_1", "npc_stash_anchor_1", "npc_stash_anchor_2", "npc_stash_anchor_3"),
            deadline=120.0, thr=15,
        )
        if xy_b1 is None:
            log("go_stash: якоря склада не совпали, меню не открылось", self.window_id)
            return False, in_town, npcs
        await asyncio.sleep(0.45)
        await self.mouse.click(self.window_info, *xy_b1)
        await asyncio.sleep(0.2)
        await self.mouse.click(self.window_info, *xy_b1)

        xy_b2 = await self._wait_pixel("npc_stash_button_2", deadline=3.0)
        if xy_b2 is not None:
            await self.mouse.click(self.window_info, *xy_b2)
            await asyncio.sleep(0.2)
            await self.mouse.click(self.window_info, *xy_b2)

        xy_q = await self._wait_pixel("npc_global_quit_button", deadline=4.0)
        if xy_q is not None:
            await self.mouse.click(self.window_info, *xy_q)
            await asyncio.sleep(0.25)
            log("go_stash: OK", self.window_id)
            return True, in_town, npcs

        log("go_stash: quit не найден, меню видимо залипло", self.window_id)
        return False, in_town, npcs

    async def sell_to_buyer(self, in_town=None, npcs=None) -> tuple[bool, bool, dict]:
        log("sell_buyer: старт", self.window_id)
        self.runtime.update_purc()

        if in_town is None or npcs is None:
            in_town, npcs = await self.is_in()

        if not npcs:
            return False, None, None

        if 'buyer' not in npcs or npcs['buyer'] == "no_data":
            return False, in_town, npcs

        xy, rgb = parseCBT(npcs['buyer'], profile=self.profile)
        if xy is None:
            return False, in_town, npcs

        await self.mouse.click(self.window_info, *xy)

        ok, xy_b1 = await self._smart_click(
            "npc_buyer_button_1", "npc_buyer_button_2",
            wait=120.0, verify=3.0, thr=10,
            anchors=("npc_buyer_anchor_1", "npc_buyer_anchor_2"),
        )
        if not ok:
            if xy_b1 is None:
                log("sell_buyer: button_1 не появилась, меню не открылось", self.window_id)
                return False, in_town, npcs
            log("sell_buyer: button_1 клацнул но button_2 не появилась (нечего продавать?)", self.window_id)
            xy_q = await self._wait_pixel("npc_global_quit_button", deadline=4.0)
            if xy_q is not None:
                await self.mouse.click(self.window_info, *xy_q)
                await asyncio.sleep(0.25)
            return True, in_town, npcs

        ok, xy_b2 = await self._smart_click("npc_buyer_button_2", "npc_buyer_button_3", wait=3.0, verify=3.0)
        if not ok and xy_b2 is not None:
            log("sell_buyer: button_2 клацнул но button_3 не появилась", self.window_id)

        xy_b3 = await self._wait_pixel("npc_buyer_button_3", deadline=2.0)
        if xy_b3 is not None:
            await asyncio.sleep(0.45)
            await self.mouse.click(self.window_info, *xy_b3)
            await asyncio.sleep(0.3)
            await self.mouse.click(self.window_info, *xy_b3)

        xy_q = await self._wait_pixel("npc_global_quit_button", deadline=4.0)
        if xy_q is not None:
            await self.mouse.click(self.window_info, *xy_q)
            await asyncio.sleep(0.25)
            log("sell_buyer: OK", self.window_id)
            return True, in_town, npcs

        log("sell_buyer: quit не найден, меню видимо залипло", self.window_id)
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
            xy_del, rgb_del = parseCBT("respawn_icon_in_gui_deleted", profile=self.profile)
            if xy_del and await self.profile.check_pixel(xy_del, rgb_del, timeout=1):
                for tab in ("respawn_exp", "respawn_items"):
                    xy_t, _ = parseCBT(tab, profile=self.profile)
                    if xy_t is not None:
                        await self.mouse.click(self.window_info, xy_t[0], xy_t[1])
                        await asyncio.sleep(0.25)

                    for btn in ("respawn_deleted_btn_1", "respawn_deleted_btn_2", "respawn_deleted_btn_3"):
                        xy_b, _ = parseCBT(btn, profile=self.profile)
                        if xy_b is not None:
                            await self.mouse.click(self.window_info, xy_b[0], xy_b[1])
                            await asyncio.sleep(0.25)

                xy_exit, _ = parseCBT("respawn_exit_gui_button", profile=self.profile)
                if xy_exit:
                    await self.mouse.click(self.window_info, xy_exit[0], xy_exit[1])
                    await asyncio.sleep(0.25)
                return False

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
