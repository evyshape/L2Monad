import asyncio
import time
from typing import Literal

import mss
import numpy as np

from bot.clogger import log
from bot.constans import BATTLE_PASS, DAILY
from bot.delays import (
    DELAY_WAIT_ADENA_SHOP_ADD,
    DELAY_WAIT_ADENA_SHOP_GOOGLE,
    SLEEP_AFTER_CLAIM_ACHIVMENTS,
)
from bot.methods.base import parseCBT
from bot.methods.game._base import GameAction


class Claims(GameAction):

    async def skip_vitality(self, mode: Literal["skip", "claim"] = "skip") -> bool:
        if mode == "skip":
            tag = "cancel_button_vitality"
        elif mode == "claim":
            tag = "yes_button_vitality"
        else:
            return False

        if await self.has(tag, timeout=2):
            await self.wait_and_click(tag, timeout=5)
            await asyncio.sleep(1)
            return True

        await asyncio.sleep(1)
        return False

    async def mail(self) -> bool:
        claimed = False

        if await self.profile.energo.is_on():
            await self.profile.energo.turn_off()
            await asyncio.sleep(3)

        if not await self.wait_and_click("main_menu_gui", timeout=7):
            log("Не удалось открыть главное меню", self.window_id)
            return False

        if not await self.wait_and_click("red_dot_mail_menu", timeout=1, thr=10):
            await self.wait_and_click("main_menu_gui", timeout=1)
            log("Не найден значок почты", self.window_id)
            return False
        log("Нашел почту", self.window_id)

        red_dot_ex = await self.has("red_dot_mail", timeout=2)
        claim_ex = await self.has("claim_all_mail", timeout=2)

        if red_dot_ex and claim_ex:
            if not await self.wait_and_click("claim_all_mail", timeout=1):
                await self.wait_and_click("npc_global_quit_button", timeout=1)
                log("Не удалось нажать Claim All (почта)", self.window_id)
                return False

            start_time = time.time()
            while time.time() - start_time < 50:
                await asyncio.sleep(2)

                red_dot_ex = await self.has("red_dot_mail", timeout=2)
                cancel_ex = await self.has("yes_button_vitality", timeout=2)

                if cancel_ex:
                    await self.wait_and_click("cancel_button_vitality", timeout=2)
                    await self.wait_and_click("npc_global_quit_button", timeout=1)
                    log("Лимит опыта, ливнул", self.window_id)
                    claimed = False
                    break

                if not red_dot_ex:
                    claimed = True
                    await self.wait_and_click("npc_global_quit_button", timeout=2)
                    log("Почта собрана", self.window_id)
                    break

            await asyncio.sleep(0.5)
            return claimed

        await self.wait_and_click("npc_global_quit_button", timeout=1)
        log("Нет писем для сбора", self.window_id)
        return False

    async def _find_daily_inside_tab(self, left, top, width, height) -> list:
        region = self.settings.REGION

        async def kuchkovator(points, radius=12):
            if not points:
                log("Нет точек для кучковки, мб вкладка говно", self.window_id)
                return []

            grouped = []
            points = sorted(points, key=lambda c: (c[1], c[0]))
            group = [points[0]]
            for pt in points[1:]:
                if any((pt[0] - g[0]) ** 2 + (pt[1] - g[1]) ** 2 <= radius ** 2 for g in group):
                    group.append(pt)
                else:
                    avg_x = int(sum(p[0] for p in group) / len(group))
                    avg_y = int(sum(p[1] for p in group) / len(group))
                    grouped.append((avg_x, avg_y))
                    group = [pt]

            avg_x = int(sum(p[0] for p in group) / len(group))
            avg_y = int(sum(p[1] for p in group) / len(group))
            grouped.append((avg_x, avg_y))
            return grouped

        def colorfinder(target_rgb, thre, s_ranges):
            with mss.mss() as sct:
                monitor = {"left": left, "top": top, "width": width, "height": height}
                screenshot = np.array(sct.grab(monitor))

            img_rgb = screenshot[:, :, :3][:, :, ::-1].astype(np.int16)
            target = np.array(target_rgb, dtype=np.int16)
            diff = np.abs(img_rgb - target)
            mask = np.all(diff <= thre, axis=-1)

            hits = []
            for y_start, y_end in s_ranges:
                band = mask[y_start:y_end + 1]
                ys, xs = np.where(band)
                for x, y_rel in zip(xs.tolist(), ys.tolist()):
                    hits.append((x, y_start + y_rel))

            hits.sort(key=lambda c: (c[1], c[0]))
            return hits

        almaz_rgb = tuple(map(int, DAILY[region]["almaz_donate"][0].split(',')))
        monetka_rgb = tuple(map(int, DAILY[region]["monetka_donate"][0].split(',')))
        donate_rgb = tuple(map(int, DAILY[region]["donate_monetka_supermonetka"][0].split(',')))
        claim_rgb = tuple(map(int, DAILY[region]["claim_daily"][0].split(',')))

        s_ranges = [
            (DAILY[region]["start_button_1"], DAILY[region]["end_button_1"]),
            (DAILY[region]["start_button_2"], DAILY[region]["end_button_2"]),
        ]

        while True:
            await asyncio.sleep(1)
            claim_positions = colorfinder(claim_rgb, 10, s_ranges)
            almaz_positions = colorfinder(almaz_rgb, 2, s_ranges)
            monetka_positions = colorfinder(monetka_rgb, 2, s_ranges)

            if len(almaz_positions) >= 2:
                log("На вкладке 2 или больше алмазов - пропускаем", self.window_id)
                return []

            blocked_colors = [almaz_rgb, donate_rgb]

            def blocked(y_start, y_end):
                for color in blocked_colors:
                    hits = colorfinder(color, 2, [(y_start, y_end)])
                    if hits:
                        return True
                return False

            if claim_positions:
                grouped_claims = await kuchkovator(claim_positions)
                for x_c, y_c in grouped_claims:
                    for y_start, y_end in s_ranges:
                        if y_start <= y_c <= y_end:
                            if blocked(y_start, y_end):
                                log(f"Пропускаем кнопку с алмазом/донатом: {(x_c, y_c)}", self.window_id)
                                break
                    else:
                        log(f"Собираю награду тут: {(x_c, y_c)}", self.window_id)
                        await self.mouse.click(self.window_info, x_c, y_c)
                        await asyncio.sleep(0.5)
                        await self.skip_vitality("claim")

                return ["claimed"]

            if len(almaz_positions) == 1:
                log("Скипаем 1 алмаз", self.window_id)
                return []

            return []

    async def daily(self) -> bool:
        region = self.settings.REGION
        window = self.window_info[self.window_id]
        left, top = window["Position"]
        width, height = window["Width"], window["Height"]

        async def find_daily_tabs(left, top, height):
            x_search = DAILY[region]["y_vkladki"]
            red_rgb = tuple(map(int, DAILY[region]["red_dot_clr"][0].split(', ')))
            log("Ищем вкладки", self.window_id)
            with mss.mss() as sct:
                monitor = {"left": left + x_search, "top": top, "width": 1, "height": height}
                screenshot = np.array(sct.grab(monitor))

            col = screenshot[:, 0, :3][:, ::-1].astype(np.int16)
            target = np.array(red_rgb, dtype=np.int16)
            diff = np.abs(col - target)
            mask = np.all(diff <= 16, axis=-1)
            hits = np.where(mask)[0].tolist()

            if not hits:
                log("Красной точки нет, скип", self.window_id)
                return []

            buttons = []
            group = [hits[0]]
            for y in hits[1:]:
                if y - group[-1] <= 12:
                    group.append(y)
                else:
                    avg = int(sum(group) / len(group))
                    buttons.append(avg)
                    group = [y]
            avg = int(sum(group) / len(group))
            buttons.append(avg)

            x_s = x_search - 14
            return [[f"{x_s}, {y}", "no"] for y in buttons]

        if await self.profile.energo.is_on():
            await self.profile.energo.turn_off()

        await self.wait_and_click("main_menu_gui", timeout=1)
        if not await self.wait_and_click("red_dot_daily_rewards", timeout=2):
            log("Не нашел красной точки, скипаю", self.window_id)
            await self.wait_and_click("main_menu_gui", timeout=1)
            return False

        await asyncio.sleep(3.5)
        tabs = await find_daily_tabs(left, top, height)
        summary = 0

        if tabs:
            for tab in tabs:
                await asyncio.sleep(1)
                if len(tab) >= 2:
                    x, y = map(int, tab[0].split(", "))
                    log(f"Перешел на вкладку: {(x, y)}", self.window_id)
                    await self.mouse.click(self.window_info, x, y)
                    result = await self._find_daily_inside_tab(left, top, width, height)
                    if result:
                        summary += 1
            await self.wait_and_click("npc_global_quit_button", timeout=2)
            log(f"Всего собрано: {summary}", self.window_id)
            return summary > 0

        await self.wait_and_click("npc_global_quit_button", timeout=1)
        log("Ничего не собрано", self.window_id)
        return False

    async def achievements(self) -> bool:
        claimed = False

        if await self.profile.energo.is_on():
            await self.profile.energo.turn_off()

        if not await self.wait_and_click("red_dot_achiv", timeout=5, thr=1):
            log("Нет красной точки на иконке достижений", self.window_id)
            return False
        log("Нашел сбор ачив", self.window_id)

        if not await self.wait_and_click("red_dot_achiv2", timeout=3, thr=1):
            log("Не удалось нажать на вторую точку достижений", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5, thr=1)
            return False

        await asyncio.sleep(2)
        while True:
            found_claim = await self.wait_and_click("achiv_claim_1", timeout=8, thr=3)
            await asyncio.sleep(SLEEP_AFTER_CLAIM_ACHIVMENTS)
            await self.wait_and_click("achiv_claim_accept", timeout=7, thr=1)

            if not found_claim:
                claimed = True
                await self.wait_and_click("achiv_claim_accept", timeout=2, thr=1)
                await self.wait_and_click("npc_global_quit_button", timeout=5, thr=1)
                break

            await asyncio.sleep(1.5)

        await asyncio.sleep(2)
        q = await self.wait_and_click("achiv_claim_accept", timeout=2, thr=1)
        if q:
            await self.wait_and_click("npc_global_quit_button", timeout=1, thr=1)

        return claimed

    async def clan(self) -> bool:
        if await self.profile.energo.is_on():
            await self.profile.energo.turn_off()
            await asyncio.sleep(1)

        if not await self.wait_and_click("main_menu_gui", timeout=5):
            log("Не удалось открыть главное меню", self.window_id)
            return False

        if not await self.wait_and_click("red_dot_clan", timeout=2):
            log("Нет красной точки клана", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False
        log("Нашел сбор клана", self.window_id)

        if not await self.wait_and_click("clan_1", timeout=3):
            log("Не нашел clan_1", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False

        if not await self.wait_and_click("clan_2", timeout=3):
            log("Не нашел clan_2", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False

        if not await self.wait_and_click("clan_3", timeout=3):
            log("Не нашел clan_3", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            await asyncio.sleep(0.5)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False
        await self.skip_vitality("claim")

        if not await self.wait_and_click("clan_5", timeout=3):
            log("Не нашел clan_5", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False

        if not await self.wait_and_click("clan_6", timeout=3):
            log("Не нашел clan_6", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False

        if not await self.wait_and_click("npc_global_quit_button", timeout=3):
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False

        await asyncio.sleep(0.3)
        return True

    async def alliance(self) -> bool:
        if self.settings.REGION != "RU":
            return False
        num = self.settings.ALLIANCE_BUTTON
        if num == 0:
            return False

        if await self.profile.energo.is_on():
            await self.profile.energo.turn_off()
            await asyncio.sleep(1)

        if not await self.wait_and_click("main_menu_gui", timeout=5):
            log("Не удалось открыть главное меню", self.window_id)
            return False

        await asyncio.sleep(1.5)
        if not await self.wait_and_click("alliance_menu_gui", timeout=3):
            log("Не нашел кнопку альянса в меню", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False
        log("Нашел сбор альянса, жму", self.window_id)

        if not await self.wait_and_click("alliance_donate_global_button", timeout=2):
            log("Не нашел кнопку доната", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False

        await asyncio.sleep(0.2)

        if not await self.wait_and_click(f"alliance_donate_{num}_button", timeout=3):
            log(f"Не нашел alliance_donate_{num}_button", self.window_id)
            await self.wait_and_click("alliance_close_donate", timeout=3)
            await asyncio.sleep(1.2)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False
        await self.skip_vitality("claim")

        if not await self.wait_and_click("npc_global_quit_button", timeout=3):
            return False
        await self.wait_and_click("npc_global_quit_button", timeout=5)

        await asyncio.sleep(0.2)
        return True

    async def battle_pass(self) -> bool:
        async def click_with_offset(tag, timeout=5):
            xy, rgb = parseCBT(tag, profile=self.profile)
            if await self.profile.check_pixel(xy, rgb, timeout=timeout):
                x, y = xy
                if tag == "battle_pass_red_dot_gui":
                    y += 7
                    x -= 5
                await self.mouse.click(self.window_info, x, y, fast=True)
                return True
            return False

        async def find_BP_1(t=25, step=5, distance=30):
            await asyncio.sleep(0.5)
            window = self.window_info[self.window_id]
            left, top = window["Position"]
            width = window["Width"]
            y_search = BATTLE_PASS["y_vkladki"]
            red_rgb = tuple(map(int, BATTLE_PASS["red_dot_clr_vkladka"][0].split(', ')))

            with mss.mss() as sct:
                monitor = {"left": left, "top": top + y_search, "width": width, "height": 1}
                log(f"{monitor}", self.window_id)
                screenshot = np.array(sct.grab(monitor))[:, :, :3][:, :, ::-1]

            row = screenshot[0, ::step, :].astype(np.int16)
            target = np.array(red_rgb, dtype=np.int16)
            diff = np.abs(row - target)
            mask = np.all(diff <= t, axis=-1)
            hits = (np.where(mask)[0] * step).tolist()
            log(f"{hits}", self.window_id)

            buttons = []
            if hits:
                group = [hits[0]]
                for x in hits[1:]:
                    if x - group[-1] <= distance:
                        group.append(x)
                    else:
                        avg = int(sum(group) / len(group))
                        buttons.append(avg)
                        group = [x]
                avg = int(sum(group) / len(group))
                buttons.append(avg)

            result = [[f"{x}, {y_search}", "no"] for x in buttons]
            log(f"final {result}", self.window_id)
            return result

        async def find_BP_2(t=8, step=3, distance=20):
            window = self.window_info[self.window_id]
            left, top = window["Position"]
            height = window["Height"]
            x_search = BATTLE_PASS["x_podvkladki"]
            red_rgb = tuple(map(int, BATTLE_PASS["red_dot_clr_podvkladka"][0].split(', ')))

            with mss.mss() as sct:
                monitor = {"left": left + x_search, "top": top, "width": 1, "height": height}
                screenshot = np.array(sct.grab(monitor))[:, :, :3][:, :, ::-1]

            col = screenshot[::step, 0, :].astype(np.int16)
            target = np.array(red_rgb, dtype=np.int16)
            diff = np.abs(col - target)
            mask = np.all(diff <= t, axis=-1)
            hits = (np.where(mask)[0] * step).tolist()

            buttons = []
            if hits:
                group = [hits[0]]
                for y in hits[1:]:
                    if y - group[-1] <= distance:
                        group.append(y)
                    else:
                        buttons.append(int(sum(group) / len(group)))
                        group = [y]
                buttons.append(int(sum(group) / len(group)))
            return [[f"{x_search}, {y}", "no"] for y in buttons]

        xy_sbor1, rgb_sbor1 = parseCBT("battle_pass_sbor_1", profile=self.profile)
        xy_sbor2, rgb_sbor2 = parseCBT("battle_pass_sbor_2", profile=self.profile)
        xy_sbor22, rgb_sbor22 = parseCBT("battle_pass_sbor_2_2", profile=self.profile)
        xy_empty, _ = parseCBT("battle_pass_empty", profile=self.profile)

        if await self.profile.energo.is_on():
            await self.profile.energo.turn_off()
            await asyncio.sleep(0.2)

        await asyncio.sleep(1)

        if not await self.wait_and_click("main_menu_gui", timeout=5):
            return False

        if not await click_with_offset("battle_pass_red_dot_gui", timeout=3):
            log("Батлпасса нет, собирать не будем", self.window_id)
            await self.wait_and_click("npc_global_quit_button", timeout=5)
            return False
        log("Нашел бп", self.window_id)

        await asyncio.sleep(1)
        log("Пробую чекнуть вкладочки бп", self.window_id)
        tabs = await find_BP_1()
        log(f"Обнаружил вкладок бп: {len(tabs)}, начинаю чекать...", self.window_id)

        for i, tab in enumerate(tabs, 1):
            x, y = map(int, tab[0].split(", "))
            await self.mouse.click(self.window_info, x, y)
            await asyncio.sleep(1)

            podtabs = await find_BP_2()
            log(f"Подвкладок найдено: {len(podtabs)}", self.window_id)

            for q, podtab in enumerate(podtabs, 1):
                x, y = map(int, podtab[0].split(", "))
                await self.mouse.click(self.window_info, x, y)

                while True:
                    if await self.profile.check_pixel(xy_sbor1, rgb_sbor1, timeout=2):
                        log(f"Собираю награду [{i}.{q}]", self.window_id)
                        await self.mouse.click(self.window_info, *xy_sbor1)
                        await asyncio.sleep(1)
                    else:
                        log(f"Нет наград во вкладке {i}, под {q}", self.window_id)
                        break

            await asyncio.sleep(0.3)

            if await self.profile.check_pixel(xy_sbor2, rgb_sbor2, timeout=1):
                await self.mouse.click(self.window_info, *xy_sbor2)
                await asyncio.sleep(1)
                await self.skip_vitality("claim")
            elif await self.profile.check_pixel(xy_sbor22, rgb_sbor22, timeout=1):
                await self.mouse.click(self.window_info, *xy_sbor22)
                await asyncio.sleep(1)
                await self.skip_vitality("claim")
            else:
                log("Собирать нечего, проверяю следующую вкладку", self.window_id)

        log("Закрываю баттл пасс", self.window_id)
        await asyncio.sleep(1.5)
        await self.wait_and_click("npc_global_quit_button", timeout=5)

        return bool(tabs)

    async def donate_shop(self) -> bool:
        tabs = self.settings.get_pages()
        if not tabs:
            log("Вкладок на выкуп в настройках 0", self.window_id)
            return False

        async def go_to_tab(tab_num):
            tag = f"magaz_str_{tab_num}"
            result = await self.wait_and_click(tag, timeout=5, thr=2)
            await asyncio.sleep(1)
            return result

        if await self.profile.energo.is_on():
            await self.profile.energo.turn_off()
            await asyncio.sleep(2)

        if not await self.wait_and_click("magaz_gui_open", timeout=5, thr=2):
            return False

        await asyncio.sleep(2.5)

        xy_close, rgb_close = parseCBT("magaz_monetka_reklama", profile=self.profile)
        if await self.profile.check_pixel(
            xy_close, rgb_close,
            timeout=DELAY_WAIT_ADENA_SHOP_ADD, thr=1, wsize="1x1",
        ):
            await asyncio.sleep(1.5)
            xy_close1, _ = parseCBT("magaz_circle_close", profile=self.profile)
            await self.mouse.click(self.window_info, *xy_close1)
            log("Вылезла обычная реклама, закрыл гадость", self.window_id)

        if self.settings.REGION != "RU":
            xy_google, rgb_google = parseCBT("magaz_google_trigger", profile=self.profile)
            if await self.profile.check_pixel(
                xy_google, rgb_google,
                timeout=DELAY_WAIT_ADENA_SHOP_GOOGLE, thr=2, wsize="2x2",
            ):
                await asyncio.sleep(0.2)
                if await self.wait_and_click("magaz_google_close", timeout=2, thr=2):
                    log("Вылез гугл, закрыл гадость", self.window_id)

        await asyncio.sleep(0.6)
        await self.wait_and_click("3_vkladka", timeout=2, thr=2)

        for tab in tabs:
            if not await go_to_tab(tab):
                continue

            await asyncio.sleep(1)

            if not await self.wait_and_click("purc_all_magaz", timeout=5, thr=2):
                await self.wait_and_click("npc_global_quit_button", timeout=2, thr=2)
                return False

            if not await self.wait_and_click("buy_all_magaz", timeout=2, thr=2):
                await self.wait_and_click("close_buy_magaz", timeout=2, thr=2)
                log("Чет пошло не так, skip!", self.window_id)
                continue

            xy_check, rgb_check = parseCBT("purc_all_magaz", profile=self.profile)
            if await self.profile.check_pixel(xy_check, rgb_check, timeout=10):
                await asyncio.sleep(0.2)
            else:
                log("Что-то пошло не так, не трогаю окно, зырь в него", self.window_id)
                return False

        if not await self.wait_and_click("close_magaz", timeout=5, thr=2):
            await self.wait_and_click("npc_global_quit_button", timeout=2, thr=2)
            return False

        await asyncio.sleep(0.2)
        return True
