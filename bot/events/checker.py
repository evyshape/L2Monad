import asyncio
import time
from typing import Dict
import numpy as np

from bot.clogger import log
from bot.delays import (
    CHECKS_HP_BANK,
    CHECKS_HP_BANK_TRIGGER,
    CHECKS_HP_BANK_TIMEOUT,
    PVP_CHECK_DELAY,
)
from bot.misc import CHECK_DISCONNECT_ERROR, CHECK_ETHERNET1_ERROR
from bot.events.events import EventsManager
from bot.events.enums import MonitorType, OverWeight, ErrorTypes, ScheduleAction, BotState
from bot.methods.base import parseCBT
from profiles.base import BaseProfile


class EventsChecker:
    def __init__(self):
        self.tasks: Dict[str, Dict[MonitorType, asyncio.Task]] = {}
        self._last_event_time: Dict[str, Dict[str, float]] = {}
        self._last_time: Dict[str, Dict[str, int | None]] = {}
        self.tname = "-EventsChecker-"

    def get_last_timestamp(self, window_id: str, event_type: str) -> int | None:
        return self._last_time.get(window_id, {}).get(event_type)

    async def _monitor_pvp(self, window_id: str, profile: BaseProfile) -> None:
        xy, rgb = parseCBT("pvp_energo_trigger", profile=profile)

        while profile.running:
            try:
                found = await profile.check_pixel(xy, rgb, timeout=PVP_CHECK_DELAY, thr=2)

                if found:
                    now = time.monotonic()
                    last_events = self._last_event_time.setdefault(window_id, {})
                    last_time = last_events.get(MonitorType.PVP, 0)

                    if now - last_time >= 20:
                        EventsManager.send_event(window_id, {"type": MonitorType.PVP})
                        log(f"ПВП ивент отправлен в {window_id}", self.tname)
                        last_events[MonitorType.PVP] = now

                    await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor pvp error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_hp_bank(self, window_id: str, profile: BaseProfile) -> None:
        if profile.runtime_data.has_quiver is None:
            quiver_status = await profile.energo.has_quiver()
            profile.runtime_data.has_quiver = quiver_status

        if profile.runtime_data.has_quiver is True:
            xy, rgb = parseCBT("q_hp_bank_in_energo", profile=profile)
        elif profile.runtime_data.has_quiver is False:
            xy, rgb = parseCBT("hp_bank_in_energo", profile=profile)
        else:
            xy, rgb = parseCBT("hp_bank_in_energo", profile=profile)

        while profile.running:
            try:
                checks = 0
                #print(1)
                for _ in range(CHECKS_HP_BANK):
                    found = await profile.check_pixel(xy, rgb, timeout=CHECKS_HP_BANK_TIMEOUT, thr=9)
                    if found:
                        checks += 1

                    await asyncio.sleep(2)

                if checks >= CHECKS_HP_BANK_TRIGGER:
                    now = time.monotonic()
                    last_events = self._last_event_time.setdefault(window_id, {})
                    last_time = last_events.get(MonitorType.HP_BANK, 0)
                    #print(2)
                    if now - last_time >= 60:
                        EventsManager.send_event(window_id, {"type": MonitorType.HP_BANK})
                        log(f"Хп банка ивент отправлен в {window_id}", self.tname)
                        last_events[MonitorType.HP_BANK] = now


                await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor hp_bank error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_soska(self, window_id: str, profile: BaseProfile) -> None:
        if profile.runtime_data.has_quiver is None:
            quiver_status = await profile.energo.has_quiver()
            profile.runtime_data.has_quiver = quiver_status

        if profile.runtime_data.has_quiver is True:
            xy, rgb = parseCBT("q_soska_in_energo", profile=profile)
        elif profile.runtime_data.has_quiver is False:
            xy, rgb = parseCBT("soska_in_energo", profile=profile)
        else:
            xy, rgb = parseCBT("soska_in_energo", profile=profile)

        while profile.running:
            try:
                checks = 0
                # print(1)
                for _ in range(4):
                    found = await profile.check_pixel(xy, rgb, timeout=0.3, thr=7, wsize="1x1")
                    # print(found)
                    if found:
                        checks += 1

                    await asyncio.sleep(1)

                if checks >= 3:
                    now = time.monotonic()
                    last_events = self._last_event_time.setdefault(window_id, {})
                    last_time = last_events.get(MonitorType.SOSKA, 0)
                    # print(2)
                    if now - last_time >= 60:
                        EventsManager.send_event(window_id, {"type": MonitorType.SOSKA})
                        log(f"Соска ивент отправлен в {window_id}", self.tname)
                        last_events[MonitorType.SOSKA] = now

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor soska error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_death(self, window_id: str, profile: BaseProfile) -> None:
        while profile.running:
            try:
                death_found, btn = await profile.combat.is_dead()
                if death_found and btn != "":
                    now_monotonic = time.monotonic()
                    now_ts = int(time.time())
                    now = now_monotonic
                    last_events = self._last_event_time.setdefault(window_id, {})
                    last_time = last_events.get(MonitorType.DEATH, 0)

                    if now - last_time >= 60:
                        #print(death_found)
                        #print(btn)
                        EventsManager.send_event(window_id, {"type": MonitorType.DEATH})
                        log(f"DEATH ивент отправлен в {window_id}", self.tname)
                        last_events[MonitorType.DEATH] = now_monotonic
                        self._last_time.setdefault(window_id, {})[MonitorType.DEATH] = now_ts

                    await asyncio.sleep(6)
                else:
                    await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor death error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_spot_back(self, window_id: str, profile: BaseProfile) -> None:
        while profile.running:
            try:
                if (
                        profile.runtime_data.current_state not in [BotState.COMBAT, BotState.DEATH]
                        and profile.runtime_data.spot_time
                        and profile.runtime_data.time_to_back()
                ):
                    now = time.monotonic()
                    last_events = self._last_event_time.setdefault(window_id, {})
                    last_time = last_events.get(MonitorType.SPOT_BACK, 0)

                    if now - last_time >= 60:
                        EventsManager.send_event(window_id, {"type": MonitorType.SPOT_BACK})
                        profile.runtime_data.spot_time = None
                        log(f"SPOT_BACK ивент отправлен в {window_id}", self.tname)
                        last_events[MonitorType.SPOT_BACK] = now

                await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor spot_back error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_sell_stash_buy(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            try:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get(MonitorType.SELL_STASH_BUY, 0)

                buying = profile.settings.is_schedule(ScheduleAction.BUYING, window_id)

                if buying and now - last_time >= 240:
                    EventsManager.send_event(window_id, {"type": MonitorType.SELL_STASH_BUY})
                    log(f"SELL_STASH_BUY ивент отправлен в {window_id}", self.tname)

                    last_events[MonitorType.SELL_STASH_BUY] = now

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor sell_stash_buy error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_mail(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            try:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get(MonitorType.CLAIM_MAIL, 0)

                mail = profile.settings.is_schedule(ScheduleAction.MAIL, window_id)

                if mail and now - last_time >= 240:
                    EventsManager.send_event(window_id, {"type": MonitorType.CLAIM_MAIL})
                    log(f"MAIL ивент отправлен в {window_id}", self.tname)

                    last_events[MonitorType.CLAIM_MAIL] = now

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor mail error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_party(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            try:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get(MonitorType.PARTY_DUNGEON, 0)

                party_dungeon = profile.settings.is_schedule(ScheduleAction.PARTY_DUNGEON, window_id)

                if party_dungeon and now - last_time >= 120:
                    EventsManager.send_event(window_id, {"type": MonitorType.PARTY_DUNGEON})
                    log(f"PARTY ивент отправлен в {window_id}", self.tname)

                    last_events[MonitorType.PARTY_DUNGEON] = now

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor party error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_auction(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            try:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get(MonitorType.AUCTION, 0)

                auc = profile.settings.is_schedule(ScheduleAction.AUCTION, window_id)

                if auc and now - last_time >= 240:
                    EventsManager.send_event(window_id, {"type": MonitorType.AUCTION})
                    log(f"AUCTION ивент отправлен в {window_id}", self.tname)

                    last_events[MonitorType.AUCTION] = now

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor auction error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_rewards(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            try:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get(MonitorType.CLAIM_REWARDS, 0)

                rewards = profile.settings.is_schedule(ScheduleAction.REWARDS, window_id)

                if rewards and now - last_time >= 240:
                    EventsManager.send_event(window_id, {"type": MonitorType.CLAIM_REWARDS})
                    log(f"REWARDS ивент отправлен в {window_id}", self.tname)

                    last_events[MonitorType.CLAIM_REWARDS] = now

                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor rewards error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_schedule_schedule(self, window_id: str, profile: BaseProfile) -> None:
        while profile.running:
            try:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get(MonitorType.SCHEDULE, 0)
                schedule = profile.settings.get_schedule_schedule()
                if schedule and now - last_time >= 240:
                    EventsManager.send_event(window_id, {"type": MonitorType.SCHEDULE})
                    log(f"schedule ивент отправлен в {window_id}", self.tname)
                    last_events[MonitorType.SCHEDULE] = now

                await asyncio.sleep(30)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor schedule error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_overweight(self, window_id: str, profile: BaseProfile):
        if profile.runtime_data.has_quiver is None:
            profile.runtime_data.has_quiver = await profile.energo.has_quiver()

        coords = {
            OverWeight.ZERO: "q_pereves0" if profile.runtime_data.has_quiver else "pereves0",
            OverWeight.FIFTY: "q_pereves2" if profile.runtime_data.has_quiver else "pereves2",
            OverWeight.EIGHTY: "q_pereves1" if profile.runtime_data.has_quiver else "pereves1",
        }

        while profile.running:
            try:
                detected_level = OverWeight.ZERO

                for level in [OverWeight.EIGHTY, OverWeight.FIFTY,
                              OverWeight.ZERO]:

                    cb_key = coords[level]
                    xy, rgb = parseCBT(cb_key, profile=profile)
                    found = await profile.check_pixel(xy, rgb, timeout=4, thr=0)
                    if found:
                        detected_level = level
                        break

                    await asyncio.sleep(5)

                profile.runtime_data.update_overweight(detected_level)
                to_notify = profile.runtime_data.need_notify()

                if to_notify is not None:
                    now = time.monotonic()
                    last_events = self._last_event_time.setdefault(window_id, {})
                    last_time = last_events.get(MonitorType.OVERWEIGHT, 0)
                    if now - last_time >= 30:
                        EventsManager.send_event(window_id, {"type": MonitorType.OVERWEIGHT})
                        last_events[MonitorType.OVERWEIGHT] = now

                await asyncio.sleep(50)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor overweight error: {e}", self.tname)
                await asyncio.sleep(5)

    async def _monitor_health(self, window_id: str, profile: BaseProfile) -> None:
        bars = [
            ((10, 9), (69, 9)),
            ((10, 8), (69, 8))
        ]

        x_min = min(x1 for (x1, _), _ in bars)
        x_max = max(x2 for _, (x2, _) in bars)
        y_min = min(y1 for (_, y1), _ in bars)
        y_max = max(y2 for _, (_, y2) in bars)

        width = abs(x_max - x_min) + 1
        height = abs(y_max - y_min) + 1
        rect = (x_min, y_min, width, height)

        t1 = np.array([160, 40, 10], dtype=np.int16)
        t2 = np.array([30, 30, 20], dtype=np.int16)
        t3 = np.array([57, 18, 8], dtype=np.int16)
        t4 = np.array([10, 10, 5], dtype=np.int16)

        while profile.running:
            try:
                [screenshot] = await profile.capture_multy([rect])
                img_i16 = screenshot.astype(np.int16)

                mask1 = np.all(np.abs(img_i16 - t1) <= t2, axis=-1)
                mask2 = np.all(np.abs(img_i16 - t3) <= t4, axis=-1)
                mask = mask1 | mask2

                re = np.mean(mask, axis=0)
                red = np.where(re > 0.4)[0]

                if len(red) > 0:
                    hpe = red[-1]
                    hp = int((hpe / (width - 1)) * 100)
                    profile.runtime_data.health = hp

                    now = time.monotonic()
                    last_events = self._last_event_time.setdefault(window_id, {})
                    last_time = last_events.get(MonitorType.HEALTH, 0)
                    if now - last_time >= 1:
                        last_events[MonitorType.HEALTH] = now

                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log(f"Monitor health error: {e}", self.tname)
                await asyncio.sleep(5)

    async def low_hp_dodge(self, window_id: str, profile: BaseProfile):
        try:
            window_id, window = next(iter(profile.window_info.items()))
            await asyncio.sleep(0.3)
            if profile.settings.LOW_HP_DODGE:
                if profile.runtime_data.current_state == BotState.COMBAT:
                    self.start_monitoring(window_id, profile, [MonitorType.HEALTH])
                else:
                    return '{"errors": 1, "description": "need combat state before calling this func"}'

                await asyncio.sleep(3)
                hb = profile.settings.HEALTH_BACK
                m = max(hb or [30])
                while profile.runtime_data.current_state == BotState.COMBAT:
                    #log(f"{profile.runtime_data.current_state}", window_id)
                    await asyncio.sleep(0.25)
                    hp = profile.runtime_data.health
                    #log(hp, window_id)
                    if hp == 0:
                        #log(f"[в лоу хп] Хп вероятно еще не получено либо шось сломалось", window_id)
                        await asyncio.sleep(0.05)
                        continue

                    if hp <= m:
                        self.stop_once(window_id, MonitorType.HEALTH)
                        log(f"Больше не терпим, мало хп! | {hp}/{m}", window_id)
                        EventsManager.send_event(window_id, {"type": MonitorType.LOW_HP_DODGE})
                        self.stop_once(window_id, MonitorType.LOW_HP_DODGE)
                    else:
                        #log(f"Терпим, нас ебут а мы крепчаем... | {hp}/{m}", window_id)
                        pass

                await asyncio.sleep(20)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log(f"Monitor low_hp_dodge error: {e}", self.tname)

    async def _check_ethernet_disc_error(self, window_id: str, profile: BaseProfile):
        while profile.running:
            try:
                found = await profile.errors.has_ethernet2()
                if found:
                    EventsManager.send_event(window_id, {
                        "type": MonitorType.ERROR,
                        "desc": ErrorTypes.ETHERNET2_ERROR,
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                log(f"Ошибка в _check_ethernet2_error: {e}", self.tname)
            await asyncio.sleep(60 * 4)

    async def _check_ethernet_error(self, window_id: str, profile: BaseProfile):
        while profile.running:
            try:
                found = await profile.errors.has_ethernet1()
                if found:
                    EventsManager.send_event(window_id, {
                        "type": MonitorType.ERROR,
                        "desc": ErrorTypes.ETHERNET_ERROR,
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                log(f"Ошибка в _check_ethernet_error: {e}", self.tname)
            await asyncio.sleep(60 * 3)

    async def _check_disconnect(self, window_id: str, profile: BaseProfile):
        while profile.running:
            try:
                found = await profile.errors.is_disconnected()
                if found:
                    EventsManager.send_event(window_id, {
                        "type": MonitorType.ERROR,
                        "desc": ErrorTypes.DISCONNECT_TO_MENU,
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                log(f"Ошибка в _check_disconnect: {e}", self.tname)
            await asyncio.sleep(60 * 8)

    async def _monitor_errors(self, window_id: str, profile: BaseProfile) -> None:
        subtasks = []

        if CHECK_ETHERNET1_ERROR:
            subtasks.append(asyncio.create_task(self._check_ethernet_error(window_id, profile)))

        if CHECK_DISCONNECT_ERROR:
            subtasks.append(asyncio.create_task(self._check_disconnect(window_id, profile)))
            subtasks.append(asyncio.create_task(self._check_ethernet_disc_error(window_id, profile)))

        try:
            while profile.running:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
        finally:
            for t in subtasks:
                t.cancel()

    def start_monitoring(self, window_id: str, profile: BaseProfile,
                         monitors: list[MonitorType]) -> None:

        if window_id not in self.tasks:
            self.tasks[window_id] = {}

        ex = self.tasks[window_id]
        checkers = {
            MonitorType.PVP: self._monitor_pvp,
            MonitorType.HP_BANK: self._monitor_hp_bank,
            MonitorType.DEATH: self._monitor_death,
            MonitorType.SPOT_BACK: self._monitor_spot_back,
            MonitorType.SELL_STASH_BUY: self._monitor_sell_stash_buy,
            MonitorType.CLAIM_MAIL: self._monitor_mail,
            MonitorType.CLAIM_REWARDS: self._monitor_rewards,
            MonitorType.SCHEDULE: self._monitor_schedule_schedule,
            MonitorType.SOSKA: self._monitor_soska,
            MonitorType.OVERWEIGHT: self._monitor_overweight,
            MonitorType.HEALTH: self._monitor_health,
            MonitorType.AUCTION: self._monitor_auction,
            MonitorType.ERROR: self._monitor_errors,
            MonitorType.LOW_HP_DODGE: self.low_hp_dodge,
            MonitorType.PARTY_DUNGEON: self._monitor_party
        }

        started = []

        for mtype in monitors:
            if mtype in ex:
                if not ex[mtype].done():
                    continue
                del ex[mtype]

            func = checkers.get(mtype)
            if func:
                task = asyncio.create_task(func(window_id, profile))
                ex[mtype] = task
                started.append(mtype.value)

        if started:
            # da eto jesko
            if len(started) == 1:
                log(f"Чекер {started[0]} запущен для {window_id}", self.tname)
            else:
                joined = " | ".join(started)
                log(f"Чекеры [{joined}] запущены для {window_id}", self.tname)

    # стопает все чекеры для переданного окна
    def stop_monitoring(self, window_id: str) -> None:
        tasks = self.tasks.pop(window_id, {})
        self._last_event_time.pop(window_id, None)
        if not tasks:
            return

        stopped = []

        for mtype, task in tasks.items():
            task.cancel()
            stopped.append(mtype.value)

        if stopped:
            if len(stopped) == 1:
                log(f"Чекер {stopped[0]} остановлен для {window_id}", self.tname)
            else:
                joined = " | ".join(stopped)
                log(f"Чекеры [{joined}] остановлены для {window_id}", self.tname)

    # стопает конкретный переданный чекер для переданного окна
    def stop_once(self, window_id: str, mtype: MonitorType) -> None:
        tasks = self.tasks.get(window_id)
        if not tasks:
            return

        task = tasks.pop(mtype, None)
        if task:
            task.cancel()
            log(f"Чекер {mtype.value} остановлен для {window_id}", self.tname)

        if not tasks:
            self.tasks.pop(window_id, None)

    def get_running(self, window_id: str) -> list[MonitorType]:
        running = []
        monitors = self.tasks.get(window_id, {})
        for mtype, task in monitors.items():
            if not task.done():
                running.append(mtype)
        return running