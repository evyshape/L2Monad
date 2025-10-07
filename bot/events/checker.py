import asyncio
import time
from typing import Dict

from bot.clogger import log
from bot.delays import PVP_CHECK_DELAY
from bot.misc import *
from bot.events.events import EventsManager
from bot.events.enums import MonitorType, OverWeight, ErrorTypes
from bot.methods.base import parseCBT
from bot.methods.game import check_rip, find_quiver, check_ethernet1_error, check_disconnect, check_ethernet2_error
from profiles.base import BaseProfile


class EventsChecker:
    def __init__(self):
        self.tasks: Dict[str, list[asyncio.Task]] = {}
        self._last_event_time: Dict[str, Dict[str, float]] = {}
        self._last_time: Dict[str, Dict[str, int | None]] = {}
        self.tname = "-EventsChecker-"

    def get_last_timestamp(self, window_id: str, event_type: str) -> int | None:
        return self._last_time.get(window_id, {}).get(event_type)

    async def _monitor_pvp(self, window_id: str, profile: BaseProfile) -> None:
        xy, rgb = parseCBT("pvp_energo_trigger", profile=profile)

        while profile.running:
            found = await profile.check_pixel(xy, rgb, timeout=0.15, thr=2)

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
                await asyncio.sleep(PVP_CHECK_DELAY)

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
            for _ in range(7):
                found = await profile.check_pixel(xy, rgb, timeout=0.6, thr=9)
                if found:
                    checks += 1
                    
                await asyncio.sleep(2)

            if checks >= 5:
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
                await asyncio.sleep(6)

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
        if profile.runtime_data.has_quiver is None:
            profile.runtime_data.has_quiver = await find_quiver(profile)

        #start_xy, _ = parseCBT("hp_start", profile=profile)
        #end_xy, _ = parseCBT("hp_end", profile=profile)

        start_xy = "10, 9"
        end_xy = "69, 9"

        x1, y1 = map(int, start_xy.split(","))
        x2, y2 = map(int, end_xy.split(","))

        bar = abs(x2 - x1)

        while profile.running:
            health_thr = profile.settings.HEALTH_BACK or []
            if not health_thr:
                await asyncio.sleep(1.0)
                continue

            step = 3
            tasks = []
            for dx in range(0, bar + 1, step):
                x = x1 + dx
                tasks.append(
                    profile.check_pixel((x, y1), (160, 40, 10), timeout=0.05, thr=60,
                                        wsize="1x1")
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            red = sum(1 for res in results if res is True)
            total = len(results)

            if total > 0:
                hp_percent = int((red / total) * 100)
            else:
                hp_percent = 0

            profile.runtime_data.health = hp_percent
            #print(hp_percent)
            now = time.monotonic()
            last_events = self._last_event_time.setdefault(window_id, {})
            last_time = last_events.get("health", 0)

            if hp_percent and now - last_time >= 1:
                last_events["health"] = now
                # EventsManager.send_event(window_id, {"type": "health"})

            await asyncio.sleep(0.1)

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
            await asyncio.sleep(60 * 6)

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

        if window_id in self.tasks:
            log(f"Чекер уже запущен для {window_id}", self.tname)
            return

        log(f"Запускаю евент чекеры для {window_id} по {[m.value for m in monitors]}", self.tname)

        tasks = []
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
        }

        for mtype in monitors:
            func = checkers.get(mtype)
            if func:
                tasks.append(asyncio.create_task(func(window_id, profile)))

        self.tasks[window_id] = tasks

    def stop_monitoring(self, window_id: str) -> None:
        tasks = self.tasks.pop(window_id, [])
        for task in tasks:
            task.cancel()