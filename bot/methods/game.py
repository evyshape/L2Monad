import asyncio
import json
import math
import random
import time

from typing import Optional, Dict, Literal

import numpy as np
import mss

from bot.delays import *
from bot.methods.base import parseCBT
from bot.methods.other import screenshot_window
from bot.clogger import log
from bot.constans import DAILY, BATTLE_PASS

from tgbot.keyboards.screenshot import delete_screenshot_kb

async def skip_vitlity(profile, mode: Literal["skip", "claim"] = "skip"):
    if mode == "skip":
        tag = "cancel_button_vitality"
    elif mode == "claim":
        tag = "yes_button_vitality"
    else:
        return False

    async def wait_and_click(tag, timeout=DELAY_WAIT_EINHASAD):
        xy, rgb = parseCBT(tag, profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=timeout):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    async def check_clr(tag):
        xy, rgb = parseCBT(tag, profile=profile)
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
        xy, rgb = parseCBT(cbt, profile=profile)
        if not await profile.check_pixel(xy, rgb, timeout=DELAY_CHECK_ENERGO):
            log(f"Не находимся в энерго", window_id)
            return False

    log(f"Находимся в энергорежиме", window_id)
    return True

async def safe_tp(profile) -> bool:
    window_id = next(iter(profile.window_info))
    targets = [
        parseCBT("home_scroll_button_energomode", profile=profile),
        parseCBT("home_scroll_button_no_energomode", profile=profile),
    ]

    tasks = [
        asyncio.create_task(profile.check_pixel(xy, rgb, timeout=5, thr=8))
        for xy, rgb in targets
    ]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for task, (xy, _) in zip(tasks, targets):
        if task in done and task.result() is True:
            for p in pending:
                p.cancel()
            await asyncio.sleep(0.06)
            return await profile.mouse.click(profile.window_info, *xy, fast=True)

    for p in pending:
        p.cancel()

    log("Были либо в стане либо нет свитков, не тпнулся =(", window_id)
    if profile.settings.TELEGRAM_NOTIFIES:
        profile.tgbot.send_notification(
            level="error",
            text="Чет могло жестко сломаться, не смогли тп в город",
            nickname=window_id,
        )
    return False


async def check_lvl_up(profile) -> bool:
    window_id = next(iter(profile.window_info))
    xy, rgb = parseCBT("lvl_up_black", profile=profile)

    log("Чекаю лвл ап залупу", window_id)
    lvl_up_visible = await profile.check_pixel(xy, rgb, timeout=0.5)

    if lvl_up_visible:
        log("Лвл ап вылез, закрываю", window_id)
        xy_close, rgb_close = parseCBT("lvl_up_close", profile=profile)
        await profile.mouse.click(profile.window_info, *xy_close)
        if profile.settings.TELEGRAM_NOTIFIES:
            profile.tgbot.send_notification(
                level="info",
                text="Перс апнул лвл, будь во внимании и качни поинт!",
                nickname=window_id,
            )
        return True
    else:
        log(f"Вероятно лвл апа не было {lvl_up_visible}", window_id)
        return False

async def energo_mode(profile, state: str) -> bool:
    window_id, window = next(iter(profile.window_info.items()))
    button_xy, button_rgb = parseCBT("energo_mode_gui", profile=profile)
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

        xy1, rgb1 = parseCBT("zalupka_gui", profile=profile)
        await asyncio.sleep(SLEEP_AFTER_UNBLOCK)
        teleported = await profile.check_pixel(xy1, rgb1, timeout=10, thr=15 if profile.settings.REGION == "RU" else 2)
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

            await asyncio.sleep(SLEEP_AFTER_UNBLOCK)
            teleported = await profile.check_pixel(xy1, rgb1, timeout=3)
            if teleported:
                return True

        return False

    elif state == "on":
        await profile.mouse.click(profile.window_info, button_x, button_y)
        await asyncio.sleep(1.5)
        center_x = width // 2
        center_y = height // 2
        await profile.mouse.click(profile.window_info, center_x, center_y)
        return True

    return False

