import asyncio
from typing import Optional
from profiles.base import BaseProfile
from bot.events.enums import MonitorType, PRIORITIES
from bot.events.checker import EventsChecker
from bot.methods.base import parseCBT
from bot.methods.other import MouseEvents
from bot.methods.game import energo_mode, check_rip, wait_teleport, buy_in_shop, \
    teleport_to_random_spot, check_energo_mode, respawn, check_town, check_autohunt, \
    buy_loot, claim_mail, check_energo_mode, energo_mode, claim_daily, \
    claim_achiv, claim_clan, claim_battle_pass, claim_donate_shop, schedule, safe_tp, \
    sell_buyer, go_stash
from random import randint
from clogger import log
from bot.windows.runtime import RuntimeData
from datetime import datetime, timedelta

class PvPDodge(BaseProfile):
    def __init__(self, window_info, settings=None):
        super().__init__(window_info, settings=settings)
        self.events_checker = EventsChecker()
        self.mouse = MouseEvents()
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._event_worker_task: Optional[asyncio.Task] = None
        self._current_event_task: Optional[asyncio.Task] = None
        self.running = True
        self.runtime_data = RuntimeData(current_state="null")

    @property
    def profile_name(self) -> str:
        return "PVP Dodge"

    @property
    def profile_version(self) -> str:
        return "1.4.5"

    @property
    def get_monitors(self) -> list:
        monitors = [MonitorType.SPOT_BACK]
        if self.settings.PVP_EVADE:
            monitors.append(MonitorType.PVP)
        if self.settings.DEATH_CHECKER:
            monitors.append(MonitorType.DEATH)
        if self.settings.HP_BANK_CHECKER:
            monitors.append(MonitorType.HP_BANK)
        if self.settings.SCHEDULE_BUYING != "":
            monitors.append(MonitorType.SELL_STASH_BUY)
        if self.settings.SCHEDULE_MAIL != "":
            monitors.append(MonitorType.CLAIM_MAIL)
        if self.settings.SCHEDULE_REWARDS != "":
            monitors.append(MonitorType.CLAIM_REWARDS)
        if self.settings.SCHEDULE_SCHEDULE != "":
            monitors.append(MonitorType.SCHEDULE)
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
            await asyncio.sleep(1)

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
            if not await check_energo_mode(self):
                await energo_mode(self, "on")
                await asyncio.sleep(1)

            await asyncio.sleep(300)
            log("Поспал 5 минут, пробую выкупить опыт и шмотки", window_id)
            if await check_energo_mode(self):
                await energo_mode(self, "off")
                await asyncio.sleep(1)

            buyed = await buy_loot(self)
            if buyed:
                log("Что-то выкупил..", window_id)
            log("Пробую идти к бакалейщику", window_id)
            result = await go_stash(self)
            result1 = await buy_in_shop(self)
            result2 = await sell_buyer(self)
            if result:
                log("Успешно скупился!", window_id)
            log("Тпаюсь на спот и ставлю автобой", window_id)
            to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
            if to_spot:
                self.runtime_data.current_state = "combat"
                self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                return True
        else:
            self.events_checker.stop_monitoring(window_id)
            log("Чини, не трогаю окно 1 час", window_id)
            await asyncio.sleep(3600)

    async def buying(self):
        window_id = next(iter(self.window_info))
        log("Начал закупаться по расписанию!", window_id)
        await self.bank_restore()

    async def back_to_spot(self):
        window_id = next(iter(self.window_info))
        if self.runtime_data.current_state == "combat":
            return True
        log("Иду закуплюсь", window_id)
        energo = await check_energo_mode(self)
        if energo:
            await energo_mode(self, "off")

        buy = await buy_in_shop(self)
        result = await go_stash(self)
        result2 = await sell_buyer(self)
        if buy:
            log("Закупился успешно, вероятно...", window_id)

        to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
        if to_spot:
            self.runtime_data.current_state = "combat"
            return True
        return True

    async def dodge(self) -> None:
        x = False
        window_id, window = next(iter(self.window_info.items()))
        xy, rgb = parseCBT("home_scroll_button_energomode")
        xy2, rgb2 = parseCBT("home_scroll_button_no_energomode")

        if xy is None:
            return

        click_x = xy[0]
        click_y = xy[1]

        await self.mouse.click(self.window_info, click_x, click_y, fast=True)
        await asyncio.sleep(2)
        await self.mouse.click(self.window_info, xy2[0], xy2[1], fast=True)
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
            sleept = randint(2, 5)
            await energo_mode(self, "on")
            log(f"Сплю {sleept} минут", window_id)
            self.runtime_data.current_state = "afk"
            self.runtime_data.spot_time = (datetime.now() + timedelta(minutes=sleept)).strftime("%H:%M")
        else:
            log(f"bad result? | dodger | pvp tp | rip?", window_id)
            log(f"bad result? | dodger | pvp tp | {result}", window_id)
            rip, btn = await check_rip(self)
            if rip:
                log("rly rip", window_id)
                self.runtime_data.current_state = "death"

    async def bank_restore(self):
        window_id, window = next(iter(self.window_info.items()))
        self.runtime_data.current_state = "shopping"
        xy, rgb = parseCBT("home_scroll_button_energomode")
        if xy is None:
            return
        click_x = xy[0]
        click_y = xy[1]
        await self.mouse.click(self.window_info, click_x, click_y)
        result = await wait_teleport(self)
        if result:
            buy = await buy_in_shop(self)
            result = await go_stash(self)
            result2 = await sell_buyer(self)
            if buy:
                to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
                if to_spot:
                    self.runtime_data.current_state = "combat"
                    return True
            else:
                log(f"bad result? {result}", window_id)
        else:
            log(f"bad result? {result}", window_id)

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
        else:
            log(f"Нет новой почты или не удалось собрать", window_id)

        self.events_checker.start_monitoring(window_id, self,
                                             monitors=self.get_monitors)
        if not await check_energo_mode(self):
            if cstate != "death":
                await energo_mode(self, "on")
                return True

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
        claimed_daily = await claim_daily(self)
        if claimed_daily:
            log(f"Дейлик успешно собран", window_id)
        else:
            log(f"Нет новых дейликов или не удалось собрать", window_id)

        claimed_mail = await claim_mail(self)
        if claimed_mail:
            log(f"Почта успешно собрана", window_id)
        else:
            log(f"Нет новой почты или не удалось собрать", window_id)

        claimed_achiv = await claim_achiv(self)
        if claimed_achiv:
            log(f"Ачивы успешно собраны", window_id)
        else:
            log(f"Нет новых ачивок или не удалось собрать", window_id)

        claimed_clan = await claim_clan(self)
        if claimed_clan:
            log(f"Клан успешно собран", window_id)
        else:
            log(f"Нет новых донатов в клан или не удалось вдонить", window_id)

        claimed_bp = await claim_battle_pass(self)
        if claimed_bp:
            log(f"Пасс успешно собран", window_id)
        else:
            log(f"Не смог собрать пасс", window_id)

        claimed_shop = await claim_donate_shop(self)
        if claimed_shop:
            log(f"Шоп успешно собран", window_id)
        else:
            log(f"Не смог собрать шоп", window_id)

        self.events_checker.start_monitoring(window_id, self,
                                             monitors=self.get_monitors)

        if not await check_energo_mode(self):
            if cstate != "death":
                await energo_mode(self, "on")
                return True

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
                result = await go_stash(self)
                result1 = await buy_in_shop(self)
                result2 = await sell_buyer(self)
                to_spot = await teleport_to_random_spot(self, self.settings.SPOT_OT, self.settings.SPOT_DO)
                if to_spot:
                    self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                    self.runtime_data.current_state = "combat"
                    return True

            log("wtf?", window_id)
            self.runtime_data.current_state = "afk"

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
        log(f"Обработка: {etype}", window_id)

        if etype == "pvp":
            await self.dodge()
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
        else:
            log(f"Что за нах: {etype}", window_id)

    def send_event(self, event: dict) -> None:
        window_id = next(iter(self.window_info))
        etype = event.get("type")
        priority = PRIORITIES.get(MonitorType(etype), 999)
        self._event_queue.put_nowait((priority, event))
        log(f"Ивент {etype} добавлен в очередь с приоритетом {priority}", window_id)
