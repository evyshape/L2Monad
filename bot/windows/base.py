from dataclasses import dataclass
from typing import Dict
from datetime import datetime, timedelta
import os

SCHEDULE_LOG_DIR = os.path.join("settings", "schedules")

@dataclass
class BaseSettings:
    REGION: str  # "JP" или "RU"
    PVP_EVADE: bool # тру фолс, не может быть одновременно включено с PVP_ANSWER
    PVP_ANSWER: bool # тру фолс, не может быть одновременно включено с PVP_EVADE
    HP_BANK_CHECKER: bool # тру фолс
    SOSKA_CHECKER: bool # тру фолс
    DEATH_CHECKER: bool # тру фолс
    SCHEDULE_BUYING: str # "10:00" или "10:00|12:00"
    SCHEDULE_MAIL: str # "10:00" или "10:00|12:00"
    SCHEDULE_REWARDS: str # "10:00" или "10:00|12:00"
    SCHEDULE_SCHEDULE: str # "10:00-18:00"
    SCHEDULE_AUCTION: str # "10:00|18:00"
    DONATE_SHOP_PAGES: str # "1|3|4" либо "1"
    SPOT_OT: int # 1 не может быть выше 4
    SPOT_DO: int # 4 не может быть выше 4
    TELEGRAM_NOTIFIES: bool # уведомления от этого окна в тг бота


    def __post_init__(self):
        if any(x > 4 for x in (self.SPOT_OT, self.SPOT_DO)):
            raise ValueError("SPOT_OT и SPOT_DO не могут быть больше 4")

        regions = {"JP", "RU"}
        if self.REGION not in regions:
            raise ValueError(f"REGION должен быть одним из: {', '.join(regions)}")

        if self.PVP_EVADE and self.PVP_ANSWER:
            raise ValueError("PVP_EVADE и PVP_ANSWER не могут быть одновременно True")

        for name, schedule in {
            "SCHEDULE_BUYING": self.SCHEDULE_BUYING,
            "SCHEDULE_MAIL": self.SCHEDULE_MAIL,
            "SCHEDULE_REWARDS": self.SCHEDULE_REWARDS
        }.items():
            self._validate_schedule(schedule, name)

    def _validate_schedule(self, schedule_str: str, field_name: str):
        if not schedule_str:
            return
        for time_str in schedule_str.split("|"):
            try:
                datetime.strptime(time_str, "%H:%M")
            except ValueError:
                raise ValueError(f"{field_name} содержит некорректное время: '{time_str}'")

    def get_schedule(self) -> Dict[str, list]:
        return {
            "buying": self.SCHEDULE_BUYING.split('|') if self.SCHEDULE_BUYING else [],
            "mail": self.SCHEDULE_MAIL.split('|') if self.SCHEDULE_MAIL else [],
            "rewards": self.SCHEDULE_REWARDS.split('|') if self.SCHEDULE_REWARDS else [],
        }

    def is_schedule(self, action: str, nickname: str) -> bool:
        #print(action)
        #print(nickname)
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        schedules = self.get_schedule()
        times = schedules.get(action.lower(), [])
        if not times:
            #print(1)
            return False

        os.makedirs(SCHEDULE_LOG_DIR, exist_ok=True)
        log_path = os.path.join(SCHEDULE_LOG_DIR, f"{nickname}.txt")

        ex = set()
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{today_str}:{action.lower()}:"):
                        parts = line.split(":")
                        if len(parts) == 3:
                            ex.add(parts[2])

        for scheduled_time_str in times:
            scheduled_time = datetime.strptime(scheduled_time_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )

            if timedelta(0) <= now - scheduled_time < timedelta(minutes=2):
                if scheduled_time_str in ex:
                    continue

                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"{today_str}:{action.lower()}:{scheduled_time_str}\n")
                return True

        return False

    def get_pages(self) -> list[int]:
        if not self.DONATE_SHOP_PAGES:
            return []
        try:
            return [int(page.strip()) for page in self.DONATE_SHOP_PAGES.split("|") if page.strip().isdigit()]
        except ValueError as e:
            raise ValueError(f"Ошибка в DONATE_SHOP_PAGES: {e}")

    def get_schedule_schedule(self) -> bool:
        if not self.SCHEDULE_SCHEDULE:
            return False

        try:
            start_str, end_str = self.SCHEDULE_SCHEDULE.split("-")
            now = datetime.now()
            start = datetime.strptime(start_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            return timedelta(0) <= now - start < timedelta(minutes=10)
        except Exception as e:
            raise ValueError(f"Ошибка в SCHEDULE_SCHEDULE: {self.SCHEDULE_SCHEDULE} — {e}")

    def is_schedule_schedule(self) -> bool:
        if not self.SCHEDULE_SCHEDULE:
            return False

        try:
            start_str, end_str = self.SCHEDULE_SCHEDULE.split("-")
            now = datetime.now()
            start = datetime.strptime(start_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            end = datetime.strptime(end_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            return start <= now <= end
        except Exception as e:
            raise ValueError(f"Ошибка в SCHEDULE_SCHEDULE: {self.SCHEDULE_SCHEDULE} — {e}")

default_values = {
    "REGION": "JP",
    "PVP_EVADE": True,
    "PVP_ANSWER": False,
    "HP_BANK_CHECKER": True,
    "SOSKA_CHECKER": False,
    "DEATH_CHECKER": True,
    "SCHEDULE_BUYING": "10:30|13:30|20:20",
    "SCHEDULE_MAIL": "10:00|15:00|20:00|05:00",
    "SCHEDULE_REWARDS": "21:03",
    "SCHEDULE_SCHEDULE": "",
    "SCHEDULE_AUCTION": "",
    "DONATE_SHOP_PAGES": "1|3",
    "SPOT_OT": 1,
    "SPOT_DO": 1,
    "TELEGRAM_NOTIFIES": True,
}

