import asyncio
import time
from typing import Dict
import numpy as np

from bot.clogger import log
from bot.delays import PVP_CHECK_DELAY, CHECKS_HP_BANK, CHECKS_HP_BANK_TRIGGER, CHECKS_HP_BANK_TIMEOUT
from bot.frame_store import FrameStore
from bot.misc import *
from bot.events.events import EventsManager
from bot.events.enums import MonitorType, OverWeight, ErrorTypes
from bot.methods.base import parseCBT
from bot.methods.game import check_rip, find_quiver, check_ethernet1_error, check_disconnect, check_ethernet2_error
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
        store = FrameStore()

        while profile.running:
            ev = store.get_frame_event()
            found = await profile.check_pixel(xy, rgb, timeout=0, thr=2)

            if found:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get("pvp", 0)

                if now - last_time >= 20:
                    EventsManager.send_event(window_id, {"type": "pvp"})
                    log(f"ПВП ивент отправлен в {window_id}", self.tname)
                    last_events["pvp"] = now

                await asyncio.sleep(3)
            else:
                await ev.wait()

    async def _monitor_hp_bank(self, window_id: str, profile: BaseProfile) -> None:
        if profile.runtime_data.has_quiver is None:
            quiver_status = await find_quiver(profile)
            profile.runtime_data.has_quiver = quiver_status

        if profile.runtime_data.has_quiver is True:
            xy, rgb = parseCBT("q_hp_bank_in_energo", profile=profile)
        if profile.runtime_data.has_quiver is False:
            xy, rgb = parseCBT("hp_bank_in_energo", profile=profile)

        while profile.running:
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
                last_time = last_events.get("hp_bank", 0)
                #print(2)
                if now - last_time >= 60:
                    EventsManager.send_event(window_id, {"type": "hp_bank"})
                    log(f"Хп банка ивент отправлен в {window_id}", self.tname)
                    last_events["hp_bank"] = now


            await asyncio.sleep(3)

    async def _monitor_soska(self, window_id: str, profile: BaseProfile) -> None:
        if profile.runtime_data.has_quiver is None:
            quiver_status = await find_quiver(profile)
            profile.runtime_data.has_quiver = quiver_status

        if profile.runtime_data.has_quiver is True:
            xy, rgb = parseCBT("q_soska_in_energo", profile=profile)
        if profile.runtime_data.has_quiver is False:
            xy, rgb = parseCBT("soska_in_energo", profile=profile)

        while profile.running:
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
                last_time = last_events.get("soska", 0)
                # print(2)
                if now - last_time >= 60:
                    EventsManager.send_event(window_id, {"type": "soska"})
                    log(f"Соска ивент отправлен в {window_id}", self.tname)
                    last_events["soska"] = now

            await asyncio.sleep(5)

    async def _monitor_death(self, window_id: str, profile: BaseProfile) -> None:
        while profile.running:
            death_found, btn = await check_rip(profile)
            if death_found and btn != "":
                now_monotonic = time.monotonic()
                now_ts = int(time.time())
                now = now_monotonic
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get("death", 0)

                if now - last_time >= 60:
                    #print(death_found)
                    #print(btn)
                    EventsManager.send_event(window_id, {"type": "death"})
                    log(f"DEATH ивент отправлен в {window_id}", self.tname)
                    last_events["death"] = now_monotonic
                    self._last_time.setdefault(window_id, {})["death"] = now_ts

                await asyncio.sleep(6)
            else:
                await asyncio.sleep(3)

    async def _monitor_spot_back(self, window_id: str, profile: BaseProfile) -> None:
        while profile.running:
            if (
                    profile.runtime_data.current_state not in ["combat", "death"]
                    and profile.runtime_data.spot_time
                    and profile.runtime_data.time_to_back()
            ):
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get("spot_back", 0)

                if now - last_time >= 60:
                    EventsManager.send_event(window_id, {"type": "spot_back"})
                    profile.runtime_data.spot_time = None
                    log(f"SPOT_BACK ивент отправлен в {window_id}", self.tname)
                    last_events["spot_back"] = now

            await asyncio.sleep(3)

    async def _monitor_sell_stash_buy(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            now = time.monotonic()
            last_events = self._last_event_time.setdefault(window_id, {})
            last_time = last_events.get("sell_stash_buy", 0)

            buying = profile.settings.is_schedule("buying", window_id)

            if buying and now - last_time >= 240:
                EventsManager.send_event(window_id, {"type": "sell_stash_buy"})
                log(f"SELL_STASH_BUY ивент отправлен в {window_id}", self.tname)

                last_events["sell_stash_buy"] = now

            await asyncio.sleep(5)

    async def _monitor_mail(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            now = time.monotonic()
            last_events = self._last_event_time.setdefault(window_id, {})
            last_time = last_events.get("claim_mail", 0)

            mail = profile.settings.is_schedule("mail", window_id)

            if mail and now - last_time >= 240:
                EventsManager.send_event(window_id, {"type": "claim_mail"})
                log(f"MAIL ивент отправлен в {window_id}", self.tname)

                last_events["claim_mail"] = now

            await asyncio.sleep(5)

    async def _monitor_party(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            now = time.monotonic()
            last_events = self._last_event_time.setdefault(window_id, {})
            last_time = last_events.get("party_dungeon", 0)

            party_dungeon = profile.settings.is_schedule("party_dungeon", window_id)

            if party_dungeon and now - last_time >= 120:
                EventsManager.send_event(window_id, {"type": "party_dungeon"})
                log(f"PARTY ивент отправлен в {window_id}", self.tname)

                last_events["party_dungeon"] = now

            await asyncio.sleep(5)

    async def _monitor_auction(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            now = time.monotonic()
            last_events = self._last_event_time.setdefault(window_id, {})
            last_time = last_events.get("auction", 0)

            auc = profile.settings.is_schedule("auction", window_id)

            if auc and now - last_time >= 240:
                EventsManager.send_event(window_id, {"type": "auction"})
                log(f"AUCTION ивент отправлен в {window_id}", self.tname)

                last_events["auction"] = now

            await asyncio.sleep(5)

    async def _monitor_rewards(self, window_id: str,
                                      profile: BaseProfile) -> None:
        while profile.running:
            now = time.monotonic()
            last_events = self._last_event_time.setdefault(window_id, {})
            last_time = last_events.get("claim_rewards", 0)

            rewards = profile.settings.is_schedule("rewards", window_id)

            if rewards and now - last_time >= 240:
                EventsManager.send_event(window_id, {"type": "claim_rewards"})
                log(f"REWARDS ивент отправлен в {window_id}", self.tname)

                last_events["claim_rewards"] = now

            await asyncio.sleep(5)

    async def _monitor_schedule_schedule(self, window_id: str, profile: BaseProfile) -> None:
        while profile.running:
            now = time.monotonic()
            last_events = self._last_event_time.setdefault(window_id, {})
            last_time = last_events.get("schedule", 0)
            schedule = profile.settings.get_schedule_schedule()
            if schedule and now - last_time >= 240:
                EventsManager.send_event(window_id, {"type": "schedule"})
                log(f"schedule ивент отправлен в {window_id}", self.tname)
                last_events["schedule"] = now

            await asyncio.sleep(30)

    async def _monitor_overweight(self, window_id: str, profile: BaseProfile):
        if profile.runtime_data.has_quiver is None:
            profile.runtime_data.has_quiver = await find_quiver(profile)

        coords = {
            OverWeight.ZERO: "q_pereves0" if profile.runtime_data.has_quiver else "pereves0",
            OverWeight.FIFTY: "q_pereves2" if profile.runtime_data.has_quiver else "pereves2",
            OverWeight.EIGHTY: "q_pereves1" if profile.runtime_data.has_quiver else "pereves1",
        }

        while profile.running:
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
                last_time = last_events.get("overweight", 0)
                if now - last_time >= 30:
                    EventsManager.send_event(window_id, {"type": "overweight"})
                    last_events["overweight"] = now

            await asyncio.sleep(50)

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

        store = FrameStore()

        while profile.running:
            ev = store.get_frame_event()

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
                last_time = last_events.get("health", 0)
                if now - last_time >= 1:
                    last_events["health"] = now
                    # EventsManager.send_event(window_id, {"type": "health"})

            await ev.wait()

    async def low_hp_dodge(self, window_id: str, profile: BaseProfile):
        window_id, window = next(iter(profile.window_info.items()))
        await asyncio.sleep(0.3)
        if profile.settings.LOW_HP_DODGE:
            if profile.runtime_data.current_state == "combat":
                self.start_monitoring(window_id, profile, [MonitorType.HEALTH])
            else:
                return '{"errors": 1, "description": "need combat state before calling this func"}'

            await asyncio.sleep(3)
            hb = profile.settings.HEALTH_BACK
            m = max(hb or [30])
            while profile.runtime_data.current_state == "combat":
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
                    EventsManager.send_event(window_id, {"type": "low_hp_dodge"})
                    self.stop_once(window_id, MonitorType.LOW_HP_DODGE)
                else:
                    #log(f"Терпим, нас ебут а мы крепчаем... | {hp}/{m}", window_id)
                    pass

            await asyncio.sleep(20)

    async def _check_ethernet_disc_error(self, window_id: str, profile: BaseProfile):
        while profile.running:
            try:
                found = await check_ethernet2_error(profile)
                if found:
                    EventsManager.send_event(window_id, {
                        "type": "error",
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
                found = await check_ethernet1_error(profile)
                if found:
                    EventsManager.send_event(window_id, {
                        "type": "error",
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
                found = await check_disconnect(profile)
                if found:
                    EventsManager.send_event(window_id, {
                        "type": "error",
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
                continue

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