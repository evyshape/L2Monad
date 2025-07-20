import json
import math
from bot.methods.base import parseCBT
from clogger import log
import random
import asyncio
import time
import numpy as np
import mss
from constans import DAILY, BATTLE_PASS
from typing import Optional, Dict, Literal
from bot.delays import *


async def skip_vitlity(profile, mode: Literal["skip", "claim"] = "skip"):
    if mode == "skip":
        tag = "cancel_button_vitality"
    elif mode == "claim":
        tag = "cancel_button_vitality"  # TODO: заменить на серую кнопку, если появится
    else:
        return False

    async def wait_and_click(tag, timeout=5):
        xy, rgb = parseCBT(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    async def check_clr(tag):
        xy, rgb = parseCBT(tag)
        return await profile.check_pixel(xy, rgb, timeout=2)

    if await check_clr(tag):
        await wait_and_click(tag, timeout=5)
        await asyncio.sleep(1)
        return True

    await asyncio.sleep(1)
    return False

async def check_energo_mode(profile) -> bool:
    window_id = next(iter(profile.window_info))
    cbts = ["energomode_center_gui"]

    for cbt in cbts:
        xy, rgb = parseCBT(cbt)
        if not await profile.check_pixel(xy, rgb, timeout=DELAY_CHECK_ENERGO):
            log(f"Не находимся в энерго", window_id)
            return False

    log(f"Находимся в энергорежиме", window_id)
    return True

async def safe_tp(profile) -> bool:
    targets = [
        parseCBT("home_scroll_button_energomode"),
        parseCBT("home_scroll_button_no_energomode"),
    ]

    for xy, rgb in targets:
        if await profile.check_pixel(xy, rgb, timeout=2):
            await asyncio.sleep(2)
            return await profile.mouse.click(profile.window_info, *xy, fast=True)

    return False

async def energo_mode(profile, state: str) -> bool:
    window_id, window = next(iter(profile.window_info.items()))
    button_xy, button_rgb = parseCBT("energo_mode_gui")
    button_x, button_y = button_xy

    width = window["Width"]
    height = window["Height"]

    if state == "off":
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
        await profile.mouse.swipe(profile.window_info, swipe_points, delay_points=0.08)

        xy1, rgb1 = parseCBT("zalupka_gui")
        teleported = await profile.check_pixel(xy1, rgb1, timeout=10)
        if teleported:
            return True
        else:
            if await check_energo_mode(profile):
                repeat_points = [
                    (center_x, center_y),
                    (center_x - 75, center_y - 50),
                ]
                await profile.mouse.swipe(profile.window_info, repeat_points, delay_points=0.2)
                await asyncio.sleep(0.2)

            await asyncio.sleep(1)
            teleported = await profile.check_pixel(xy1, rgb1, timeout=3)
            if teleported:
                return True

        return False

    elif state == "on":
        await profile.mouse.click(profile.window_info, button_x, button_y)
        await asyncio.sleep(0.9)
        center_x = width // 2
        center_y = height // 2
        await profile.mouse.click(profile.window_info, center_x, center_y)
        return True

    return False

async def autohunt(profile) -> bool:
    button_xy, button_rgb = parseCBT("auto_combat_mode_gui")
    button_x, button_y = button_xy
    click = await profile.mouse.click(profile.window_info, button_x, button_y)
    if click:
        return True
    else:
        return False

async def schedule(profile, state) -> bool:

    async def wait_and_click(tag, timeout=5, thr=3):
        xy, rgb = parseCBT(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False
    tag = ""
    window_id = next(iter(profile.window_info))
    if state == "on":
        log("Пробую запустить расписание", window_id)
        tag = "schedule_start"
    if state == "off":
        log("Пробую остановить расписан", window_id)
        tag = "schedule_stop"

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")

    if not await wait_and_click("main_menu_gui", timeout=7):
        #log(f"Не удалось открыть главное меню", window_id)
        return False

    if not await wait_and_click("schedule_menu", timeout=5):
        return False

    await asyncio.sleep(1)
    if not await wait_and_click(tag, timeout=5):
        log("Окно сломалось?", window_id)
        return False

    if state == "off":
        if await wait_and_click("main_menu_gui", timeout=7):
            await asyncio.sleep(2)
            await energo_mode(profile, "on")
            return True

    await asyncio.sleep(2)
    tp = await wait_teleport(profile)
    if tp:
        await energo_mode(profile, "on")
        return True

    return False

async def wait_teleport(profile) -> bool:
    xy1, rgb1 = parseCBT("zalupka_gui")
    window_id = next(iter(profile.window_info))
    success = 0
    await asyncio.sleep(1)

    for _ in range(8):
        await asyncio.sleep(0.25)
        teleported = await profile.check_pixel(xy1, rgb1, timeout=DELAY_TELEPORT_TO_HOME)
        if teleported:
            success += 1

    if success >= 7:
        log("tped succ", window_id)
        return True
    else:
        log("tped failed", window_id)
        return False

async def check_autohunt(profile) -> bool:
    xy1, rgb1 = parseCBT("auto_combat_ON")
    window_id = next(iter(profile.window_info))
    success = 0
    await asyncio.sleep(2)

    for _ in range(5):
        await asyncio.sleep(0.2)
        teleported = await profile.check_pixel(xy1, rgb1, timeout=DELAY_AUTOHUNT_CHECK)
        if teleported:
            success += 1

    if success >= 3:
        log("hunt succ", window_id)
        return True
    else:
        log("no hunt", window_id)
        return False

async def teleport_to_random_spot(profile, from_: int = 1, to_: int = 4) -> bool:
    await asyncio.sleep(0.2)
    window_id = next(iter(profile.window_info))
    spot = random.randint(from_, to_)

    log(f"Пробую тпнуться на спот №{spot}", window_id)

    if await check_energo_mode(profile):
        log(f"Был в энерго, вырубаю перед тп", window_id)
        await energo_mode(profile, "off")

    await asyncio.sleep(0.2)

    steps = [
        "spot_teleport_call_button",
        f"spot_choice_{spot}",
        f"spot_acept_choice_{spot}"
    ]

    for key in steps:
        xy, rgb = parseCBT(key)

        if not await profile.check_pixel(xy, rgb, timeout=3):
            log(f"Не нашел {key} за 3 сек", window_id)
            return False

        x, y = xy
        if not await profile.mouse.click(profile.window_info, x, y):
            log(f"Не удалось нажать на {key} ({x}, {y})", window_id)
            return False

        await asyncio.sleep(0.1)

    tped = await wait_teleport(profile)

    if not tped:
        log("Телепорт не подтвержден — недостаточно срабатываний залупки", window_id)
        return False

    log("Залупка найдена, включаю автобой и энерго", window_id)

    hunt = await autohunt(profile)
    if hunt:
        log("Автобой включен", window_id)
        await asyncio.sleep(0.15)
        await energo_mode(profile, "on")
        await asyncio.sleep(0.05)
        return True

    return False

async def respawn(profile):
    emode = await check_energo_mode(profile)
    if emode:
        await energo_mode(profile, "off")

    death_found, btn = await check_rip(profile)
    if death_found and btn != "":
        xy1, rgb1 = parseCBT(btn)
        await profile.mouse.click(profile.window_info, xy1[0], xy1[1], fast=True)
        tped = await wait_teleport(profile)
        if tped:
            if emode:
                await energo_mode(profile, "on")
                await asyncio.sleep(1)
        return True
    return False

async def check_rip(profile) -> bool:
    window_id = next(iter(profile.window_info))
    cbts = ["you_were_killed_energomode", "check_death_penalty", "respawn_village"]

    #log("Начал чекать смерть", window_id)

    async def check(cbt: str) -> bool:
        #log(f"Чекаю {cbt}", window_id)
        xy, rgb = parseCBT(cbt)
        return await profile.check_pixel(xy, rgb, timeout=0.1)

    results = await asyncio.gather(*(check(cbt) for cbt in cbts))
    for cbt, found in zip(cbts, results):
        if found:
            #log(f"Детектнул {cbt}", window_id)
            return True, cbt

    return False, ""


async def get_npc_positions(profile) -> Optional[Dict[str, str]]:
    """
    profile — это объект ес че, вызывайте напрямую из обьекта бота
    """
    npc_mapping = {}
    window_id = next(iter(profile.window_info))
    log(f"Пробую получить позиции нпс", window_id)

    for j in [2, 3, 4, 5]:
        xy, rgb = parseCBT(f"npc_list_{j}")
        #log(f"Пробую чекнуть npc_list_{j}", window_id)

        result = await profile.check_pixel(xy, rgb, timeout=DELAY_CHECK_NPC_POSITIONS, thr=3, wsize="1x1")

        if result:
            log(f"Детектнул позиции, {j}", window_id)
            if j == 2:
                npc_mapping = {
                    "stash": f"npc_list_{j}",
                    "shop": "npc_list_1",
                    "buyer": "npc_list_4"
                }
            elif j == 3:
                npc_mapping = {
                    "stash": f"npc_list_{j}",
                    "shop": "npc_list_1",
                    "buyer": "npc_list_5"
                }
            elif j == 4:
                npc_mapping = {
                    "stash": f"npc_list_{j}",
                    "shop": "npc_list_2",
                    "buyer": "npc_list_6"
                }
            elif j == 5:
                npc_mapping = {
                    "stash": f"npc_list_{j}",
                    "shop": "npc_list_3",
                    "buyer": "no_data"
                }
            break
        else:
            log(f"no {j}", window_id)

    if npc_mapping:
        log(f"NPC mapping: {json.dumps(npc_mapping, indent=4)}", window_id)
        return npc_mapping
    else:
        log(f"get_npc_positions false, не обнаружил npc", window_id)
        return None

async def check_town(profile) -> tuple[bool, dict | None]:
    window_id = next(iter(profile.window_info))
    timeout = 20
    start_time = asyncio.get_event_loop().time()
    log(f"Начал проверять в городе ли я, таймаут: {timeout}", window_id)

    while asyncio.get_event_loop().time() - start_time < timeout:
        xy, rgb = parseCBT("white_cube_in_minimap")
        log(f"Чекаю белый кубик на мапе", window_id)
        if xy is None or rgb is None:
            return False, None

        result = await profile.check_pixel(xy, rgb, timeout=1)
        if result:
            log(f"Белый кубик найден, открываю список нпс", window_id)
            xy, rgb = parseCBT("npc_list_in_town")
            if xy is None:
                return False, None

            x, y = xy
            click_result = await profile.mouse.click(profile.window_info, x, y)
            if click_result:
                log(f"Открыл список нпс, получаю позиции", window_id)
                await asyncio.sleep(0.03)
                allNPC = await get_npc_positions(profile)
                if allNPC:
                    log("Нахожусь в городе, список нпс открыт", window_id)
                    return True, allNPC
        else:
            log(f"Белого кубика не было, чекаю позиции в тупую", window_id)
            allNPC = await get_npc_positions(profile)
            if allNPC:
                log("Список нпс уже открыт, мы в городе", window_id)
                return True, allNPC

            rip = await check_rip(profile)
            if rip:
                log("Умер прямо в момент тпшки в город, ресаюсь", window_id)
                res = await respawn(profile)
                if res:
                    log("Встал, верну False", window_id)
                    return False, None

            log("Все условия не пройдены, жесть", window_id)

        await asyncio.sleep(0.5)

    log("Не удалось определить, в городе ли мы =( (ТАЙМАУТ ТИПО ИСТЕК)", window_id)
    return False, None


async def buy_in_shop(profile) -> bool:
    window_id = next(iter(profile.window_info))
    log(f"Запускаю закупку у бакалейщика", window_id)
    in_town, npcs = await check_town(profile)

    if 'shop' not in npcs:
        return False

    shop_npc_key = npcs['shop']
    if shop_npc_key == "no_data":
        return False

    xy, rgb = parseCBT(shop_npc_key)
    if xy is None:
        return False

    x, y = xy
    await profile.mouse.click(profile.window_info, x, y)

    shop_button_name = "npc_shop_button_1"
    xy_btn, rgb_btn = parseCBT(shop_button_name)
    if xy_btn is None:
        return False

    attempts = 0
    while not await profile.check_pixel(xy_btn, rgb_btn, timeout=1, thr=7):
        await asyncio.sleep(0.05)
        attempts += 1
        if attempts >= 200:
            return False

    await asyncio.sleep(1.2)
    shop_buttons = ["npc_shop_button_1", "npc_shop_button_2", "npc_shop_button_3"]
    for button_name in shop_buttons:
        xy_btn, rgb_btn = parseCBT(button_name)
        if xy_btn is None:
            return False

        pixel_found = await profile.check_pixel(xy_btn, rgb_btn, timeout=3)
        if pixel_found:
            x, y = xy_btn
            await asyncio.sleep(0.1)
            await profile.mouse.click(profile.window_info, x, y)
        else:
            if button_name in ["npc_shop_button_2", "npc_shop_button_3"]:
                continue
            else:
                return False

    quit_button = "npc_global_quit_button"
    xy_quit, rgb_quit = parseCBT(quit_button)
    if xy_quit is None:
        return False

    pixel_found = await profile.check_pixel(xy_quit, rgb_quit, timeout=3)
    if pixel_found:
        x, y = xy_quit
        await profile.mouse.click(profile.window_info, x, y)
    else:
        return False

    return True

async def go_stash(profile) -> bool:
    window_id = next(iter(profile.window_info))
    log(f"Открываю склад", window_id)
    in_town, npcs = await check_town(profile)

    if 'stash' not in npcs or npcs['stash'] == "no_data":
        return False

    xy, rgb = parseCBT(npcs['stash'])
    if xy is None:
        return False

    await profile.mouse.click(profile.window_info, *xy)

    stash_ui_xy, stash_ui_rgb = parseCBT("npc_stash_button_1")
    if stash_ui_xy is None:
        return False

    for _ in range(200):
        if await profile.check_pixel(stash_ui_xy, stash_ui_rgb, timeout=1, thr=7):
            break
        await asyncio.sleep(0.05)
    else:
        return False

    await asyncio.sleep(1.2)
    for button in ["npc_stash_button_1", "npc_stash_button_2"]:
        xy_btn, rgb_btn = parseCBT(button)
        if xy_btn and await profile.check_pixel(xy_btn, rgb_btn, timeout=3):
            await asyncio.sleep(0.1)
            await profile.mouse.click(profile.window_info, *xy_btn)
        elif button == "npc_stash_button_1":
            return False

    xy_quit, rgb_quit = parseCBT("npc_global_quit_button")
    if xy_quit and await profile.check_pixel(xy_quit, rgb_quit, timeout=3):
        await profile.mouse.click(profile.window_info, *xy_quit)
        return True

    return False

async def sell_buyer(profile) -> bool:
    window_id = next(iter(profile.window_info))
    log(f"Продаю хлам скупщику", window_id)
    in_town, npcs = await check_town(profile)

    if 'buyer' not in npcs or npcs['buyer'] == "no_data":
        return False

    xy, rgb = parseCBT(npcs['buyer'])
    if xy is None:
        return False

    await profile.mouse.click(profile.window_info, *xy)

    buyer_ui_xy, buyer_ui_rgb = parseCBT("npc_buyer_button_1")
    if buyer_ui_xy is None:
        return False

    for _ in range(200):
        if await profile.check_pixel(buyer_ui_xy, buyer_ui_rgb, timeout=1, thr=7):
            break
        await asyncio.sleep(0.05)
    else:
        return False

    await asyncio.sleep(1.2)
    for button in ["npc_buyer_button_1", "npc_buyer_button_2", "npc_buyer_button_3"]:
        xy_btn, rgb_btn = parseCBT(button)
        if xy_btn and await profile.check_pixel(xy_btn, rgb_btn, timeout=3):
            await asyncio.sleep(0.1)
            await profile.mouse.click(profile.window_info, *xy_btn)
        elif button not in ["npc_buyer_button_2", "npc_buyer_button_3"]:
            return False

    xy_quit, rgb_quit = parseCBT("npc_global_quit_button")
    if xy_quit and await profile.check_pixel(xy_quit, rgb_quit, timeout=3):
        await profile.mouse.click(profile.window_info, *xy_quit)
        return True

    return False

async def buy_loot(profile) -> bool:
    window_info = profile.window_info

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")

    xy, rgb = parseCBT("krest_after_respawn")
    if not await profile.check_pixel(xy, rgb, timeout=3):
        return False

    await profile.mouse.click(window_info, xy[0], xy[1])
    await asyncio.sleep(0.5)

    xy, rgb = parseCBT("respawn_icon_in_gui")
    if not await profile.check_pixel(xy, rgb, timeout=3):
        xy_select_all, rgb_select_all = parseCBT("respawn_select_all")
        if await profile.check_pixel(xy_select_all, rgb_select_all, timeout=1):
            await profile.mouse.click(window_info, xy_select_all[0], xy_select_all[1])
            await asyncio.sleep(0.5)
            xy_delete_exp, rgb_delete_exp = parseCBT("delete_exp")
            if await profile.check_pixel(xy_delete_exp, rgb_delete_exp, timeout=2):
                await profile.mouse.click(window_info, xy_delete_exp[0],
                                          xy_delete_exp[1])
                await asyncio.sleep(0.3)
                xy_yes, rgb_yes = parseCBT("delete_all_yes")
                if await profile.check_pixel(xy_yes, rgb_yes, timeout=2):
                    await profile.mouse.click(window_info, xy_yes[0], xy_yes[1])
                    await asyncio.sleep(0.2)
                    xy, _ = parseCBT("respawn_exit_gui_button")
                    await profile.mouse.click(window_info, xy[0], xy[1])
                    await asyncio.sleep(0.3)
                    return False
                return False
        return False

    async def do_buy():
        xy_monetka, rgb_monetka = parseCBT("monetka_respawn")
        for _ in range(3):
            if await profile.check_pixel(xy_monetka, rgb_monetka, timeout=1):
                break
            await profile.mouse.click(window_info, xy_monetka[0], xy_monetka[1])
            await asyncio.sleep(0.4)

        buyyed = 0
        for i in range(1, 5):
            key = f"respawn_monetka_exp_{i}"
            xy, rgb = parseCBT(key)
            if await profile.check_pixel(xy, rgb, timeout=1):
                await profile.mouse.click(window_info, xy[0], xy[1])
                buyyed += 1
                await asyncio.sleep(0.2)

        if buyyed == 4:
            await asyncio.sleep(1)
            xy, rgb = parseCBT("respawn_monetka_exp_1")
            if await profile.check_pixel(xy, rgb, timeout=1):
                await profile.mouse.click(window_info, xy[0], xy[1])
                await asyncio.sleep(0.2)

        xy, rgb = parseCBT("respawn_buy_gui_button")
        if await profile.check_pixel(xy, rgb, timeout=2):
            await profile.mouse.click(window_info, xy[0], xy[1])
            await asyncio.sleep(0.4)
        else:
            return False

        xy, rgb = parseCBT("respawn_accept_buy_gui_button")
        if await profile.check_pixel(xy, rgb, timeout=2):
            await profile.mouse.click(window_info, xy[0], xy[1])
            await asyncio.sleep(0.4)
            return True

        return False

    await do_buy()
    xy, _ = parseCBT("respawn_items")
    await profile.mouse.click(window_info, xy[0], xy[1])
    await asyncio.sleep(0.5)
    await do_buy()
    xy, _ = parseCBT("respawn_exit_gui_button")
    await profile.mouse.click(window_info, xy[0], xy[1])
    await asyncio.sleep(0.3)

    return True


async def claim_mail(profile) -> bool:
    claimed = False
    window_id = next(iter(profile.window_info))

    async def wait_and_click(tag, timeout=5, thr=3):
        xy, rgb = parseCBT(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    async def check_clr(tag):
        xy, rgb = parseCBT(tag)
        return await profile.check_pixel(xy, rgb, timeout=2)

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")

    if not await wait_and_click("main_menu_gui", timeout=7):
        #log(f"Не удалось открыть главное меню", window_id)
        return False

    if not await wait_and_click("red_dot_mail_menu", timeout=1, thr=10):
        log(f"Не найден значок почты", window_id)
        return False

    red_dot_ex = await check_clr("red_dot_mail")
    claim_ex = await check_clr("claim_all_mail")

    if red_dot_ex and claim_ex:
        if not await wait_and_click("claim_all_mail", timeout=1):
            await wait_and_click("npc_global_quit_button", timeout=1)
            log(f"Не удалось нажать Claim All", window_id)
            return False

        start_time = time.time()
        while time.time() - start_time < 120:
            await asyncio.sleep(1)

            red_dot_ex = await check_clr("red_dot_mail")
            cancel_ex = await check_clr("cancel_button_vitality")

            if cancel_ex:
                await wait_and_click("cancel_button_vitality", timeout=1)
                await wait_and_click("npc_global_quit_button", timeout=1)
                log(f"Лимит опыта, ливнул", window_id)
                claimed = False
                break

            if not red_dot_ex:
                claimed = True
                await wait_and_click("npc_global_quit_button", timeout=2)
                log(f"Почта собрана", window_id)
                break

        await asyncio.sleep(0.5)
        return claimed
    else:
        await wait_and_click("npc_global_quit_button", timeout=1)
        log(f"Нет писем для сбора", window_id)
        return False

async def claim_daily(profile) -> bool:
    window_info = profile.window_info
    window_id, window = next(iter(window_info.items()))
    left, top = window["Position"]
    width = window["Width"]
    height = window["Height"]

    async def wait_and_click(tag, timeout=5, thr=3):
        xy, rgb = parseCBT(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr):
            x, y = xy
            await profile.mouse.click(window_info, x, y)
            return True
        return False

    async def kuchkovator(points, radius=12):
        if not points:
            return []

        grouped = []
        points = sorted(points, key=lambda c: (c[1], c[0]))
        group = [points[0]]

        for pt in points[1:]:
            if any((pt[0] - g[0])**2 + (pt[1] - g[1])**2 <= radius**2 for g in group):
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

    async def find_daily_tabs():
        x_search = DAILY["y_vkladki"]
        red_rgb = tuple(map(int, DAILY["red_dot_clr"][0].split(', ')))

        hits = []
        with mss.mss() as sct:
            monitor = {"left": left + x_search, "top": top, "width": 1, "height": height}
            screenshot = np.array(sct.grab(monitor))
            for y in range(0, height, 1):
                pixel_bgr = screenshot[y, 0][:3]
                pixel_rgb = pixel_bgr[::-1]
                if all(abs(int(pixel_rgb[i]) - red_rgb[i]) <= 16 for i in range(3)):
                    hits.append(y)

        buttons = []
        if hits:
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

    async def find_daily():
        almaz_rgb = tuple(map(int, DAILY["almaz_donate"][0].split(', ')))
        monetka_rgb = tuple(map(int, DAILY["monetka_donate"][0].split(', ')))
        claim_rgb = tuple(map(int, DAILY["claim_daily"][0].split(', ')))

        def colorfinder(target_rgb, thre):
            hits = []
            with mss.mss() as sct:
                monitor = {"left": left, "top": top, "width": width, "height": height}
                screenshot = np.array(sct.grab(monitor))
            img_rgb = screenshot[:, :, :3][:, :, ::-1]

            for y_start, y_end in [
                (DAILY["start_button_1"], DAILY["end_button_1"]),
                (DAILY["start_button_2"], DAILY["end_button_2"]),
            ]:
                for y in range(y_start, y_end + 1):
                    for x in range(width):
                        pixel = img_rgb[y, x]
                        if all(abs(int(pixel[i]) - target_rgb[i]) <= thre for i in range(3)):
                            hits.append((x, y))

            hits.sort(key=lambda c: (c[1], c[0]))
            return hits, screenshot

        while True:
            await asyncio.sleep(3)
            almaz_positions, screenshot = colorfinder(almaz_rgb, 1)
            if len(almaz_positions) == 2:
                return []

            monetka_positions, _ = colorfinder(monetka_rgb, 2)
            if not monetka_positions:
                claim_positions, _ = colorfinder(claim_rgb, 10)
                if claim_positions:
                    grouped_claims = await kuchkovator(claim_positions)
                    for (x_c, y_c) in grouped_claims:
                        await profile.mouse.click(window_info, x_c, y_c)
                        await asyncio.sleep(0.5)
                        await skip_vitlity(profile)
                    return ["claimed"]
                return []

            for (x_m, y_m) in monetka_positions:
                await profile.mouse.click(window_info, x_m, y_m)
                if not await wait_and_click("monetka_proverka"):
                    continue
                if not await wait_and_click("confirm_buy_daily"):
                    continue

                timeout = 5
                start_time = time.time()
                claimed = False
                while time.time() - start_time < timeout:
                    _, screenshot = colorfinder(almaz_rgb, 2)
                    img_rgb = screenshot[:, :, :3][:, :, ::-1]

                    if 0 <= y_m < height and 0 <= x_m < width:
                        pixel = img_rgb[y_m, x_m]
                        if all(abs(int(pixel[i]) - claim_rgb[i]) <= 2 for i in range(3)):
                            await profile.mouse.click(window_info, x_m, y_m)
                            claimed = True
                            break
                    await asyncio.sleep(0.1)

                if claimed:
                    break
            return []

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")

    await wait_and_click("main_menu_gui", timeout=1)

    if not await wait_and_click("red_dot_daily_rewards", timeout=2):
        return False

    await asyncio.sleep(1)

    tabs = await find_daily_tabs()
    summary = 0

    if tabs:
        for tab in tabs:
            await asyncio.sleep(1)
            if len(tab) >= 2:
                x, y = map(int, tab[0].split(", "))
                await profile.mouse.click(window_info, x, y)
                result = await find_daily()
                if result:
                    summary += 1

        if await wait_and_click("npc_global_quit_button", timeout=2):
            return summary > 0
    else:
        await wait_and_click("npc_global_quit_button", timeout=1)

    return False

async def claim_achiv(profile) -> bool:
    claimed = False
    window_id = next(iter(profile.window_info))

    async def wait_and_click(tag, timeout=5):
        xy, rgb = parseCBT(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")

    if not await wait_and_click("red_dot_achiv", timeout=5):
        log("Нет красной точки на иконке достижений", window_id)
        return False

    if not await wait_and_click("red_dot_achiv2", timeout=3):
        log("Не удалось нажать на вторую точку достижений", window_id)
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    while True:
        found_claim = await wait_and_click("achiv_claim_1", timeout=1)
        await asyncio.sleep(0.2)
        found_accept = await wait_and_click("achiv_claim_accept", timeout=1)

        if not found_claim:
            claimed = True
            await wait_and_click("npc_global_quit_button", timeout=5)
            break

    return claimed

async def claim_clan(profile) -> bool:
    window_id = next(iter(profile.window_info))

    async def wait_and_click(tag, timeout=5):
        xy, rgb = parseCBT(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")
        await asyncio.sleep(1)

    if not await wait_and_click("main_menu_gui", timeout=5):
        log("Не удалось открыть главное меню", window_id)
        return False

    if not await wait_and_click("red_dot_clan", timeout=2):
        log("Нет красной точки клана", window_id)
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    if not await wait_and_click("clan_1", timeout=3):
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    if not await wait_and_click("clan_2", timeout=3):
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    while True:
        found_clan_3 = await wait_and_click("clan_3", timeout=2)
        found_clan_4 = await wait_and_click("clan_4", timeout=2)

        if found_clan_3:
            if found_clan_4:
                await asyncio.sleep(0.5)
                await wait_and_click("clan_4", timeout=1)
            continue
        else:
            break

    if await wait_and_click("clan_5", timeout=2):
        if await wait_and_click("clan_6", timeout=2):
            await asyncio.sleep(0.1)
            await wait_and_click("npc_global_quit_button", timeout=2)
            await asyncio.sleep(0.3)
            return True
        else:
            await wait_and_click("npc_global_quit_button", timeout=5)
            return False

    return False

async def claim_battle_pass(profile) -> bool:
    window_info = profile.window_info
    window_id = next(iter(window_info))

    async def wait_and_click(tag, timeout=5):
        xy, rgb = parseCBT(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout):
            x, y = xy
            await profile.mouse.click(window_info, x, y)
            return True
        return False

    async def find_BP_1(t=5, step=5, distance=30):
        await asyncio.sleep(0.5)
        window_id, window = next(iter(window_info.items()))
        left, top = window["Position"]
        width = window["Width"]
        y_search = BATTLE_PASS["y_vkladki"]
        red_rgb = tuple(map(int, BATTLE_PASS["red_dot_clr_vkladka"][0].split(', ')))

        hits = []
        with mss.mss() as sct:
            monitor = {"left": left, "top": top + y_search, "width": width, "height": 1}
            screenshot = np.array(sct.grab(monitor))[:, :, :3][:, :, ::-1]
            for x in range(0, width, step):
                pixel_rgb = screenshot[0, x]
                if all(abs(int(pixel_rgb[i]) - red_rgb[i]) <= t for i in range(3)):
                    hits.append(x)

        buttons = []
        if hits:
            group = [hits[0]]
            for x in hits[1:]:
                if x - group[-1] <= distance:
                    group.append(x)
                else:
                    buttons.append(int(sum(group) / len(group)))
                    group = [x]
            buttons.append(int(sum(group) / len(group)))
        return [[f"{x}, {y_search}", "no"] for x in buttons]

    async def find_BP_2(t=8, step=3, distance=20):
        window_id, window = next(iter(window_info.items()))
        left, top = window["Position"]
        height = window["Height"]
        x_search = BATTLE_PASS["x_podvkladki"]
        red_rgb = tuple(map(int, BATTLE_PASS["red_dot_clr_podvkladka"][0].split(', ')))

        hits = []
        with mss.mss() as sct:
            monitor = {"left": left + x_search, "top": top, "width": 1, "height": height}
            screenshot = np.array(sct.grab(monitor))[:, :, :3][:, :, ::-1]
            for y in range(0, height, step):
                pixel_rgb = screenshot[y, 0]
                if all(abs(int(pixel_rgb[i]) - red_rgb[i]) <= t for i in range(3)):
                    hits.append(y)

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

    xy_sbor1, rgb_sbor1 = parseCBT("battle_pass_sbor_1")
    xy_sbor2, rgb_sbor2 = parseCBT("battle_pass_sbor_2")
    xy_sbor22, rgb_sbor22 = parseCBT("battle_pass_sbor_2_2")
    xy_empty, _ = parseCBT("battle_pass_empty")

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")
        await asyncio.sleep(0.2)

    await asyncio.sleep(1)

    if not await wait_and_click("main_menu_gui", 5):
        return False

    if not await wait_and_click("battle_pass_red_dot_gui", 3):
        log("Батлпасса нет, собирать не будем", window_id)
        await wait_and_click("npc_global_quit_button", 5)
        return False

    log("Пробую чекнуть вкладочки бп", window_id)
    tabs = await find_BP_1()
    log(f"Обнаружил вкладок бп: {len(tabs)}, начинаю чекать...", window_id)

    for i, tab in enumerate(tabs, 1):
        x, y = map(int, tab[0].split(", "))
        await profile.mouse.click(window_info, x, y)
        await asyncio.sleep(1)

        podtabs = await find_BP_2()
        log(f"Подвкладок найдено: {len(podtabs)}", window_id)

        for q, podtab in enumerate(podtabs, 1):
            x, y = map(int, podtab[0].split(", "))
            await profile.mouse.click(window_info, x, y)

            while True:
                if await profile.check_pixel(xy_sbor1, rgb_sbor1, timeout=2):
                    log(f"Собираю награду [{i}.{q}]", window_id)
                    await profile.mouse.click(window_info, *xy_sbor1)
                    await asyncio.sleep(1)
                else:
                    log(f"Нет наград во вкладке {i}, под {q}", window_id)
                    break

        await asyncio.sleep(0.3)

        if await profile.check_pixel(xy_sbor2, rgb_sbor2, timeout=1):
            await profile.mouse.click(window_info, *xy_sbor2)
            await asyncio.sleep(1)
            await skip_vitlity(profile)
        elif await profile.check_pixel(xy_sbor22, rgb_sbor22, timeout=1):
            await profile.mouse.click(window_info, *xy_sbor22)
            await asyncio.sleep(1)
            await skip_vitlity(profile)
        else:
            log("Собирать нечего, проверяю следующую вкладку", window_id)

    log("Закрываю баттл пасс", window_id)
    await asyncio.sleep(1.5)
    await wait_and_click("npc_global_quit_button", 5)

    return bool(tabs)

async def claim_donate_shop(profile) -> bool:
    window_info = profile.window_info
    window_id = next(iter(window_info))
    tabs = profile.settings.get_pages()
    if not tabs:
        log("Вкладок на выкуп в настройках 0", window_id)
        return False

    async def wait_and_click(tag, timeout=5, thr=2, wsize="2x2"):
        xy, rgb = parseCBT(tag)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr, wsize=wsize):
            await profile.mouse.click(window_info, *xy)
            return True
        return False

    async def go_to_tab(tab_num):
        tag = f"magaz_str_{tab_num}"
        result = await wait_and_click(tag, timeout=5)
        await asyncio.sleep(1)
        return result

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")
        await asyncio.sleep(2)

    if not await wait_and_click("magaz_gui_open", timeout=5):
        return False

    await asyncio.sleep(2.5)

    xy_close, rgb_close = parseCBT("magaz_monetka_reklama")
    if await profile.check_pixel(xy_close, rgb_close, timeout=6, thr=1, wsize="1x1"):
        await asyncio.sleep(1.5)
        xy_close1, rgb_close1 = parseCBT("magaz_circle_close")
        await profile.mouse.click(window_info, *xy_close1)
        log("Вылезла обычная реклама, закрыл гадость", window_id)

    xy_google, rgb_google = parseCBT("magaz_google_trigger")
    if await profile.check_pixel(xy_google, rgb_google, timeout=4, thr=2, wsize="2x2"):
        await asyncio.sleep(0.2)
        if await wait_and_click("magaz_google_close", timeout=2):
            log("Вылез гугл, закрыл гадость", window_id)

    #if not await wait_and_click("red_dot_magaz", timeout=4):
        #await wait_and_click("npc_global_quit_button", timeout=5)
        #log("Кругляша нет, выходим из шопа", window_id)
        #return False

    await asyncio.sleep(1.2)
    await wait_and_click("3_vkladka", timeout=2)

    for tab in tabs:
        if not await go_to_tab(tab):
            continue

        await asyncio.sleep(1)

        if not await wait_and_click("purc_all_magaz", timeout=5):
            await wait_and_click("npc_global_quit_button", timeout=2)
            return False

        if not await wait_and_click("buy_all_magaz", timeout=2):
            await wait_and_click("close_buy_magaz", timeout=2)
            #await asyncio.sleep(1)
            #await wait_and_click("npc_global_quit_button", timeout=2)
            log("Чет пошло не так, skip!", window_id)
            continue

        xy_check, rgb_check = parseCBT("purc_all_magaz")
        if await profile.check_pixel(xy_check, rgb_check, timeout=10):
            await asyncio.sleep(0.2)
        else:
            log("Что-то пошло не так, не трогаю окно, зырь в него", window_id)
            return False

    if not await wait_and_click("close_magaz", timeout=5):
        await wait_and_click("npc_global_quit_button", timeout=2)
        return False

    await asyncio.sleep(0.2)
    return True