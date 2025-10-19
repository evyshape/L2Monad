import asyncio
import random
import time
from datetime import datetime, timedelta
from random import randint
from typing import Optional

from bot.clogger import log

from profiles.base import BaseProfile
from bot.events.checker import EventsChecker
from bot.events.enums import MonitorType, PRIORITIES, ErrorTypes
from bot.methods.base import parseCBT
from bot.delays import DELAY_PVP_ANSWER, MIN_SLEEP_AFTER_RIP, MAX_SLEEP_AFTER_RIP, \
    MAX_PVP_DODGE_SLEEP, MIN_PVP_DODGE_SLEEP, MAX_LOW_HP_DODGE_SLEEP, MIN_LOW_HP_DODGE_SLEEP
from bot.methods.other import MouseEvents, screenshot_window
from tgbot.keyboards.screenshot import delete_screenshot_kb
from bot.misc import *
from bot.methods.game import (
    check_town,
    check_bablo,
    check_rip,
    wait_teleport,
    buy_in_shop,
    teleport_to_random_spot,
    respawn,
    check_autohunt,
    buy_loot,
    claim_mail,
    check_energo_mode,
    energo_mode,
    claim_daily,
    claim_achiv,
    claim_alliance,
    claim_clan,
    claim_battle_pass,
    claim_donate_shop,
    schedule,
    safe_tp,
    sell_buyer,
    go_stash,
    auction_rereg,
    connect_to_server,
    close_ethernet1_error,
    close_ethernet2_error,
)
from bot.windows.runtime import RuntimeData


