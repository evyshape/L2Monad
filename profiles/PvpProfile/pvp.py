import asyncio
import random
import time
from datetime import datetime, timedelta
from random import randint, uniform

from bot.clogger import log

from profiles.event_driven import EventDrivenProfile
from bot.events.enums import MonitorType, ErrorTypes, BotState, NotifyLevel
from bot.methods.base import parseCBT
from bot.methods.other import screenshot_window
from bot.methods.game import PartyDungeon


class PvPDodge(EventDrivenProfile):

    @property
    def profile_name(self) -> str:
        return "PVP Dodge"

    @property
    def profile_version(self) -> str:
        return "1.6.2"

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
        if getattr(self.settings, "SCHEDULE_PARTY_DUNGEON", ""):
            monitors.append(MonitorType.PARTY_DUNGEON)
        if getattr(self.settings, "SCHEDULE_SCHEDULE", ""):
            monitors.append(MonitorType.SCHEDULE)
        if getattr(self.settings, "SCHEDULE_AUCTION", ""):
            monitors.append(MonitorType.AUCTION)

        return monitors

    async def main_loop(self) -> None:
        window_id = self.window_id
        log(f"Запуск профиля {self.profile_name} {self.profile_version}", window_id)

        hunt = await self.combat.is_autohunt_on()
        if not hunt:
            energo = await self.energo.is_on()
            if energo:
                await self.energo.turn_off()
            rip, btn = await self.combat.is_dead()
            if not rip:
                to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT, self.settings.SPOT_DO)
                if to_spot:
                    self.runtime_data.current_state = BotState.COMBAT
        if hunt:
            self.runtime_data.current_state = BotState.COMBAT

        self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
        self._event_worker_task = asyncio.create_task(self._event_worker())

        while self.running:
            if self._event_worker_task.done():
                log("Event worker умер, перезапускаю", window_id)
                self._event_worker_task = asyncio.create_task(self._event_worker())
            await asyncio.sleep(1)

    async def on_stop(self) -> None:
        window_id = self.window_id
        log("dodger stopped =(", window_id)
        self.events_checker.stop_monitoring(window_id)
        self.running = False
        if self._event_worker_task:
            self._event_worker_task.cancel()
        if self._current_event_task:
            self._current_event_task.cancel()
        await super().on_stop()

    async def respawn_buy(self):
        window_id = self.window_id
        log("Респавнюсь + посплю + выкуплю шмоточки", window_id)
        async with self.paused_monitors():
            respawned = await self.combat.respawn()
            if respawned:
                log("Стопнул мониторинг новых ивентов на время сна", window_id)
                await asyncio.sleep(10) #todo
                await self.energo.turn_on()
                await asyncio.sleep(1)

                await asyncio.sleep(random.uniform(self.settings.MIN_SLEEP_AFTER_RIP, self.settings.MAX_SLEEP_AFTER_RIP))
                log("Поспал, пробую выкупить опыт и шмотки", window_id)
                if await self.energo.is_on():
                    await self.energo.turn_off()
                    await asyncio.sleep(1)

                if self.settings.BUY_LOOT_RIP:
                    buyed = await self.town.buy_loot(clr=False)
                    if buyed:
                        log("Что-то выкупил..", window_id)

                if self.settings.NEED_SHOP_AFTER_RIP:
                    log("Пробую идти к бакалейщику", window_id)
                    stash_ok, in_town, npcs = await self.town.go_stash()
                    shop_ok, _, _ = await self.town.buy_in_shop(in_town=in_town, npcs=npcs)
                    buyer_ok, _, _ = await self.town.sell_to_buyer(in_town=in_town, npcs=npcs)
                    if stash_ok:
                        log("Успешно скупился!", window_id)

                await asyncio.sleep(1)
                log("Тпаюсь на спот и ставлю автобой", window_id)
                #todo сунуть проверку телепорт свитков
                to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT, self.settings.SPOT_DO)
                if to_spot:
                    self.runtime_data.current_state = BotState.COMBAT
                    return True
                else:
                    #todo почему автобой не включился?
                    self.notify_screenshot("Шось пошло не так, не тпнулся на спот либо не включился автобой?")
                    return
            else:
                log("Не респавнулся, жду повторного ивента", window_id)
                await asyncio.sleep(4)

    async def buying(self):
        window_id = self.window_id
        log("Начал закупаться по расписанию!", window_id)
        await self.bank_restore()

    async def back_to_spot(self):

        window_id = self.window_id
        if self.runtime_data.current_state == BotState.COMBAT:
            return True
        log("Пробую вернуться на спот", window_id)
        self.events_checker.stop_monitoring(window_id)
        energo = await self.energo.is_on()
        if energo:
            await self.energo.turn_off()

        if self.settings.NEED_SHOP_AFTER_PVP_EVADE:
            stash_ok, in_town, npcs = await self.town.go_stash()
            shop_ok, _, _ = await self.town.buy_in_shop(in_town=in_town, npcs=npcs, check_loot=True)
            buyer_ok, _, _ = await self.town.sell_to_buyer(in_town=in_town, npcs=npcs)

            if stash_ok:
                log("Закупился успешно, вероятно...", window_id)

        await asyncio.sleep(2.5)
        to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT, self.settings.SPOT_DO)
        self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
        if to_spot:
            self.runtime_data.current_state = BotState.COMBAT

            self.runtime_data.update_last_return()
            return True
        return to_spot

    async def dodge(self) -> None:
        self.runtime_data.set_state(BotState.PVP)
        window_id, window = self.window_id, self.window_info[self.window_id]
        self.events_checker.stop_monitoring(window_id)
        if not self.settings.FAST_DODGE and self.settings.LOW_HP_DODGE:
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
        running = self.events_checker.get_running(window_id)
        if MonitorType.HEALTH in running:
            self.events_checker.stop_once(window_id, MonitorType.HEALTH)

        pixel = await self.check_pixel(xy2, rgb2, 7)
        if pixel:
            log(f"Контрольный тп вжат", window_id)
            await self.mouse.click(self.window_info, xy2[0], xy2[1], fast=True)
            await asyncio.sleep(1)
        else:
            log(f"rip? or no?", window_id)
            rip, btn = await self.combat.is_dead()
            if rip:
                log("rly rip", window_id)
                self.runtime_data.current_state = BotState.DEATH
                x = True
                return

        result = await self.tp.wait_arrived()
        if result and not x:
            sleept = randint(self.settings.MIN_PVP_DODGE_SLEEP, self.settings.MAX_PVP_DODGE_SLEEP)
            await self.energo.turn_on()
            log(f"Сплю {sleept} сек.", window_id)
            self.runtime_data.update_last_succ_dodge()
            self.runtime_data.current_state = BotState.AFK
            self.runtime_data.spot_time = (datetime.now() + timedelta(seconds=sleept)).strftime("%H:%M:%S")
            self.notify(NotifyLevel.WARNING, "Задоджил пвп успешно")
        else:
            self.notify(NotifyLevel.WARNING, "Не смог доджнуть пвп, втф?")
            self.notify_screenshot("Не смог доджнуть пвп, #важно")

            log(f"bad result? | dodger | pvp tp | rip?", window_id)
            log(f"bad result? | dodger | pvp tp | {result}", window_id)
            rip, btn = await self.combat.is_dead()
            if rip:
                log("rly rip", window_id)
                self.runtime_data.current_state = BotState.DEATH

    async def bank_restore(self):
        window_id, window = self.window_id, self.window_info[self.window_id]
        async with self.paused_monitors():
            rip, btn = await self.combat.is_dead()
            if rip:
                self.runtime_data.current_state = BotState.DEATH
                return

            self.runtime_data.current_state = BotState.SHOPPING
            xy, rgb = parseCBT("home_scroll_button_energomode", profile=self)

            click_x = xy[0]
            click_y = xy[1]
            await self.mouse.click(self.window_info, click_x, click_y)
            result = await self.tp.wait_arrived()
            if result:
                stash_ok, in_town, npcs = await self.town.go_stash()
                shop_ok, _, _ = await self.town.buy_in_shop(in_town=in_town, npcs=npcs, check_loot=True)
                buyer_ok, _, _ = await self.town.sell_to_buyer(in_town=in_town, npcs=npcs)

                if stash_ok:
                    to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT, self.settings.SPOT_DO)
                    if to_spot:
                        self.runtime_data.current_state = BotState.COMBAT
                        self.notify(NotifyLevel.TRASH, "Закупился успешно")
                        return True
                else:
                    log(f"bad result? {result} / buy", window_id)
                    town = await self.town.is_in()
                    if town:
                        #todo
                        to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT,
                                                                self.settings.SPOT_DO)
                        if to_spot:
                            self.runtime_data.current_state = BotState.COMBAT
                            return True
                    else:
                        self.notify_screenshot(f"Шось пошло не так в bank_restore\n\nСтеш: {stash_ok}\nГород: {town}")
            else:
                log(f"/ bad result? {result} / else", window_id)
                rip, btn = await self.combat.is_dead()
                if rip:
                    log("Помер мгновенно как приехал на спот, бувае...", window_id)


    async def mail(self):
        window_id, window = self.window_id, self.window_info[self.window_id]
        cstate = self.runtime_data.current_state
        if cstate == BotState.DEATH:
            return
        self.runtime_data.current_state = BotState.CLAIMING
        async with self.paused_monitors():
            log("Не мониторю новые события во время почты", window_id)
            claimed_mail = await self.claims.mail()
            if claimed_mail:
                log(f"Почта успешно собрана", window_id)
                self.notify(NotifyLevel.TRASH, "Собрал почту")
            else:
                log(f"Нет новой почты или не удалось собрать", window_id)

            if not await self.energo.is_on():
                if cstate != BotState.DEATH:
                    await self.energo.turn_on()
                    self.runtime_data.current_state = cstate
                    return True
                else:
                    self.runtime_data.set_state(BotState.DEATH) #wtf если смерть уже была, ну пох

            await asyncio.sleep(1)

    async def rewards(self):
        #print(1)
        window_id, window = self.window_id, self.window_info[self.window_id]
        cstate = self.runtime_data.current_state
        #print(cstate)
        if cstate == BotState.DEATH:
            #print(cstate)
            return
        self.events_checker.stop_monitoring(window_id)
        self.runtime_data.current_state = BotState.CLAIMING
        log("Не мониторю новые события во время сборов", window_id)
        await asyncio.sleep(1)

        if self.settings.NEED_CLAIM_DAILY:
            claimed_daily = await self.claims.daily()
            if claimed_daily:
                log(f"Дейлик успешно собран", window_id)
            else:
                log(f"Нет новых дейликов или не удалось собрать", window_id)

        if self.settings.NEED_CLAIM_MAIL:
            claimed_mail = await self.claims.mail()
            if claimed_mail:
                log(f"Почта успешно собрана", window_id)
            else:
                log(f"Нет новой почты или не удалось собрать", window_id)

        if self.settings.NEED_CLAIM_ACHIV:
            claimed_achiv = await self.claims.achievements()
            if claimed_achiv:
                log(f"Ачивы успешно собраны", window_id)
            else:
                log(f"Нет новых ачивок или не удалось собрать", window_id)

        if self.settings.NEED_CLAIM_CLAN:
            claimed_clan = await self.claims.clan()
            if claimed_clan:
                log(f"Клан успешно собран", window_id)
            else:
                log(f"Нет новых донатов в клан или не удалось вдонить", window_id)

        if self.settings.NEED_CLAIM_ALI:
            claim_ali = await self.claims.alliance()
            if claim_ali:
                log(f"Альянс успешно собран", window_id)
            else:
                log(f"Не смог собрать альянс", window_id)

        if self.settings.NEED_CLAIM_BATTLE_PASS:
            claimed_bp = await self.claims.battle_pass()
            if claimed_bp:
                log(f"Пасс успешно собран", window_id)
            else:
                log(f"Не смог собрать пасс", window_id)

        if self.settings.NEED_CLAIM_DONATE_SHOP:
            claimed_shop = await self.claims.donate_shop()
            if claimed_shop:
                log(f"Шоп успешно собран", window_id)
            else:
                log(f"Не смог собрать шоп", window_id)

        self.notify(NotifyLevel.TRASH, "Собрал награды по расписанию")

        if not await self.energo.is_on():
            if cstate != BotState.DEATH:
                await self.energo.turn_on()
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
        window_id, window = self.window_id, self.window_info[self.window_id]
        cstate = self.runtime_data.current_state
        #print(cstate)
        if cstate == BotState.DEATH:
            #print(cstate)
            return
        async with self.paused_monitors():
            self.runtime_data.current_state = BotState.SCHEDULE
            if await self.energo.is_on():
                await self.energo.turn_off()
                await asyncio.sleep(1)

            sch = await self.scheduler.start()
            if sch is None:
                log("Не смог стартануть расписание, полный инвентарь либо оно не настроено, улетаю на спот.", window_id)
                to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT,
                                                        self.settings.SPOT_DO)
                if to_spot:
                    self.runtime_data.current_state = BotState.COMBAT
                    return True
                else:
                    log("wtf?___", window_id)

            if sch is True:
                farm = 0
                log("Расписание началось", window_id)
                while self.settings.is_schedule_schedule():
                    log(f"Расписание уже идет, прошло {farm} сек.", window_id)
                    farm += 300
                    await asyncio.sleep(300)

                log("Расписание кончилось", window_id)
                await self.scheduler.stop()
                if await self.energo.is_on():
                    await self.energo.turn_off()
                    await asyncio.sleep(1)
                tp = await self.tp.safe_home()
                if tp:
                    stash_ok, in_town, npcs = await self.town.go_stash()
                    shop_ok, _, _ = await self.town.buy_in_shop(in_town=in_town, npcs=npcs)
                    buyer_ok, _, _ = await self.town.sell_to_buyer(in_town=in_town, npcs=npcs)
                    to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT, self.settings.SPOT_DO)
                    if to_spot:
                        self.runtime_data.current_state = BotState.COMBAT
                        return True

                log("wtf?", window_id)
                self.runtime_data.current_state = BotState.AFK

    async def overweight_check(self):
        window_id, window = self.window_id, self.window_info[self.window_id]
        runtime = self.runtime_data
        afk_threshold = self.settings.OVERWEIGHT_AFK
        current_level = runtime.overweight.value

        to_notify = runtime.need_notify()
        if to_notify is not None:
            log(f"Перевес изменился: {runtime.last_overweight.value} -> {current_level}",
                window_id)
            self.notify(
                NotifyLevel.INFO if current_level < afk_threshold else NotifyLevel.WARNING,
                f"Перевес окна: {current_level}",
            )

        if current_level >= afk_threshold and runtime.current_state != BotState.AFK:
            runtime.set_state(BotState.AFK)
            async with self.paused_monitors():
                log(f"Перевес достиг порога, переводим в афк: {current_level}", window_id)
                tped = await self.tp.safe_home()
                if tped:
                    await self.tp.wait_arrived()
                    await self.energo.turn_on()
                    await asyncio.sleep(4)
                    self.notify_screenshot("Дошли до порога перевеса, стоим в городе афк #важно\nРекомендую сгрузить мусор и перезапустить окно через тг бота")

    async def pvp_answer(self):
        window_id, window = self.window_id, self.window_info[self.window_id]
        wait_d = self.settings.DELAY_PVP_ANSWER
        log(f"Пробую ответить на пвп, таймаут: {wait_d} сек.", window_id)

        self.events_checker.stop_monitoring(window_id)
        self.runtime_data.set_state(BotState.PVP)
        xy, rgb = parseCBT("pvp_energo_trigger", profile=self)
        click_x, click_y = xy
        await self.mouse.click(self.window_info, click_x, click_y, fast=True)

        self.events_checker.start_monitoring(window_id, self,
                                             monitors=[MonitorType.HEALTH,
                                                       MonitorType.DEATH])

        wait = await self.tp.wait_arrived(need=1)
        if not wait:
            log("wtf? not wait pvp answer unblock", window_id)
            self.events_checker.stop_monitoring(window_id)
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            return

        for x in range(wait_d * 10):
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
                            rip, btn = await self.combat.is_dead()
                            if rip:
                                log("rly rip", window_id)
                                self.runtime_data.current_state = BotState.DEATH
                                return

                        tped = await self.tp.wait_arrived()
                        if tped:
                            sleept = randint(3, 5)
                            self.runtime_data.current_state = BotState.AFK
                            self.runtime_data.spot_time = (datetime.now() + timedelta(
                                minutes=sleept)).strftime("%H:%M:%S")
                            log(f"Вроде как ушел от пвп, сплю {sleept} мин.", window_id)
                            self.events_checker.stop_monitoring(window_id)
                            self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                            await asyncio.sleep(1)
                            await self.energo.turn_on()
                            self.notify(NotifyLevel.WARNING, "Задоджил пвп успешно (после попытки ответа)")
                            return
                    else:
                        log("Вероятно, погиб?", window_id)
                        rip, btn = await self.combat.is_dead()
                        if rip:
                            log("rly rip", window_id)
                            self.runtime_data.current_state = BotState.DEATH
                            return

            if await self.combat.has_adena():
                log(f"Пвп успешно завершено", window_id)
                await asyncio.sleep(1)
                break

            await asyncio.sleep(0.1)

        rip, btn = await self.combat.is_dead()
        if rip:
            log(f"{rip} | Сдох после попытки ответа, мда", window_id)
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            return

        log(f"Мы живы! Посмотрю на хп пару секунд и вернусь на спот.", window_id)
        curr_h = self.runtime_data.health
        for _ in range(self.settings.PVP_ANSWER_CHECK_HP_ITERATIONS):
            hlt = self.runtime_data.health
            hp_diff = curr_h - hlt
            diff = (hp_diff / curr_h) * 100

            rip, _ = await self.combat.is_dead()
            log(f"data|{curr_h}|{hlt}|{hp_diff}|{rip}", window_id)
            if rip:
                log("Смерть во время проверок хп, итс овер...", window_id)
                self.runtime_data.current_state = BotState.DEATH
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
                        current = time.time()
                        last_death = self.events_checker.get_last_timestamp(window_id,
                                                                            "death")
                        if last_death is not None and current - last_death <= 20:
                            self.runtime_data.current_state = BotState.DEATH
                            log(f"rip!", window_id)
                            return

                    tped = await self.tp.wait_arrived()
                    if tped:
                        sleept = randint(3, 5)
                        self.runtime_data.current_state = BotState.AFK
                        self.runtime_data.spot_time = (datetime.now() + timedelta(
                            minutes=sleept)).strftime("%H:%M:%S")
                        log(f"Вроде как ушел от пвп, сплю {sleept} мин.", window_id)
                        self.events_checker.stop_monitoring(window_id)
                        self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
                        await asyncio.sleep(1)
                        await self.energo.turn_on()
                        self.notify(NotifyLevel.WARNING, "Задоджил пвп успешно (после попытки ответа2)")
                        return
                else:
                    log("Вероятно, погиб?", window_id)
                    rip, btn = await self.combat.is_dead()
                    if rip:
                        log("rly rip", window_id)
                        self.runtime_data.current_state = BotState.DEATH
                        return

            await asyncio.sleep(0.1)
        log("exited", window_id)
        rip, btn = await self.combat.is_dead()
        if rip:
            log(f"{rip} | Сдох после попытки ответа, мда2", window_id)
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            return

        self.events_checker.stop_monitoring(window_id)
        to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT,
                                                self.settings.SPOT_DO)
        if to_spot:
            self.runtime_data.current_state = BotState.COMBAT
            self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)
            self.notify(NotifyLevel.WARNING, "Успешно завершил пвп, вероятно кого-то убил?")
        else:
            log("Не смог тпнуться на спот, если включено тг - смотри скриншот.")
            await asyncio.sleep(4)
            self.notify_screenshot("После ответа пвп не смог тпнуться на спот, #важно")
            self.events_checker.start_monitoring(window_id, self,
                                                 monitors=self.get_monitors)
            return

    async def handle_auction(self):
        window_id, window = self.window_id, self.window_info[self.window_id]
        cstate = self.runtime_data.current_state
        if cstate == BotState.DEATH:
            return
        self.runtime_data.current_state = BotState.CLAIMING
        self.events_checker.stop_monitoring(window_id)
        log("Не мониторю новые события во время перевыставления аука", window_id)
        if await self.energo.is_on():
            await self.energo.turn_off()

        rereg = await self.auction.reregister()

        if not await self.energo.is_on():
            await self.energo.turn_on()

        if rereg:
            log(f"Аук успешно перевыставлен!", window_id)
            self.notify(NotifyLevel.TRASH, "Перевыставил аук")
        else:
            log(f"Не смог перевыставить аук", window_id)

        self.runtime_data.current_state = cstate
        self.events_checker.start_monitoring(window_id, self,
                                             monitors=self.get_monitors)
        if not await self.energo.is_on():
            if cstate != BotState.DEATH:
                await self.energo.turn_on()
                return True

        await asyncio.sleep(1)
        return True

    _ERROR_METHOD_MAP = {
        "connect_to_server": "connect",
        "close_ethernet1_error": "close_ethernet1",
        "close_ethernet2_error": "close_ethernet2",
    }

    async def handle_error(self, desc):
        window_id = self.window_id
        f = desc.value
        method_name = self._ERROR_METHOD_MAP.get(f)
        func = getattr(self.errors, method_name, None) if method_name else None

        if func:
            self.events_checker.stop_monitoring(window_id)
            result = await func()
            if result:
                self.runtime_data.set_state(BotState.AFK)
                if desc == ErrorTypes.ETHERNET2_ERROR:
                    res2 = await self.errors.connect()
                    if res2:
                        self.runtime_data.spot_time = (datetime.now() + timedelta(
                            minutes=3)).strftime("%H:%M:%S")

                        await self.energo.turn_on()
                    else:
                        self.notify_screenshot("Чет супер злое после попытки подрубиться на сервер")

                elif desc == ErrorTypes.ETHERNET_ERROR:
                    if self.runtime_data.current_state == BotState.COMBAT:
                        await asyncio.sleep(2)
                        await self.energo.turn_on()

                self.events_checker.start_monitoring(window_id, self,
                                                     monitors=self.get_monitors)
                return
            else:
                self.notify_screenshot(f"Чет злое в обработке ошибок #важно | {f}")
        else:
            log(f"{f}", window_id)
            return

    async def party(self):
        window_id, window = self.window_id, self.window_info[self.window_id]
        try:
            async with self.paused_monitors():
                rip, btn = await self.combat.is_dead()
                if rip:
                    log("Окно сдохло, пати данжа не буде =(", window_id)
                    return

                flaged = False
                energo = await self.energo.is_on()
                if energo:
                    flaged = True
                    #await self.energo.turn_off()
                    await asyncio.sleep(0.1)

                self.runtime_data.current_state = BotState.AFK
                await self.tp.safe_home()
                await asyncio.sleep(1.5)
                await self.tp.wait_arrived()
                dungeon = PartyDungeon(self)
                await dungeon.party_create()
                await asyncio.sleep(0.5)
                await dungeon.open_dungeon()
                await asyncio.sleep(1.5)
                xy = await dungeon.find_dungeon()
                if not xy:
                    log("Не нашел данжик, выхожу", window_id)
                    await dungeon.wait_and_click("main_menu_gui")
                    await asyncio.sleep(1.8)
                    await dungeon.party_leave()
                    if flaged:
                        await self.energo.turn_on()

                    await self.back_to_spot()
                    return

                started = await dungeon.start_dungeon(xy)
                if not started:
                    log("Данж не стартанул, выхожу из пати", window_id)
                    await dungeon.party_leave()
                    await self.back_to_spot()
                    return

                if started:
                    await self.combat.toggle_autohunt()
                    to_back = await dungeon.no_limit() # энерго включено клики в dungeon.cliks
                    self.events_checker.start_monitoring(window_id, self, monitors=[MonitorType.DEATH])
                    log(to_back, window_id)
                    while True:
                        hunt = await self.combat.is_autohunt_on()
                        log(hunt, window_id)
                        if not hunt:
                            self.events_checker.stop_monitoring(window_id)
                            rip, btn = await self.combat.is_dead()
                            if rip:
                                log("Анлука, помер во время пати данжа. оффаюсь", window_id)
                                return

                            break

                        await asyncio.sleep(10)

                    log("Успешно пробежал пати данжик закуплюсь и оффаюсь", window_id)
                    if await self.energo.is_on():
                        await self.energo.turn_off(ignore=True)
                        await asyncio.sleep(1)

                        self.notify_screenshot("Закачал пати данжик, закуплюсь и оффнусь =)")

                    await self.mouse.click(self.window_info, 200, 100)

                    await dungeon.to_start()
                    await dungeon.party_leave()

                    ok, in_town, npcs = await self.town.buy_in_shop()
                    log(f"ok={ok}, town={in_town}", window_id)
                    if not await self.energo.is_on():
                        await self.energo.turn_on()
                        await asyncio.sleep(1)

                    rip, btn = await self.combat.is_dead()
                    if not rip:
                        to_spot = await self.tp.to_random_spot(self.settings.SPOT_OT,
                                                                self.settings.SPOT_DO)
                        if to_spot:
                            self.runtime_data.current_state = BotState.COMBAT
                            return True

                    return False

        except asyncio.CancelledError:
            log("Профиль остановлен вручную", window_id)
            raise

    async def lowhp_zatichka(self):
        window_id, window = self.window_id, self.window_info[self.window_id]
        log(f"curr hp: {self.runtime_data.health}", window_id)
        xy, rgb = parseCBT("home_scroll_button_energomode", profile=self)
        self.events_checker.stop_once(window_id, MonitorType.LOW_HP_DODGE)
        self.events_checker.stop_once(window_id, MonitorType.HEALTH)
        click_x = xy[0]
        click_y = xy[1]
        await self.mouse.click(self.window_info, click_x, click_y)
        result = await self.tp.wait_arrived()
        if result:
            sleept = uniform(self.settings.MIN_LOW_HP_DODGE_SLEEP, self.settings.MAX_LOW_HP_DODGE_SLEEP)
            await self.energo.turn_on()
            log(f"Сплю {sleept} сек.", window_id)
            #self.runtime_data.update_last_succ_dodge()
            self.runtime_data.current_state = BotState.AFK
            self.runtime_data.spot_time = (datetime.now() + timedelta(seconds=sleept)).strftime("%H:%M:%S")
            self.notify(NotifyLevel.WARNING, f"Мало хп, улетел со спота\nПосплю {sleept} сек.")
        else:
            self.events_checker.start_monitoring(window_id, self, monitors=self.get_monitors)

    EVENT_HANDLERS = {
        MonitorType.PVP: "_handle_pvp",
        MonitorType.LOW_HP_DODGE: "lowhp_zatichka",
        MonitorType.HP_BANK: "bank_restore",
        MonitorType.SOSKA: "bank_restore",
        MonitorType.DEATH: "respawn_buy",
        MonitorType.SPOT_BACK: "back_to_spot",
        MonitorType.SELL_STASH_BUY: "buying",
        MonitorType.CLAIM_MAIL: "mail",
        MonitorType.CLAIM_REWARDS: "rewards",
        MonitorType.PARTY_DUNGEON: "party",
        MonitorType.SCHEDULE: "schedule_schedule",
        MonitorType.OVERWEIGHT: "overweight_check",
        MonitorType.AUCTION: "handle_auction",
    }

    async def _handle_pvp(self):
        if self.settings.PVP_EVADE:
            await self.dodge()
        elif self.settings.PVP_ANSWER:
            await self.pvp_answer()