async def auction_rereg(profile) -> bool:
    window_id, window = next(iter(profile.window_info.items()))

    async def wait_and_click(tag, timeout=5, thr=3):
        xy, rgb = parseCBT(tag, profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    need = ["auction_server_market_server", "auction_server_market_global"]
    succ = []
    failed = []

    if not await wait_and_click("main_menu_gui", timeout=7):
        log(f"Не удалось открыть главное меню В АУКЕ", window_id)
        return False

    if not await wait_and_click("auction_menu", timeout=4):
        log(f"Не удалось ткнуть по auction_menu", window_id)
        return False

    await asyncio.sleep(0.3)
    xy, rgb = parseCBT("auction_nalog", profile=profile)
    if not await profile.check_pixel(xy, rgb, timeout=DELAY_WAIT_AUCTION, thr=4):
        log("Чет пошло не так, не прогрузился аук =( Пробую выйти в меню", window_id)
        await wait_and_click("main_menu_gui", timeout=1)
        return False

    for k in need:
        try_success = True

        if not await wait_and_click(k, timeout=4):
            log(f"Не удалось ткнуть по {k}", window_id)
            try_success = False
        else:
            await asyncio.sleep(3)

        if try_success and not await wait_and_click("auction_sell_page", timeout=5):
            log(f"Не удалось ткнуть по auction_sell_page для {k}", window_id)
            try_success = False

        if try_success and not await wait_and_click("auction_sell_select_all_active", timeout=5):
            log(f"Не удалось ткнуть по auction_sell_select_all_active для {k}", window_id)
            try_success = False

        if try_success and not await wait_and_click("auction_sell_reregister_active", timeout=5):
            log(f"Не удалось ткнуть по auction_sell_reregister_active для {k}", window_id)
            try_success = False

        if try_success and not await wait_and_click("auction_sell_reregister_confirm", timeout=5):
            log(f"Не удалось ткнуть по auction_sell_reregister_confirm для {k}", window_id)
            try_success = False

        await asyncio.sleep(0.3)

        if try_success:
            xy, rgb = parseCBT("auction_sell_select_all_inactive", profile=profile)
            waited = await profile.check_pixel(xy, rgb, timeout=70, thr=0)
            if waited:
                succ.append(k)
            else:
                failed.append(k)
        else:
            failed.append(k)


    if succ:
        log(f"Успешно перевыставил аук! | {succ}", window_id)
    if failed:
        log(f"Не удалось перевыставить аук! | {failed}", window_id)

    await wait_and_click("main_menu_gui", timeout=1)

    return bool(succ)

async def autohunt(profile) -> bool:
    button_xy, button_rgb = parseCBT("auto_combat_mode_gui", profile=profile)
    button_x, button_y = button_xy
    click = await profile.mouse.click(profile.window_info, button_x, button_y)
    if click:
        return True
    else:
        return False

async def schedule(profile, state) -> bool:

    async def wait_and_click(tag, timeout=5, thr=3):
        xy, rgb = parseCBT(tag, profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False
    tag = ""
    window_id = next(iter(profile.window_info))
    if state == "on":
        log("Пробую запустить расписание", window_id)
        if profile.settings.TELEGRAM_NOTIFIES:
            profile.tgbot.send_notification(
                level="info",
                text="Пробую включить шедулю",
                nickname=window_id,
            )
        tag = "schedule_start"
    if state == "off":
        log("Пробую остановить расписание", window_id)
        if profile.settings.TELEGRAM_NOTIFIES:
            profile.tgbot.send_notification(
                level="info",
                text="Пробую оффнуть шедулю",
                nickname=window_id,
            )
        tp = await safe_tp(profile)
        tp1 = await wait_teleport(profile)
        if tp1:
            await energo_mode(profile, "on")
            return True

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
        if profile.settings.TELEGRAM_NOTIFIES:
            profile.tgbot.send_notification(
                level="error",
                text=f"Возможно окно залипло, подойди глянь плиз\n\ntry schedule {state} | {tag}",
                nickname=window_id,
            )
            screenn = screenshot_window(profile.window_info, tg=True)
            profile.tgbot.send_pic(photo=screenn, caption="Кажись залипли, #важно",
                                parse_mode="HTML", nickname=window_id,
                                reply_markup=delete_screenshot_kb())

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

async def find_quiver(profile) -> bool:
    xy1, rgb1 = parseCBT("q_quiver", profile=profile)
    window_id = next(iter(profile.window_info))
    if await check_energo_mode(profile):
        quiver = await profile.check_pixel(xy1, rgb1, timeout=2, thr=2, wsize="1x1")
        #print(quiver)
        if quiver:
            return False
        else:
            return True

    return None

async def wait_teleport(profile, need: int = 7) -> bool:
    xy1, rgb1 = parseCBT("zalupka_gui", profile=profile)
    #print(xy1, rgb1)
    window_id = next(iter(profile.window_info))
    success = 0
    await asyncio.sleep(2)

    for _ in range(need):
        await asyncio.sleep(0.25)
        teleported = await profile.check_pixel(xy1, rgb1, timeout=DELAY_TELEPORT_TO_HOME, thr=18 if profile.settings.REGION == "RU" else 2)
        #print(teleported)
        if teleported:
            success += 1

    if success >= 6:
        log(f"tped succ | {success}/{need}", window_id)
        return True
    else:
        log(f"tped failed | {success}/{need}", window_id)
        return False

async def check_autohunt(profile) -> bool:
    xy1, rgb1 = parseCBT("auto_combat_ON", profile=profile)
    window_id = next(iter(profile.window_info))
    success = 0
    await asyncio.sleep(2)

    for _ in range(5):
        await asyncio.sleep(0.1)
        teleported = await profile.check_pixel(xy1, rgb1, timeout=DELAY_AUTOHUNT_CHECK, thr=5)
        if teleported:
            success += 1

    if success >= 3:
        log("hunt succ", window_id)
        return True
    else:
        log("no hunt", window_id)
        return False

async def teleport_to_random_spot(profile, from_: int = 1, to_: int = 4, fast=True) -> bool:
    await asyncio.sleep(0.5)
    window_id = next(iter(profile.window_info))
    spot = random.randint(from_, to_)

    log(f"Пробую тпнуться на спот №{spot}", window_id)

    if not fast:
        if await check_energo_mode(profile):
            log(f"Был в энерго, вырубаю перед тп", window_id)
            await energo_mode(profile, "off")

    await asyncio.sleep(0.05)

    steps = [
        "spot_teleport_call_button",
        f"spot_choice_{spot}",
        f"spot_accept_choice_{spot}"
    ]

    for key in steps:
        xy, rgb = parseCBT(key, profile=profile)

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
        profile.runtime_data.update_last_return()
        if profile.settings.TELEGRAM_NOTIFIES:
            profile.tgbot.send_notification(
                level="trash",
                text="Тпнулся на спот успешно",
                nickname=window_id,
            )
        return True

    return False

async def respawn(profile):
    window_id = next(iter(profile.window_info))
    if profile.settings.TELEGRAM_NOTIFIES:
        profile.tgbot.send_notification(
            level="warning",
            text="Пробую воскресить чара",
            nickname=window_id,
        )
    rip_energo = False
    emode = await check_energo_mode(profile)
    if emode:
        energokill = parseCBT("you_were_killed_energomode", profile=profile)
        xy, rgb = energokill
        rip_energo = await profile.check_pixel(xy, rgb, timeout=2)
        await energo_mode(profile, "off")
        await asyncio.sleep(2)

    if rip_energo:
        xy1, rgb1 = parseCBT("respawn_village", profile=profile)
        await profile.mouse.click(profile.window_info, xy1[0], xy1[1], fast=True)
        await asyncio.sleep(5)
        if emode:
            await energo_mode(profile, "on")
            await asyncio.sleep(1)
        return True
    else:
        xy1, rgb1 = parseCBT("respawn_village", profile=profile)
        await profile.mouse.click(profile.window_info, xy1[0], xy1[1], fast=True)
        await asyncio.sleep(2)
        return True

    path = screenshot_window(profile.window_info)
    if profile.settings.TELEGRAM_NOTIFIES:
        profile.tgbot.send_notification(
            level="error",
            text=f"Воскрешение неудачно =(\nГляди {path}",
            nickname=window_id,
        )
    return False

async def check_bablo(profile):
    cbt = "monetka_gui"
    xy, rgb = parseCBT(cbt, profile=profile)
    return await profile.check_pixel(xy, rgb, timeout=1, thr=7, wsize="2x2")

async def check_rip(profile) -> bool:
    window_id = next(iter(profile.window_info))
    cbts = ["you_were_killed_energomode", "check_death_penalty", "respawn_village"]

    #log("Начал чекать смерть", window_id)

    async def check(cbt: str) -> bool:
        #log(f"Чекаю {cbt}", window_id)
        xy, rgb = parseCBT(cbt, profile=profile)
        return await profile.check_pixel(xy, rgb, timeout=5)

    results = await asyncio.gather(*(check(cbt) for cbt in cbts))
    for cbt, found in zip(cbts, results):
        if found:
            log(f"Детектнул {cbt}", window_id)
            return True, cbt

    return False, ""

# возможно надо будет вернуть старую, бацнул тестовый варик. надо фидбек собрать #todo
async def get_npc_positions(profile, thr=THR_CHECK_NPC_POSITIONS, retries: int = 5) -> Optional[Dict[str, str]]:
    window_id = next(iter(profile.window_info))

    npc_batches = [[2, 3], [4, 5]]
    if profile.settings.REGION == "RU":
        npc_batches.append([6])

    for attempt in range(1, retries + 1):
        log(f"Попытка {attempt}/{retries} получить позиции нпс", window_id)

        found_j = None

        for batch in npc_batches:
            async def check_npc(j):
                xy, rgb = parseCBT(f"npc_list_{j}", profile=profile)
                result = await profile.check_pixel(
                    xy,
                    rgb,
                    timeout=DELAY_CHECK_NPC_POSITIONS,
                    thr=thr,
                    wsize="1x1",
                )
                return j if result else None

            results = await asyncio.gather(*(check_npc(j) for j in batch))
            found_j = min([r for r in results if r is not None], default=None)

            if found_j:
                break

        if found_j:
            log(f"Детектнул позиции, {found_j}", window_id)
            if found_j == 2:
                npc_mapping = {"stash": "npc_list_2", "shop": "npc_list_1", "buyer": "npc_list_4"}
            elif found_j == 3:
                npc_mapping = {"stash": "npc_list_3", "shop": "npc_list_1", "buyer": "npc_list_5"}
            elif found_j == 4:
                npc_mapping = {"stash": "npc_list_4", "shop": "npc_list_2", "buyer": "npc_list_6"}
            elif found_j == 5:
                npc_mapping = {"stash": "npc_list_5", "shop": "npc_list_3", "buyer": "no_data"}
            elif found_j == 6:
                npc_mapping = {"stash": "npc_list_6", "shop": "npc_list_4", "buyer": "no_data"}

            profile.runtime_data.update_last_mapping(npc_mapping)
            log(f"NPC mapping: {json.dumps(npc_mapping, indent=4)}", window_id)
            return npc_mapping

        await asyncio.sleep(0.3)

    log(f"get_npc_positions false, не обнаружил npc за {retries} попыток", window_id)
    return None



async def check_town(profile) -> tuple[bool, dict | None]:
    window_id = next(iter(profile.window_info))
    timeout = 50
    start_time = asyncio.get_event_loop().time()
    log(f"Начал проверять в городе ли я, таймаут: {timeout}", window_id)

    while asyncio.get_event_loop().time() - start_time < timeout:
        xy, rgb = parseCBT("white_cube_in_minimap", profile=profile)
        log(f"Чекаю белый кубик на мапе", window_id)
        if xy is None or rgb is None:
            return False, None

        result = await profile.check_pixel(xy, rgb, timeout=1)
        if result:
            log(f"Белый кубик найден, открываю список нпс", window_id)
            xy, rgb = parseCBT("npc_list_in_town", profile=profile)
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
                    await asyncio.sleep(2)
                    allNPC = await get_npc_positions(profile)
                    if allNPC:
                        log("Список нпс уже открыт, мы в городе", window_id)
                        return True, allNPC

                    if profile.settings.TELEGRAM_NOTIFIES:
                        screenn = screenshot_window(profile.window_info, tg=True)
                        profile.tgbot.send_pic(
                            photo=screenn,
                            caption="Кажись залипли, #важно",
                            parse_mode="HTML",
                            nickname=window_id,
                            reply_markup=delete_screenshot_kb()
                        )
                    log("Встал, верну False", window_id)
                    return False, None

            log("Все условия не пройдены, жесть", window_id)

        await asyncio.sleep(0.5)

    log("Не удалось определить, в городе ли мы =( (ТАЙМАУТ ТИПО ИСТЕК)", window_id)
    return False, None


async def buy_in_shop(profile, in_town=None, npcs=None, check_loot=False) -> tuple[bool, bool, dict]:
    profile.runtime_data.update_buy()
    window_id = next(iter(profile.window_info))
    if in_town is None or npcs is None:
        in_town, npcs = await check_town(profile)

    if 'shop' not in npcs or npcs['shop'] == "no_data":
        return False, in_town, npcs

    xy, rgb = parseCBT(npcs['shop'], profile=profile)
    if xy is None:
        return False, in_town, npcs

    #todo просто проверять есть ли крест и нужен ли выкуп, потом добавлю
    #if check_loot:
    #    try_to_buy = await buy_loot(profile)
    #    if try_to_buy:
    #        log("Успешно выкупил шмотки пока пробегал в городе!", window_id)

    await profile.mouse.click(profile.window_info, *xy)

    xy_btn1, rgb_btn1 = parseCBT("npc_shop_button_1", profile=profile)
    if xy_btn1 is None:
        return False, in_town, npcs

    for i in range(200):
        if await profile.check_pixel(xy_btn1, rgb_btn1, timeout=0.1):
            await asyncio.sleep(0.45)
            await profile.mouse.click(profile.window_info, *xy_btn1)
            break
        await asyncio.sleep(0.05)
    else:
        return False, in_town, npcs

    xy_btn2, rgb_btn2 = parseCBT("npc_shop_button_2", profile=profile)
    if xy_btn2 is None:
        return False, in_town, npcs

    if await profile.check_pixel(xy_btn2, rgb_btn2, timeout=1.5):
        await profile.mouse.click(profile.window_info, *xy_btn2)

        xy_no_adena, rgb_no_adena = parseCBT("npc_shop_button_no_adena", profile=profile)
        if xy_no_adena:
            for j in range(5):
                if await profile.check_pixel(xy_no_adena, rgb_no_adena, timeout=0.1):
                    xy_quit, rgb_quit = parseCBT("npc_global_quit_button", profile=profile)
                    xy_ok, rgb_ok = parseCBT("npc_shop_button_no_adena_confirm", profile=profile)
                    if xy_ok and await profile.check_pixel(xy_ok, rgb_ok, timeout=1):
                        await profile.mouse.click(profile.window_info, *xy_ok)
                        await asyncio.sleep(0.25)
                        await profile.mouse.click(profile.window_info, *xy_quit)
                    #todo tg uved here
                    return True, in_town, npcs
                await asyncio.sleep(0.1)

    xy_btn3, rgb_btn3 = parseCBT("npc_shop_button_3", profile=profile)
    if xy_btn3 and await profile.check_pixel(xy_btn3, rgb_btn3, timeout=1.5):
        await profile.mouse.click(profile.window_info, *xy_btn3)

    xy_quit, rgb_quit = parseCBT("npc_global_quit_button", profile=profile)
    if xy_quit and await profile.check_pixel(xy_quit, rgb_quit, timeout=4):
        await profile.mouse.click(profile.window_info, *xy_quit)
        await asyncio.sleep(0.25)
        return True, in_town, npcs

    return False, in_town, npcs


async def go_stash(profile, in_town=None, npcs=None) -> tuple[bool, bool, dict]:
    window_id = next(iter(profile.window_info))
    log("Старт go_stash", window_id)

    profile.runtime_data.update_stashing()

    if in_town is None or npcs is None:
        log("чекаю нпс", window_id)
        in_town, npcs = await check_town(profile)
        log(f"in_town: {in_town}, npcs: {npcs}", window_id)

    if 'stash' not in npcs or npcs['stash'] == "no_data":
        log("стеш не найден", window_id)
        return False, in_town, npcs

    xy, rgb = parseCBT(npcs['stash'], profile=profile)
    if xy is None:
        log("корды стеша не нашел", window_id)
        return False, in_town, npcs

    log(f"клик по стешу {xy}", window_id)
    await profile.mouse.click(profile.window_info, *xy)

    stash_buttons = ["npc_stash_button_1", "npc_stash_button_2"]
    for i, button in enumerate(stash_buttons):
        xy_btn, rgb_btn = parseCBT(button, profile=profile)
        if xy_btn is None:
            log(f"корды {button} не нашел", window_id)
            if i == 0:
                return False, in_town, npcs
            continue

        if i == 0:
            log(f"жду {button}...", window_id)
            for _ in range(200):
                if await profile.check_pixel(xy_btn, rgb_btn, timeout=0.2, thr=7):
                    await asyncio.sleep(0.45)
                    log(f"клик по {button} в {xy_btn}", window_id)
                    await profile.mouse.click(profile.window_info, *xy_btn)
                    break
                await asyncio.sleep(0.05)
            else:
                log(f"таймаут {button}", window_id)
                return False, in_town, npcs
        else:
            if await profile.check_pixel(xy_btn, rgb_btn, timeout=1.5):
                log(f"клац {button} в {xy_btn}", window_id)
                await profile.mouse.click(profile.window_info, *xy_btn)
            else:
                log(f"кнопка {button} не появилась", window_id)

    xy_quit, rgb_quit = parseCBT("npc_global_quit_button", profile=profile)
    if xy_quit and await profile.check_pixel(xy_quit, rgb_quit, timeout=4):
        log(f"клацнул выход {xy_quit}", window_id)
        await profile.mouse.click(profile.window_info, *xy_quit)
        await asyncio.sleep(0.25)
        log("завершил функу", window_id)
        return True, in_town, npcs

    log("не завершил функу", window_id)
    return False, in_town, npcs



async def sell_buyer(profile, in_town=None, npcs=None) -> tuple[bool, bool, dict]:
    window_id = next(iter(profile.window_info))
    log("Старт sell_buyer", window_id)

    profile.runtime_data.update_purc()

    if in_town is None or npcs is None:
        log("чекаю нпс", window_id)
        in_town, npcs = await check_town(profile)
        log(f"in_town: {in_town}, npcs: {npcs}", window_id)

    if 'buyer' not in npcs or npcs['buyer'] == "no_data":
        log("скуп не найден", window_id)
        return False, in_town, npcs

    xy, rgb = parseCBT(npcs['buyer'], profile=profile)
    if xy is None:
        return False, in_town, npcs

    log(f"клик по скупу {xy}", window_id)
    await profile.mouse.click(profile.window_info, *xy)

    buyer_buttons = ["npc_buyer_button_1", "npc_buyer_button_2", "npc_buyer_button_3"]
    for i, button in enumerate(buyer_buttons):
        xy_btn, rgb_btn = parseCBT(button, profile=profile)
        if xy_btn is None:
            log(f"корды {button} не нашел", window_id)
            if i == 0:
                return False, in_town, npcs
            continue

        if i == 0:
            log(f"жду {button}...", window_id)
            for _ in range(200):
                if await profile.check_pixel(xy_btn, rgb_btn, timeout=0.1):
                    await asyncio.sleep(0.45)
                    log(f"клик по {button} в {xy_btn}", window_id)
                    await profile.mouse.click(profile.window_info, *xy_btn)
                    break
                await asyncio.sleep(0.05)
            else:
                log(f"таймаут {button}", window_id)
                return False, in_town, npcs
        else:
            if await profile.check_pixel(xy_btn, rgb_btn, timeout=1.5):
                log(f"клац {button} в {xy_btn}", window_id)
                await profile.mouse.click(profile.window_info, *xy_btn)
            else:
                log(f"кнопка {button} не появилась", window_id)

    xy_quit, rgb_quit = parseCBT("npc_global_quit_button", profile=profile)
    if xy_quit and await profile.check_pixel(xy_quit, rgb_quit, timeout=4):
        log(f"клацнул выход {xy_quit}", window_id)
        await profile.mouse.click(profile.window_info, *xy_quit)
        await asyncio.sleep(0.25)
        log("завершил функу", window_id)
        return True, in_town, npcs

    log("не завершил функу", window_id)
    return False, in_town, npcs


async def buy_loot(profile) -> bool:
    window_info = profile.window_info

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")

    xy, rgb = parseCBT("krest_after_respawn", profile=profile)
    if not await profile.check_pixel(xy, rgb, timeout=1.5):
        return False

    await profile.mouse.click(window_info, xy[0], xy[1])
    await asyncio.sleep(0.5)

    xy, rgb = parseCBT("respawn_icon_in_gui", profile=profile)
    if not await profile.check_pixel(xy, rgb, timeout=2):
        xy_select_all, rgb_select_all = parseCBT("respawn_select_all", profile=profile)
        if await profile.check_pixel(xy_select_all, rgb_select_all, timeout=1):
            await profile.mouse.click(window_info, xy_select_all[0], xy_select_all[1])
            await asyncio.sleep(0.5)
            xy_delete_exp, rgb_delete_exp = parseCBT("delete_exp", profile=profile)
            if await profile.check_pixel(xy_delete_exp, rgb_delete_exp, timeout=2):
                await profile.mouse.click(window_info, xy_delete_exp[0],
                                          xy_delete_exp[1])
                await asyncio.sleep(0.3)
                xy_yes, rgb_yes = parseCBT("delete_all_yes", profile=profile)
                if await profile.check_pixel(xy_yes, rgb_yes, timeout=2):
                    await profile.mouse.click(window_info, xy_yes[0], xy_yes[1])
                    await asyncio.sleep(0.1)
                    xy, _ = parseCBT("respawn_exit_gui_button", profile=profile)
                    await profile.mouse.click(window_info, xy[0], xy[1])
                    await asyncio.sleep(0.2)
                    return False
                return False
        return False

    async def do_buy():
        xy_monetka, rgb_monetka = parseCBT("monetka_respawn", profile=profile)
        for _ in range(3):
            if await profile.check_pixel(xy_monetka, rgb_monetka, timeout=1):
                break
            await profile.mouse.click(window_info, xy_monetka[0], xy_monetka[1])
            await asyncio.sleep(0.4)

        buyyed = 0
        for i in range(1, 5):
            key = f"respawn_monetka_exp_{i}"
            xy, rgb = parseCBT(key, profile=profile)
            if await profile.check_pixel(xy, rgb, timeout=0.5):
                await profile.mouse.click(window_info, xy[0], xy[1])
                buyyed += 1
                await asyncio.sleep(0.1)

        if buyyed == 4:
            await asyncio.sleep(0.5)
            xy, rgb = parseCBT("respawn_monetka_exp_1", profile=profile)
            if await profile.check_pixel(xy, rgb, timeout=1):
                await profile.mouse.click(window_info, xy[0], xy[1])
                await asyncio.sleep(0.1)

        xy, rgb = parseCBT("respawn_buy_gui_button", profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=2):
            await profile.mouse.click(window_info, xy[0], xy[1])
            await asyncio.sleep(0.3)
        else:
            return False

        xy, rgb = parseCBT("respawn_accept_buy_gui_button", profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=2):
            await profile.mouse.click(window_info, xy[0], xy[1])
            await asyncio.sleep(0.4)
            return True

        return False

    await do_buy()
    xy, _ = parseCBT("respawn_items", profile=profile)
    await profile.mouse.click(window_info, xy[0], xy[1])
    await asyncio.sleep(0.5)
    await do_buy()
    xy, _ = parseCBT("respawn_exit_gui_button", profile=profile)
    await profile.mouse.click(window_info, xy[0], xy[1])
    await asyncio.sleep(0.3)

    return True


async def claim_mail(profile) -> bool:
    claimed = False
    window_id = next(iter(profile.window_info))

    async def wait_and_click(tag, timeout=5, thr=3):
        xy, rgb = parseCBT(tag, profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr):
            x, y = xy
            await profile.mouse.click(profile.window_info, x, y)
            return True
        return False

    async def check_clr(tag):
        xy, rgb = parseCBT(tag, profile=profile)
        return await profile.check_pixel(xy, rgb, timeout=2)

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")

    if not await wait_and_click("main_menu_gui", timeout=7):
        log(f"Не удалось открыть главное меню", window_id)
        return False

    if not await wait_and_click("red_dot_mail_menu", timeout=1, thr=10):
        await wait_and_click("main_menu_gui", timeout=1)
        log(f"Не найден значок почты", window_id)
        return False
    else:
        log("Нашел почту", window_id)

    red_dot_ex = await check_clr("red_dot_mail")
    claim_ex = await check_clr("claim_all_mail")

    if red_dot_ex and claim_ex:
        if not await wait_and_click("claim_all_mail", timeout=1):
            await wait_and_click("npc_global_quit_button", timeout=1)
            log(f"Не удалось нажать Claim All (почта)", window_id)
            return False

        start_time = time.time()
        while time.time() - start_time < 120:
            await asyncio.sleep(2)

            red_dot_ex = await check_clr("red_dot_mail")
            cancel_ex = await check_clr("yes_button_vitality")

            if cancel_ex:
                await wait_and_click("cancel_button_vitality", timeout=2)
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

async def find_daily(profile, window_info, left, top, width, height):

    async def wait_and_click(tag, timeout=5, thr=3):
        xy, rgb = parseCBT(tag, profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr):
            x, y = xy
            await profile.mouse.click(window_info, x, y)
            log(f"Клик по {tag} на {xy}", next(iter(window_info.keys())))
            return True
        log(f"Не найден {tag}", next(iter(window_info.keys())))
        return False

    async def kuchkovator(points, radius=12):
        if not points:
            log("Нет точек для кучковки, мб вкладка говно", next(iter(window_info.keys())))
            return []

        grouped = []
        points = sorted(points, key=lambda c: (c[1], c[0]))
        group = [points[0]]
        for pt in points[1:]:
            if any((pt[0]-g[0])**2 + (pt[1]-g[1])**2 <= radius**2 for g in group):
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
        hits = []
        with mss.mss() as sct:
            monitor = {"left": left, "top": top, "width": width, "height": height}
            screenshot = np.array(sct.grab(monitor))

        img_rgb = screenshot[:, :, :3][:, :, ::-1]
        for y_start, y_end in s_ranges:
            for y in range(y_start, y_end + 1):
                for x in range(width):
                    pixel = img_rgb[y, x]
                    if all(abs(int(pixel[i]) - target_rgb[i]) <= thre for i in range(3)):
                        hits.append((x, y))

        hits.sort(key=lambda c: (c[1], c[0]))
        return hits

    almaz_rgb = tuple(map(int, DAILY["almaz_donate"][0].split(',')))
    monetka_rgb = tuple(map(int, DAILY["monetka_donate"][0].split(',')))
    donate_rgb = tuple(map(int, DAILY["donate_monetka_supermonetka"][0].split(',')))
    claim_rgb = tuple(map(int, DAILY["claim_daily"][0].split(',')))

    s_ranges = [
        (DAILY["start_button_1"], DAILY["end_button_1"]),
        (DAILY["start_button_2"], DAILY["end_button_2"]),
    ]

    while True:
        await asyncio.sleep(1)
        claim_positions = colorfinder(claim_rgb, 10, s_ranges)
        almaz_positions = colorfinder(almaz_rgb, 2, s_ranges)
        monetka_positions = colorfinder(monetka_rgb, 2, s_ranges)

        if len(almaz_positions) >= 2:
            log("На вкладке 2 или больше алмазов — пропускаем", next(iter(window_info.keys())))
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
                            log(f"Пропускаем кнопку с алмазом/донатом: {(x_c, y_c)}", next(iter(window_info.keys())))
                            break
                else:
                    log(f"Собираю награду тут: {(x_c, y_c)}", next(iter(window_info.keys())))
                    await profile.mouse.click(window_info, x_c, y_c)
                    await asyncio.sleep(0.5)
                    await skip_vitlity(profile, "claim")

            return ["claimed"]

        if len(almaz_positions) == 1:
            log("Скипаем 1 алмаз", next(iter(window_info.keys())))
            return []

        return []


async def claim_daily(profile) -> bool:
    window_info = profile.window_info
    window_id, window = next(iter(window_info.items()))
    left, top = window["Position"]
    width, height = window["Width"], window["Height"]

    async def wait_and_click(tag, timeout=5, thr=3):
        xy, rgb = parseCBT(tag, profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=timeout, thr=thr):
            x, y = xy
            await profile.mouse.click(window_info, x, y)
            log(f"Клик по {tag} на {xy}", next(iter(window_info.keys())))
            return True
        log(f"Не найден {tag}", next(iter(window_info.keys())))
        return False

    async def find_daily_tabs(left, top, height):
        x_search = DAILY["y_vkladki"]
        red_rgb = tuple(map(int, DAILY["red_dot_clr"][0].split(', ')))
        hits = []
        log("Ищем вкладки", next(iter(window_info.keys())))
        with mss.mss() as sct:
            monitor = {"left": left + x_search, "top": top, "width": 1, "height": height}
            screenshot = np.array(sct.grab(monitor))
            for y in range(height):
                pixel_rgb = screenshot[y, 0][:3][::-1]
                if all(abs(int(pixel_rgb[i]) - red_rgb[i]) <= 16 for i in range(3)):
                    hits.append(y)
        if not hits:
            log("Красной точки нет, скип", next(iter(window_info.keys())))
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

    if await check_energo_mode(profile):
        await energo_mode(profile, "off")

    await wait_and_click("main_menu_gui", timeout=1)
    if not await wait_and_click("red_dot_daily_rewards", timeout=2):
        log("Не нашел красной точки, скипаю", window_id)
        await wait_and_click("main_menu_gui", timeout=1)
        return False

    await asyncio.sleep(1)
    tabs = await find_daily_tabs(left, top, height)
    summary = 0

    if tabs:
        for tab in tabs:
            await asyncio.sleep(1)
            if len(tab) >= 2:
                x, y = map(int, tab[0].split(", "))
                log(f"Перешел на вкладку: {(x, y)}", window_id)
                await profile.mouse.click(window_info, x, y)
                result = await find_daily(profile, window_info, left, top, width, height)
                if result:
                    summary += 1
        await wait_and_click("npc_global_quit_button", timeout=2)
        log(f"Всего собрано: {summary}", window_id)
        return summary > 0
    else:
        await wait_and_click("npc_global_quit_button", timeout=1)
        log("Ничего не собрано", window_id)
        return False


async def claim_achiv(profile) -> bool:
    claimed = False
    window_id = next(iter(profile.window_info))

    async def wait_and_click(tag, timeout=5):
        xy, rgb = parseCBT(tag, profile=profile)
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
    else:
        log("Нашел сбор ачив", window_id)

    if not await wait_and_click("red_dot_achiv2", timeout=3):
        log("Не удалось нажать на вторую точку достижений", window_id)
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    while True:
        found_claim = await wait_and_click("achiv_claim_1", timeout=2)
        await asyncio.sleep(0.2)
        found_accept = await wait_and_click("achiv_claim_accept", timeout=2)

        if not found_claim:
            claimed = True
            await wait_and_click("npc_global_quit_button", timeout=5)
            break

    return claimed

async def claim_clan(profile) -> bool:
    window_id = next(iter(profile.window_info))

    async def wait_and_click(tag, timeout=5):
        xy, rgb = parseCBT(tag, profile=profile)
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
    else:
        log("Нашел сбор клана", window_id)

    if not await wait_and_click("clan_1", timeout=3):
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    if not await wait_and_click("clan_2", timeout=3):
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    if not await wait_and_click("clan_3", timeout=3):
        await wait_and_click("npc_global_quit_button", timeout=5)
        await asyncio.sleep(0.5)
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False
    else:
        await skip_vitlity(profile, "claim")

    if not await wait_and_click("clan_5", timeout=3):
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False
        
    if not await wait_and_click("clan_6", timeout=3):
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    if not await wait_and_click("npc_global_quit_button", timeout=3):
        await wait_and_click("npc_global_quit_button", timeout=5)
        return False

    await asyncio.sleep(0.3)
    return True

async def claim_battle_pass(profile) -> bool:
    window_info = profile.window_info
    window_id = next(iter(window_info))

    async def wait_and_click(tag, timeout=5):
        xy, rgb = parseCBT(tag, profile=profile)
        if await profile.check_pixel(xy, rgb, timeout=timeout):
            x, y = xy
            if tag == "battle_pass_red_dot_gui":
                y += 7
                x -= 5
            await profile.mouse.click(window_info, x, y, fast=True)
            return True
        return False

    async def find_BP_1(t=25, step=5, distance=30):
        await asyncio.sleep(0.5)

        window_id, window = next(iter(window_info.items()))
        left, top = window["Position"]
        width = window["Width"]
        y_search = BATTLE_PASS["y_vkladki"]
        red_rgb = tuple(map(int, BATTLE_PASS["red_dot_clr_vkladka"][0].split(', ')))

        hits = []
        with mss.mss() as sct:
            monitor = {"left": left, "top": top + y_search, "width": width, "height": 1}
            log(f"{monitor}", window_id)
            screenshot = np.array(sct.grab(monitor))[:, :, :3][:, :, ::-1]

            for x in range(0, width, step):
                pixel_rgb = screenshot[0, x]
                if all(abs(int(pixel_rgb[i]) - red_rgb[i]) <= t for i in range(3)):
                    hits.append(x)

            log(f"{hits}", window_id)

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
        log(f"final {result}", window_id)
        return result

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

    xy_sbor1, rgb_sbor1 = parseCBT("battle_pass_sbor_1", profile=profile)
    xy_sbor2, rgb_sbor2 = parseCBT("battle_pass_sbor_2", profile=profile)
    xy_sbor22, rgb_sbor22 = parseCBT("battle_pass_sbor_2_2", profile=profile)
    xy_empty, _ = parseCBT("battle_pass_empty", profile=profile)

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
    else:
        log("Нашел бп", window_id)

    await asyncio.sleep(1)
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
            await skip_vitlity(profile, "claim")
        elif await profile.check_pixel(xy_sbor22, rgb_sbor22, timeout=1):
            await profile.mouse.click(window_info, *xy_sbor22)
            await asyncio.sleep(1)
            await skip_vitlity(profile, "claim")
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
        xy, rgb = parseCBT(tag, profile=profile)
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

    xy_close, rgb_close = parseCBT("magaz_monetka_reklama", profile=profile)
    if await profile.check_pixel(xy_close, rgb_close, timeout=DELAY_WAIT_ADENA_SHOP_ADD, thr=1, wsize="1x1"):
        await asyncio.sleep(1.5)
        xy_close1, rgb_close1 = parseCBT("magaz_circle_close", profile=profile)
        await profile.mouse.click(window_info, *xy_close1)
        log("Вылезла обычная реклама, закрыл гадость", window_id)

    if profile.settings.REGION != "RU":
        xy_google, rgb_google = parseCBT("magaz_google_trigger", profile=profile)
        if await profile.check_pixel(xy_google, rgb_google, timeout=DELAY_WAIT_ADENA_SHOP_GOOGLE, thr=2, wsize="2x2"):
            await asyncio.sleep(0.2)
            if await wait_and_click("magaz_google_close", timeout=2):
                log("Вылез гугл, закрыл гадость", window_id)

    #if not await wait_and_click("red_dot_magaz", timeout=4):
        #await wait_and_click("npc_global_quit_button", timeout=5)
        #log("Кругляша нет, выходим из шопа", window_id)
        #return False

    await asyncio.sleep(0.6)
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

        xy_check, rgb_check = parseCBT("purc_all_magaz", profile=profile)
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