class PvPDodge(BaseProfile):
    def __init__(self, window_info, settings=None):
        from tgbot.bot import TgBot
        super().__init__(window_info, settings=settings)
        self.events_checker = EventsChecker()
        self.mouse = MouseEvents()
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._event_worker_task: Optional[asyncio.Task] = None
        self._current_event_task: Optional[asyncio.Task] = None
        self.runtime_data = RuntimeData(current_state="null")
        self.tgbot = TgBot()

    @property
    def profile_name(self) -> str:
        return "PVP Dodge"

    @property
    def profile_version(self) -> str:
        return "1.6.1"

    # todo переделать, хочу class MonitorRule в который суну условия
    @property
    def get_monitors(self) -> list:
        monitors = [MonitorType.SPOT_BACK, MonitorType.ERROR]

        if getattr(self.settings, "PVP_EVADE", False):
            monitors.append(MonitorType.PVP)
        if getattr(self.settings, "PVP_ANSWER", False):
            monitors.append(MonitorType.PVP)
        if getattr(self.settings, "DEATH_CHECKER", False):
            monitors.append(MonitorType.DEATH)
        if getattr(self.settings, "SOSKA_CHECKER", False):
            monitors.append(MonitorType.SOSKA)
        if getattr(self.settings, "HP_BANK_CHECKER", False):
            monitors.append(MonitorType.HP_BANK)
        if getattr(self.settings, "OVERWEIGHT_CHECKER", False):
            monitors.append(MonitorType.OVERWEIGHT)
        if getattr(self.settings, "LOW_HP_DODGE", False):
            monitors.append(MonitorType.LOW_HP_DODGE)

        if getattr(self.settings, "SCHEDULE_BUYING", ""):
            monitors.append(MonitorType.SELL_STASH_BUY)
        if getattr(self.settings, "SCHEDULE_MAIL", ""):
            monitors.append(MonitorType.CLAIM_MAIL)
        if getattr(self.settings, "SCHEDULE_REWARDS", ""):
            monitors.append(MonitorType.CLAIM_REWARDS)
        if getattr(self.settings, "SCHEDULE_SCHEDULE", ""):
            monitors.append(MonitorType.SCHEDULE)
        if getattr(self.settings, "SCHEDULE_AUCTION", ""):
            monitors.append(MonitorType.AUCTION)

        return monitors

    async def main_loop(self) -> None:
        window_id = next(iter(self.window_info))
        log(f"Запуск профиля {self.profile_name} {self.profile_version}", window_id)

        hunt = await check_autohunt(self)
        if not hunt:
            energo = await check_energo_mode(self)
            if energo:
                await energo_mode(self, "off")
            rip, btn = await check_rip(self)
            if not rip:
                to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
                if to_spot:
                    self.runtime_data.current_state = "combat"
        if hunt:
            self.runtime_data.current_state = "combat"

        self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
        self._event_worker_task = asyncio.create_task(self._event_worker())

        while self.running:
            await asyncio.sleep(0.1)

    async def on_stop(self) -> None:
        window_id = next(iter(self.window_info))
        log("dodger stopped =(", window_id)
        self.events_checker.stop_monitoring(window_id)
        self.running = False
        if self._event_worker_task:
            self._event_worker_task.cancel()
        if self._current_event_task:
            self._current_event_task.cancel()
        await super().on_stop()

    async def respawn_buy(self):
        window_id = next(iter(self.window_info))
        log("Респавнюсь + посплю + выкуплю шмоточки", window_id)
        respawned = await respawn(self)
        if respawned:
            self.events_checker.stop_monitoring(window_id)
            log("Стопнул мониторинг новых ивентов на время сна", window_id)
            await asyncio.sleep(15) #todo
            await energo_mode(self, "on")
            await asyncio.sleep(1)

            await asyncio.sleep(random.uniform(MIN_SLEEP_AFTER_RIP, MAX_SLEEP_AFTER_RIP))
            log("Поспал, пробую выкупить опыт и шмотки", window_id)
            if await check_energo_mode(self):
                await energo_mode(self, "off")
                await asyncio.sleep(1)

            buyed = await buy_loot(self)
            if buyed:
                log("Что-то выкупил..", window_id)
            if NEED_SHOP_AFTER_RIP:
                log("Пробую идти к бакалейщику", window_id)
                stash_ok, in_town, npcs = await go_stash(self)
                shop_ok, _, _ = await buy_in_shop(self, in_town=in_town, npcs=npcs)
                buyer_ok, _, _ = await sell_buyer(self, in_town=in_town, npcs=npcs)
                if stash_ok:
                    log("Успешно скупился!", window_id)
            await asyncio.sleep(1)
            log("Тпаюсь на спот и ставлю автобой", window_id)
            #todo сунуть проверку телепорт свитков
            to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
            if to_spot:
                self.runtime_data.current_state = "combat"
                self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                return True
            else:
                #todo почему автобой не включился?
                if self.settings.TELEGRAM_NOTIFIES:
                    screenn = screenshot_window(self.window_info, tg=True)
                    self.tgbot.send_pic(
                        photo=screenn,
                        caption=f"Шось пошло не так, не тпнулся на спот либо не включился автобой?",
                        parse_mode="HTML",
                        nickname=window_id,
                        reply_markup=delete_screenshot_kb()
                    )
                self.events_checker.start_monitoring(window_id, self,
                                                     monitors=self.get_monitors)
                return
        else:
            self.events_checker.stop_monitoring(window_id)
            path = screenshot_window(self.window_info)
            log(f"Чини, не трогаю окно 1 час | {path}", window_id)
            await asyncio.sleep(3600)

    async def buying(self):
        window_id = next(iter(self.window_info))
        log("Начал закупаться по расписанию!", window_id)
        await self.bank_restore()

    async def back_to_spot(self):

        window_id = next(iter(self.window_info))
        if self.runtime_data.current_state == "combat":
            return True
        log("Пробую вернуться на спот", window_id)
        self.events_checker.stop_monitoring(window_id)
        energo = await check_energo_mode(self)
        if energo:
            await energo_mode(self, "off")

        if NEED_SHOP_AFTER_PVP_EVADE:
            stash_ok, in_town, npcs = await go_stash(self)
            shop_ok, _, _ = await buy_in_shop(self, in_town=in_town, npcs=npcs, check_loot=True)
            buyer_ok, _, _ = await sell_buyer(self, in_town=in_town, npcs=npcs)

            if stash_ok:
                log("Закупился успешно, вероятно...", window_id)

        await asyncio.sleep(2.5)
        to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
        self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
        if to_spot:
            self.runtime_data.current_state = "combat"

            self.runtime_data.update_last_return()
            return True
        return True

    async def dodge(self) -> None:
        self.runtime_data.set_state("pvp")
        window_id, window = next(iter(self.window_info.items()))
        self.events_checker.stop_monitoring(window_id)
        if not FAST_DODGE and self.settings.LOW_HP_DODGE:
            self.events_checker.start_monitoring(window_id, self, monitors=[MonitorType.HEALTH])
            hb = self.settings.HEALTH_BACK
            m = max(hb or [30])
            xy, rgb = parseCBT("pvp_energo_trigger", profile=self)
            await asyncio.sleep(1)

            while await self.check_pixel(xy, rgb, timeout=1, thr=13):
                await asyncio.sleep(0.25)
                hp = self.runtime_data.health
                if hp == 0:
                    log(f"[в додже] Хп вероятно еще не получено либо шось сломалось", window_id)
                    await asyncio.sleep(0.05)
                    continue

                if hp <= m:
                    self.events_checker.stop_monitoring(window_id)
                    log(f"Больше не терпим, траю доджить! | {hp}/{m}", window_id)
                    break
                else:
                    #log(f"Терпим, нас ебут а мы крепчаем... | {hp}/{m}", window_id)
                    pass
            else:
                log("Вышел с цикла, не нашел мечи? если хп в норме не буду доджить...", window_id)
                self.events_checker.stop_monitoring(window_id)
                hp = self.runtime_data.health
                if hp >= m:
                    self.events_checker.start_monitoring(window_id, self,
                                                         monitors=self.get_monitors)
                    log(f"Вроде все ок, хп +- {hp}%, выхожу с доджа", window_id)
                    return

        self.runtime_data.update_last_dodge()
        self.runtime_data.update_dodge_attempt()
        x = False
        xy, rgb = parseCBT("home_scroll_button_energomode", profile=self)
        xy2, rgb2 = parseCBT("home_scroll_button_no_energomode", profile=self)

        click_x = xy[0]
        click_y = xy[1]

        await self.mouse.click(self.window_info, click_x, click_y, fast=True)
        await asyncio.sleep(2)
        await self.mouse.click(self.window_info, xy2[0], xy2[1], fast=True)
        self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
        pixel = await self.check_pixel(xy2, rgb2, 7)
        if pixel:
            log(f"Контрольный тп вжат", window_id)
            await self.mouse.click(self.window_info, xy2[0], xy2[1], fast=True)
            await asyncio.sleep(1)
        else:
            log(f"rip? or no?", window_id)
            rip, btn = await check_rip(self)
            if rip:
                log("rly rip", window_id)
                self.runtime_data.current_state = "death"
                x = True

        result = await wait_teleport(self)
        if result and not x:
            sleept = randint(MIN_PVP_DODGE_SLEEP, MAX_PVP_DODGE_SLEEP)
            await energo_mode(self, "on")
            log(f"Сплю {sleept} мин.", window_id)
            self.runtime_data.update_last_succ_dodge()
            self.runtime_data.current_state = "afk"
            self.runtime_data.spot_time = (datetime.now() + timedelta(minutes=sleept)).strftime("%H:%M")
            if self.settings.TELEGRAM_NOTIFIES:
                self.tgbot.send_notification(
                    level="warning",
                    text="Задоджил пвп успешно",
                    nickname=window_id,
                )
        else:
            if self.settings.TELEGRAM_NOTIFIES:
                self.tgbot.send_notification(
                    level="warning",
                    text="Не смог доджнуть пвп, втф?",
                    nickname=window_id,
                )
                screenn = screenshot_window(self.window_info, tg=True)
                self.tgbot.send_pic(photo=screenn, caption="Не смог доджнуть пвп, #важно", parse_mode="HTML", nickname=window_id, reply_markup=delete_screenshot_kb())

            log(f"bad result? | dodger | pvp tp | rip?", window_id)
            log(f"bad result? | dodger | pvp tp | {result}", window_id)
            rip, btn = await check_rip(self)
            if rip:
                log("rly rip", window_id)
                self.runtime_data.current_state = "death"

    async def bank_restore(self):
        window_id, window = next(iter(self.window_info.items()))
        self.events_checker.stop_monitoring(window_id)
        rip, btn = await check_rip(self)
        if rip:
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            self.runtime_data.current_state = "death"
            return

        self.runtime_data.current_state = "shopping"
        xy, rgb = parseCBT("home_scroll_button_energomode", profile=self)

        click_x = xy[0]
        click_y = xy[1]
        await self.mouse.click(self.window_info, click_x, click_y)
        result = await wait_teleport(self)
        if result:
            stash_ok, in_town, npcs = await go_stash(self)
            shop_ok, _, _ = await buy_in_shop(self, in_town=in_town, npcs=npcs, check_loot=True)
            buyer_ok, _, _ = await sell_buyer(self, in_town=in_town, npcs=npcs)

            if stash_ok:
                to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
                if to_spot:
                    self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                    self.runtime_data.current_state = "combat"
                    if self.settings.TELEGRAM_NOTIFIES:
                        self.tgbot.send_notification(
                            level="trash",
                            text="Закупился успешно",
                            nickname=window_id,
                        )
                    return True
            else:
                log(f"bad result? {result} / buy", window_id)
                town = await check_town(self)
                if town:
                    #todo
                    to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT,
                                                            self.settings.SPOT_DO)
                    if to_spot:
                        self.events_checker.start_monitoring(window_id, self,
                                                             monitors=self.get_monitors)
                        self.runtime_data.current_state = "combat"
                        return True
                else:
                    if self.settings.TELEGRAM_NOTIFIES:
                        screenn = screenshot_window(self.window_info, tg=True)
                        self.tgbot.send_pic(
                            photo=screenn,
                            caption=f"Шось пошло не так в bank_restore\n\nСтеш: {stash_ok}\nГород: {town}",
                            parse_mode="HTML",
                            nickname=window_id,
                            reply_markup=delete_screenshot_kb()
                        )
        else:
            log(f"/ bad result? {result} / else", window_id)
            rip, btn = await check_rip(self)
            if rip:
                log("Помер мгновенно как приехал на спот, бувае...", window_id)

            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)


    async def mail(self):
        window_id, window = next(iter(self.window_info.items()))
        cstate = self.runtime_data.current_state
        if cstate == "death":
            return
        self.runtime_data.current_state = "claiming"
        self.events_checker.stop_monitoring(window_id)
        log("Не мониторю новые события во время почты", window_id)
        claimed_mail = await claim_mail(self)
        if claimed_mail:
            log(f"Почта успешно собрана", window_id)
            if self.settings.TELEGRAM_NOTIFIES:
                self.tgbot.send_notification(
                    level="trash",
                    text="Собрал почту",
                    nickname=window_id,
                )
        else:
            log(f"Нет новой почты или не удалось собрать", window_id)

        if not await check_energo_mode(self):
            if cstate != "death":
                await energo_mode(self, "on")
                self.runtime_data.current_state = cstate
                self.events_checker.start_monitoring(window_id, self,
                                                     monitors=self.get_monitors)
                return True
            else:
                self.events_checker.start_monitoring(window_id, self,
                                                     monitors=self.get_monitors)
                self.runtime_data.set_state("death") #wtf если смерть уже была, ну пох

        await asyncio.sleep(1)

    async def rewards(self):
        #print(1)
        window_id, window = next(iter(self.window_info.items()))
        cstate = self.runtime_data.current_state
        #print(cstate)
        if cstate == "death":
            #print(cstate)
            return
        self.events_checker.stop_monitoring(window_id)
        self.runtime_data.current_state = "claiming"
        log("Не мониторю новые события во время сборов", window_id)
        await asyncio.sleep(1)

        if NEED_CLAIM_DAILY:
            claimed_daily = await claim_daily(self)
            if claimed_daily:
                log(f"Дейлик успешно собран", window_id)
            else:
                log(f"Нет новых дейликов или не удалось собрать", window_id)

        if NEED_CLAIM_MAIL:
            claimed_mail = await claim_mail(self)
            if claimed_mail:
                log(f"Почта успешно собрана", window_id)
            else:
                log(f"Нет новой почты или не удалось собрать", window_id)

        if NEED_CLAIM_ACHIV:
            claimed_achiv = await claim_achiv(self)
            if claimed_achiv:
                log(f"Ачивы успешно собраны", window_id)
            else:
                log(f"Нет новых ачивок или не удалось собрать", window_id)

        if NEED_CLAIM_CLAN:
            claimed_clan = await claim_clan(self)
            if claimed_clan:
                log(f"Клан успешно собран", window_id)
            else:
                log(f"Нет новых донатов в клан или не удалось вдонить", window_id)

        if NEED_CLAIM_ALI:
            claim_ali = await claim_alliance(self)
            if claim_ali:
                log(f"Альянс успешно собран", window_id)
            else:
                log(f"Не смог собрать альянс", window_id)

        if NEED_CLAIM_BATTLE_PASS:
            claimed_bp = await claim_battle_pass(self)
            if claimed_bp:
                log(f"Пасс успешно собран", window_id)
            else:
                log(f"Не смог собрать пасс", window_id)

        if NEED_CLAIM_DONATE_SHOP:
            claimed_shop = await claim_donate_shop(self)
            if claimed_shop:
                log(f"Шоп успешно собран", window_id)
            else:
                log(f"Не смог собрать шоп", window_id)

        if self.settings.TELEGRAM_NOTIFIES:
            self.tgbot.send_notification(
                level="trash",
                text="Собрал награды по расписанию",
                nickname=window_id,
            )

        if not await check_energo_mode(self):
            if cstate != "death":
                await energo_mode(self, "on")
                self.runtime_data.current_state = cstate
                self.events_checker.start_monitoring(window_id, self,
                                                     monitors=self.get_monitors)
                return True
        else:
            self.runtime_data.current_state = cstate
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)

        await asyncio.sleep(1)

    async def schedule_schedule(self):
        window_id, window = next(iter(self.window_info.items()))
        cstate = self.runtime_data.current_state
        #print(cstate)
        if cstate == "death":
            #print(cstate)
            return
        self.events_checker.stop_monitoring(window_id)
        self.runtime_data.current_state = "schedule"
        if await check_energo_mode(self):
            await energo_mode(self, "off")
            await asyncio.sleep(1)

        sch = await schedule(self, "on")
        if sch:
            farm = 0
            log("Расписание началось", window_id)
            while self.settings.is_schedule_schedule():
                log(f"Расписание уже идет, прошло {farm} сек.", window_id)
                farm += 300
                await asyncio.sleep(300)

            log("Расписание кончилось", window_id)
            await schedule(self, "off")
            if await check_energo_mode(self):
                await energo_mode(self, "off")
                await asyncio.sleep(1)
            tp = await safe_tp(self)
            if tp:
                stash_ok, in_town, npcs = await go_stash(self)
                shop_ok, _, _ = await buy_in_shop(self, in_town=in_town, npcs=npcs)
                buyer_ok, _, _ = await sell_buyer(self, in_town=in_town, npcs=npcs)
                to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
                if to_spot:
                    self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                    self.runtime_data.current_state = "combat"
                    return True

            log("wtf?", window_id)
            self.runtime_data.current_state = "afk"

    async def overweight_check(self):
        window_id, window = next(iter(self.window_info.items()))
        runtime = self.runtime_data
        afk_threshold = self.settings.OVERWEIGHT_AFK
        current_level = runtime.overweight.value

        to_notify = runtime.need_notify()
        if to_notify is not None:
            log(f"Перевес изменился: {runtime.last_overweight.value} -> {current_level}",
                window_id)
            if self.settings.TELEGRAM_NOTIFIES:
                self.tgbot.send_notification(
                    level="info" if current_level < afk_threshold else "warning",
                    text=f"Перевес окна: {current_level}",
                    nickname=window_id
                )

        if current_level >= afk_threshold and runtime.current_state != "afk":
            runtime.set_state("afk")
            self.events_checker.stop_monitoring(window_id)
            log(f"Перевес достиг порога, переводим в афк: {current_level}", window_id)
            tped = await safe_tp(self)
            if tped:
                await wait_teleport(self)
                await energo_mode(self, "on")
                if self.settings.TELEGRAM_NOTIFIES:
                    await asyncio.sleep(4)
                    screenn = screenshot_window(self.window_info, tg=True)
                    self.tgbot.send_pic(
                        photo=screenn,
                        caption="Дошли до порога перевеса, стоим в городе афк #важно\nРекомендую сгрузить мусор и перезапустить окно через тг бота",
                        parse_mode="HTML",
                        nickname=window_id,
                        reply_markup=delete_screenshot_kb()
                    )

    async def pvp_answer(self):
        window_id, window = next(iter(self.window_info.items()))
        wait = DELAY_PVP_ANSWER
        log(f"Пробую ответить на пвп, таймаут: {wait} сек.", window_id)

        self.events_checker.stop_monitoring(window_id)
        self.runtime_data.set_state("pvp")
        xy, rgb = parseCBT("pvp_energo_trigger", profile=self)
        click_x, click_y = xy
        await self.mouse.click(self.window_info, click_x, click_y, fast=True)

        self.events_checker.start_monitoring(window_id, self,
                                             monitors=[MonitorType.HEALTH,
                                                       MonitorType.DEATH])

        wait = await wait_teleport(self, need=1)
        if not wait:
            log("wtf? not wait pvp answer unblock", window_id)
            self.events_checker.stop_monitoring(window_id)
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            return

        for x in range(wait * 10):
            current = time.time()
            last_death = self.events_checker.get_last_timestamp(window_id, "death")
            if last_death is not None and current - last_death <= 20:
                log(f"Сдохли во время ответа, анлук", window_id)
                return

            health = self.runtime_data.health
            if health:
                log(f"Текущее хп: {health}", window_id)
                m = max(self.settings.HEALTH_BACK or [20])
                if health <= m:
                    log(f"Хп упало! {health}% | {m}, пробую улететь!",
                        window_id)

                    xy, rgb = parseCBT("home_scroll_button_no_energomode", profile=self)

                    click_x = xy[0]
                    click_y = xy[1]

                    result = await self.mouse.click(self.window_info, click_x, click_y, fast=True)

                    if result:
                        await asyncio.sleep(1)
                        pixel = await self.check_pixel(xy, rgb, 7)
                        if pixel:
                            log(f"Контрольный тп вжат", window_id)
                            await self.mouse.click(self.window_info, xy[0], xy[1], fast=True)
                            await asyncio.sleep(1)
                        else:
                            log(f"rip? or no?", window_id)
                            rip, btn = await check_rip(self)
                            if rip:
                                log("rly rip", window_id)
                                self.runtime_data.current_state = "death"
                                return

                        tped = await wait_teleport(self)
                        if tped:
                            sleept = randint(3, 5)
                            self.runtime_data.current_state = "afk"
                            self.runtime_data.spot_time = (datetime.now() + timedelta(
                                minutes=sleept)).strftime("%H:%M")
                            log(f"Вроде как ушел от пвп, сплю {sleept} мин.", window_id)
                            self.events_checker.stop_monitoring(window_id)
                            self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                            await asyncio.sleep(1)
                            await energo_mode(self, "on")
                            if self.settings.TELEGRAM_NOTIFIES:
                                self.tgbot.send_notification(
                                    level="warning",
                                    text="Задоджил пвп успешно (после попытки ответа)",
                                    nickname=window_id,
                                )
                            return
                    else:
                        log("Вероятно, погиб?", window_id)
                        rip, btn = await check_rip(self)
                        if rip:
                            log("rly rip", window_id)
                            self.runtime_data.current_state = "death"
                            return

            if await check_bablo(self):
                log(f"Пвп успешно завершено", window_id)
                await asyncio.sleep(1)
                break

        rip, btn = await check_rip(self)
        if rip:
            log(f"{rip} | Сдох после попытки ответа, мда", window_id)
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            return

        log(f"Мы живы! Посмотрю на хп пару секунд и вернусь на спот.", window_id)
        curr_h = self.runtime_data.health
        for _ in range(PVP_ANSWER_CHECK_HP_ITERATIONS):
            hlt = self.runtime_data.health
            hp_diff = curr_h - hlt
            diff = (hp_diff / curr_h) * 100

            rip, _ = await check_rip(self)
            log(f"data|{curr_h}|{hlt}|{hp_diff}|{rip}", window_id)
            if rip:
                log("Смерть во время проверок хп, итс овер...", window_id)
                self.runtime_data.current_state = "death"
                self.events_checker.stop_monitoring(window_id)
                self.events_checker.start_monitoring(window_id, self,
                                                     monitors=self.get_monitors)
                return

            if diff >= 20: # проценты, в целом можно вынести в /bot/misc.py
                log(f"Хп упало на {diff:.1f}%, улетаю!", window_id)
                xy, rgb = parseCBT("home_scroll_button_no_energomode", profile=self)

                click_x = xy[0]
                click_y = xy[1]

                result = await self.mouse.click(self.window_info, click_x, click_y, fast=True)

                if result:
                    await asyncio.sleep(1)
                    pixel = await self.check_pixel(xy, rgb, 7)
                    if pixel:
                        log(f"Контрольный тп вжат", window_id)
                        await self.mouse.click(self.window_info, xy[0], xy[1], fast=True)
                        await asyncio.sleep(1)
                    else:
                        log(f"rip? or no?", window_id)
                        rip, btn = await check_rip(self)
                        if rip:
                            log("rly rip", window_id)
                            self.runtime_data.current_state = "death"
                            return

                    tped = await wait_teleport(self)
                    if tped:
                        sleept = randint(3, 5)
                        self.runtime_data.current_state = "afk"
                        self.runtime_data.spot_time = (datetime.now() + timedelta(
                            minutes=sleept)).strftime("%H:%M")
                        log(f"Вроде как ушел от пвп, сплю {sleept} мин.", window_id)
                        self.events_checker.stop_monitoring(window_id)
                        self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                        await asyncio.sleep(1)
                        await energo_mode(self, "on")
                        if self.settings.TELEGRAM_NOTIFIES:
                            self.tgbot.send_notification(
                                level="warning",
                                text="Задоджил пвп успешно (после попытки ответа2)",
                                nickname=window_id,
                            )
                        return
                else:
                    log("Вероятно, погиб?", window_id)
                    rip, btn = await check_rip(self)
                    if rip:
                        log("rly rip", window_id)
                        self.runtime_data.current_state = "death"
                        return

            await asyncio.sleep(0.1)
        log("exited", window_id)
        rip, btn = await check_rip(self)
        if rip:
            log(f"{rip} | Сдох после попытки ответа, мда2", window_id)
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            return

        self.events_checker.stop_monitoring(window_id)
        to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT,
                                                self.settings.SPOT_DO)
        if to_spot:
            self.runtime_data.current_state = "combat"
            self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
            if self.settings.TELEGRAM_NOTIFIES:
                self.tgbot.send_notification(
                    level="warning",
                    text="Успешно завершил пвп, вероятно кого-то убил?",
                    nickname=window_id,
                )
        else:
            log("Не смог тпнуться на спот, если включено тг - смотри скриншот.")
            await asyncio.sleep(4)
            screenn = screenshot_window(self.window_info, tg=True)
            if self.settings.TELEGRAM_NOTIFIES:
                self.tgbot.send_pic(
                    photo=screenn,
                    caption="После ответа пвп не смог тпнуться на спот, #важно",
                    parse_mode="HTML",
                    nickname=window_id,
                    reply_markup=delete_screenshot_kb()
                )
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            return

    async def auction(self):
        window_id, window = next(iter(self.window_info.items()))
        cstate = self.runtime_data.current_state
        if cstate == "death":
            return
        self.runtime_data.current_state = "claiming"
        self.events_checker.stop_monitoring(window_id)
        log("Не мониторю новые события во время перевыставления аука", window_id)
        if await check_energo_mode(self):
            await energo_mode(self, "off")

        rereg = await auction_rereg(self)

        if not await check_energo_mode(self):
            await energo_mode(self, "on")

        if rereg:
            log(f"Аук успешно перевыставлен!", window_id)
            if self.settings.TELEGRAM_NOTIFIES:
                self.tgbot.send_notification(
                    level="trash",
                    text="Перевыставил аук",
                    nickname=window_id,
                )
        else:
            log(f"Не смог перевыставить аук", window_id)

        self.runtime_data.current_state = cstate
        self.events_checker.start_monitoring(window_id, self,
                                             monitors=self.get_monitors)
        if not await check_energo_mode(self):
            if cstate != "death":
                await energo_mode(self, "on")
                return True

        await asyncio.sleep(1)
        return True

    async def errors(self, desc):
        window_id = next(iter(self.window_info))
        f = desc.value
        func = globals().get(f)

        if func:
            self.events_checker.stop_monitoring(window_id)
            result = await func(self)
            if result:
                self.runtime_data.set_state("afk")
                if desc == ErrorTypes.ETHERNET2_ERROR:
                    res2 = await connect_to_server(self)
                    if res2:
                        self.runtime_data.spot_time = (datetime.now() + timedelta(
                            minutes=3)).strftime("%H:%M")

                        await energo_mode(self, "on")
                    else:
                        if self.settings.TELEGRAM_NOTIFIES:
                            screenn = screenshot_window(self.window_info, tg=True)
                            self.tgbot.send_pic(
                                photo=screenn,
                                caption=f"Чет супер злое после попытки подрубиться на сервер",
                                parse_mode="HTML",
                                nickname=window_id,
                                reply_markup=delete_screenshot_kb()
                            )

                elif desc == ErrorTypes.ETHERNET_ERROR:
                    print(1)
                    if self.runtime_data.current_state == "combat":
                        print(2)
                        await asyncio.sleep(2)
                        await energo_mode(self, "on")

                self.events_checker.start_monitoring(window_id, self,
                                                     monitors=self.get_monitors)
                return
            else:
                if self.settings.TELEGRAM_NOTIFIES:
                    screenn = screenshot_window(self.window_info, tg=True)
                    self.tgbot.send_pic(
                        photo=screenn,
                        caption=f"Чет злое в обработке ошибок #важно | {f}",
                        parse_mode="HTML",
                        nickname=window_id,
                        reply_markup=delete_screenshot_kb()
                    )
        else:
            log(f"{f}", window_id)
            return

    async def lowhp_zatichka(self):
        window_id, window = next(iter(self.window_info.items()))
        xy, rgb = parseCBT("home_scroll_button_energomode", profile=self)
        self.events_checker.stop_once(window_id, MonitorType.LOW_HP_DODGE)
        click_x = xy[0]
        click_y = xy[1]
        await self.mouse.click(self.window_info, click_x, click_y)
        result = await wait_teleport(self)
        if result:
            sleept = randint(MIN_LOW_HP_DODGE_SLEEP, MAX_LOW_HP_DODGE_SLEEP)
            await energo_mode(self, "on")
            log(f"Сплю {sleept} мин.", window_id)
            #self.runtime_data.update_last_succ_dodge()
            self.runtime_data.current_state = "afk"
            self.runtime_data.spot_time = (datetime.now() + timedelta(minutes=sleept)).strftime("%H:%M")
            if self.settings.TELEGRAM_NOTIFIES:
                self.tgbot.send_notification(
                    level="warning",
                    text=f"Мало хп, улетел со спота\nПосплю {sleept} мин.",
                    nickname=window_id,
                )

    async def _event_worker(self) -> None:
        window_id = next(iter(self.window_info))
        while self.running:
            priority, event = await self._event_queue.get()

            if self._current_event_task and not self._current_event_task.done():
                log(f"Отмена / {priority}", window_id)
                self._current_event_task.cancel()
                try:
                    await self._current_event_task
                except asyncio.CancelledError:
                    pass

            self._current_event_task = asyncio.create_task(self._process_event(event))

            try:
                await self._current_event_task
            except asyncio.CancelledError:
                log("Обработка прервана, чини", window_id)

            self._event_queue.task_done()

    async def _process_event(self, event: dict) -> None:
        window_id = next(iter(self.window_info))
        etype = event.get("type")
        desc = event.get("desc")

        if desc:
            log(f"Обработка: {etype} ({desc})", window_id)
        else:
            log(f"Обработка: {etype}", window_id)

        if etype == "pvp":
            if self.settings.PVP_EVADE:
                await self.dodge()
            elif self.settings.PVP_ANSWER:
                await self.pvp_answer()

        elif etype == "low_hp_dodge":
            await self.lowhp_zatichka()
        elif etype == "hp_bank":
            await self.bank_restore()
        elif etype == "death":
            await self.respawn_buy()
        elif etype == "spot_back":
            await self.back_to_spot()
        elif etype == "sell_stash_buy":
            await self.buying()
        elif etype == "claim_mail":
            await self.mail()
        elif etype == "claim_rewards":
            await self.rewards()
        elif etype == "schedule":
            await self.schedule_schedule()
        elif etype == "soska":
            await self.bank_restore()
        elif etype == "overweight":
            await self.overweight_check()
        elif etype == "auction":
            await self.auction()
        elif etype == "error" and desc is not None:
            await self.errors(desc)
        else:
            log(f"Шось страшное и необработанное: {etype}", window_id)

    def send_event(self, event: dict) -> None:
        window_id = next(iter(self.window_info))
        etype = event.get("type")
        priority = PRIORITIES.get(MonitorType(etype), 999)
        self._event_queue.put_nowait((priority, event))
        log(f"Ивент {etype} добавлен в очередь с приоритетом {priority}", window_id)

    def is_running(self):
        return self.running