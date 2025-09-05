import asyncio
import time
from typing import Dict
from bot.events.events import EventsManager
from profiles.base import BaseProfile
from bot.methods.base import parseCBT
from bot.events.enums import MonitorType
from clogger import log
from bot.events.enums import OverWeight
from bot.methods.game import check_rip, find_quiver

class EventsChecker:
    def __init__(self):
        self.tasks: Dict[str, list[asyncio.Task]] = {}
        self._last_event_time: Dict[str, Dict[str, float]] = {}
        self.tname = "-EventsChecker-"

    async def _monitor_pvp(self, window_id: str, profile: BaseProfile) -> None:
        xy, rgb = parseCBT("pvp_energo_trigger")

        while profile.running:
            found = await profile.check_pixel(xy, rgb, timeout=0.4, thr=1)

            if found:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get("pvp", 0)

                if now - last_time >= 20:
                    EventsManager.send_event(window_id, {"type": "pvp"})
                    log(f"ПВП ивент отправлен в {window_id}", self.tname)
                    last_events["pvp"] = now

                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.05)

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
            for _ in range(13):
                found = await profile.check_pixel(xy, rgb, timeout=0.3, thr=7)
                #print(found)
                if found:
                    checks += 1
                    
                await asyncio.sleep(1)

            if checks >= 10:
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
            for _ in range(13):
                found = await profile.check_pixel(xy, rgb, timeout=0.3, thr=7)
                # print(found)
                if found:
                    checks += 1

                await asyncio.sleep(1)

            if checks >= 10:
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
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get("death", 0)

                if now - last_time >= 60:
                    #print(death_found)
                    #print(btn)
                    EventsManager.send_event(window_id, {"type": "death"})
                    log(f"DEATH ивент отправлен в {window_id}", self.tname)
                    last_events["death"] = now

                await asyncio.sleep(2)
            else:
                await asyncio.sleep(1)

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

    async def _monitor_overweight(self, window_id: str, profile: BaseProfile) -> None:
        await asyncio.sleep(1)
        if profile.runtime_data.has_quiver is None:
            profile.runtime_data.has_quiver = await find_quiver(profile)

        coords = {
            OverWeight.ZERO: "q_pereves0" if profile.runtime_data.has_quiver else "pereves0",
            OverWeight.FIFTY: "q_pereves2" if profile.runtime_data.has_quiver else "pereves2",
            OverWeight.EIGHTY: "q_pereves1" if profile.runtime_data.has_quiver else "pereves1",
        }

        while profile.running:
            checks = {level: 0 for level in
                      [OverWeight.ZERO, OverWeight.FIFTY, OverWeight.EIGHTY]}

            for _ in range(2):
                for level, cb_key in coords.items():
                    xy, rgb = parseCBT(cb_key)
                    found = await profile.check_pixel(xy, rgb, timeout=2, thr=1)
                    if found:
                        checks[level] += 1
                await asyncio.sleep(1)

            detected_level = OverWeight.ZERO
            if checks[OverWeight.EIGHTY] >= 1:
                detected_level = OverWeight.EIGHTY
            elif checks[OverWeight.FIFTY] >= 1:
                detected_level = OverWeight.FIFTY

            profile.runtime_data.update_overweight(detected_level)
            to_notify = profile.runtime_data.need_overweight(profile.settings.OVERWEIGHT_AFK)

            if to_notify is not None:
                now = time.monotonic()
                last_events = self._last_event_time.setdefault(window_id, {})
                last_time = last_events.get(f"overweight", 0)
                if now - last_time >= 30:
                    EventsManager.send_event(window_id, {"type": "overweight"})
                    last_events["overweight"] = now

            await asyncio.sleep(5)

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

        self.tasks[window_id] = tasks

    def stop_monitoring(self, window_id: str) -> None:
        tasks = self.tasks.pop(window_id, [])
        for task in tasks:
            task.cancel()