import asyncio
import time
from typing import Dict

from bot.clogger import log
from bot.delays import PVP_CHECK_DELAY
from bot.events.events import EventsManager
from bot.events.enums import MonitorType, OverWeight
from bot.methods.base import parseCBT
from bot.methods.game import check_rip, find_quiver
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
        xy, rgb = parseCBT("pvp_energo_trigger")

        while profile.running:
            found = await profile.check_pixel(xy, rgb, timeout=0.15, thr=4)

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
            xy, rgb = parseCBT("q_hp_bank_in_energo")
        if profile.runtime_data.has_quiver is False:
            xy, rgb = parseCBT("hp_bank_in_energo")

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


            await asyncio.sleep(5)

    async def _monitor_soska(self, window_id: str, profile: BaseProfile) -> None:
        if profile.runtime_data.has_quiver is None:
            quiver_status = await find_quiver(profile)
            profile.runtime_data.has_quiver = quiver_status

        if profile.runtime_data.has_quiver is True:
            xy, rgb = parseCBT("q_soska_in_energo")
        if profile.runtime_data.has_quiver is False:
            xy, rgb = parseCBT("soska_in_energo")

        while profile.running:
            checks = 0
            # print(1)
            for _ in range(4):
                found = await profile.check_pixel(xy, rgb, timeout=0.3, thr=7)
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
        await asyncio.sleep(1)
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
                xy, rgb = parseCBT(cb_key)
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

        all_levels = list(range(10, 101, 10)) # анти хардкод списка епт

        while profile.running:
            health_thr = profile.settings.HEALTH_BACK or []
            if not health_thr:
                await asyncio.sleep(1.0)
                continue

            min_thr = min(health_thr)  # минимальный порог для сьеба в город
            check_levels = [x for x in all_levels if x >= min_thr]

            hp_keys = [f"hp_{value}" for value in check_levels]

            tasks = []
            for cb_key in hp_keys:
                xy, rgb = parseCBT(cb_key)
                tasks.append(
                    profile.check_pixel(xy, rgb, timeout=3, thr=31, wsize="1x1")
                )  # todo подобрать идеальный thr

            results = await asyncio.gather(*tasks, return_exceptions=True)

            found_levels = [
                int(key.split("_")[1]) for key, res in zip(hp_keys, results) if
                res is True
            ]
            if not found_levels:
                await asyncio.sleep(2)
                continue

            detected_hp = max(found_levels)
            profile.runtime_data.health = detected_hp

            now = time.monotonic()
            last_events = self._last_event_time.setdefault(window_id, {})
            last_time = last_events.get("health", 0)

            if detected_hp and now - last_time >= 1:
                # EventsManager.send_event(window_id, {"type": "health"}) # можно в целом вернуть но я пока не хочу ловить ивентами буду брать из рантайма
                last_events["health"] = now

            await asyncio.sleep(1)

    def start_monitoring(self, window_id: str, profile: BaseProfile,
                         monitors: list[MonitorType]) -> None:
        if window_id in self.tasks:
            log(f"Чекер уже запущен для {window_id}", self.tname)
            return

        log(f"Запускаю евент чекеры для {window_id} по {[m.value for m in monitors]}", self.tname)

        tasks = []
        for monitor_type in monitors:
            if monitor_type == MonitorType.PVP:
                tasks.append(asyncio.create_task(self._monitor_pvp(window_id, profile)))
            elif monitor_type == MonitorType.HP_BANK:
                tasks.append(asyncio.create_task(self._monitor_hp_bank(window_id, profile)))
            elif monitor_type == MonitorType.DEATH:
                tasks.append(asyncio.create_task(self._monitor_death(window_id, profile)))
            elif monitor_type == MonitorType.SPOT_BACK:
                tasks.append(asyncio.create_task(self._monitor_spot_back(window_id, profile)))
            elif monitor_type == MonitorType.SELL_STASH_BUY:
                tasks.append(asyncio.create_task(self._monitor_sell_stash_buy(window_id, profile)))
            elif monitor_type == MonitorType.CLAIM_MAIL:
                tasks.append(asyncio.create_task(self._monitor_mail(window_id, profile)))
            elif monitor_type == MonitorType.CLAIM_REWARDS:
                tasks.append(asyncio.create_task(self._monitor_rewards(window_id, profile)))
            elif monitor_type == MonitorType.SCHEDULE:
                tasks.append(asyncio.create_task(self._monitor_schedule_schedule(window_id, profile)))
            elif monitor_type == MonitorType.SOSKA:
                tasks.append(asyncio.create_task(self._monitor_soska(window_id, profile)))
            elif monitor_type == MonitorType.OVERWEIGHT:
                tasks.append(asyncio.create_task(self._monitor_overweight(window_id, profile)))
            elif monitor_type == MonitorType.HEALTH:
                tasks.append(asyncio.create_task(self._monitor_health(window_id, profile)))
            elif monitor_type == MonitorType.AUCTION:
                tasks.append(asyncio.create_task(self._monitor_auction(window_id, profile)))

        self.tasks[window_id] = tasks

    def stop_monitoring(self, window_id: str) -> None:
        tasks = self.tasks.pop(window_id, [])
        for task in tasks:
            task.cancel()