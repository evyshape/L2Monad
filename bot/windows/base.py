from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime, timedelta
import os

from bot.constans import SCHEDULE_LOG_DIR
from bot.events.enums import Region, ScheduleAction

@dataclass
class BaseSettings:
    REGION: str  # "JP" или "RU"
    PEACE_MODE: bool # тру = включена мирка, фолс = выключена мирка
    PVP_EVADE: bool # тру фолс, не может быть одновременно включено с PVP_ANSWER
    PVP_ANSWER: bool # тру фолс, не может быть одновременно включено с PVP_EVADE
    LOW_HP_DODGE: bool # тру фолс, хочет не пустой HEALTH_BACK
    HEALTH_BACK: List[int] # [30, 40, 50], это если включен ответ пвп при каком пороге улетать в город
    BUY_LOOT_TOWN: bool # выкупать ли шмотки пока бегаем в городе?
    BUY_LOOT_RIP: bool # выкупать ли шмотка после смерти?
    HP_BANK_CHECKER: bool # тру фолс
    SOSKA_CHECKER: bool # тру фолс
    DEATH_CHECKER: bool # тру фолс
    OVERWEIGHT_CHECKER: bool # тру фолс
    OVERWEIGHT_AFK: bool # 0-49 игнорим и ничего не делаем при любом перевесе, 50-79 тпнемся в город при перевесе 50 и будем афк, 80+ тпнемся в город при 80
    SCHEDULE_BUYING: str # "10:00" или "10:00|12:00"
    SCHEDULE_MAIL: str # "10:00" или "10:00|12:00"
    SCHEDULE_REWARDS: str # "10:00" или "10:00|12:00"
    SCHEDULE_SCHEDULE: str # "10:00-18:00"
    SCHEDULE_AUCTION: str # "10:00|18:00"
    SCHEDULE_PARTY_DUNGEON: str # "10:00|18:00"
    PARTY_DUNGEON_HARD: int # сложность от 1 до 4
    DONATE_SHOP_PAGES: str # "1|3|4" либо "1"
    ALLIANCE_BUTTON: int #0 = не донатим, 1 = 1.5кк, 2 = 6кк
    SPOT_OT: int # 1 не может быть выше 4
    SPOT_DO: int # 4 не может быть выше 4
    TELEGRAM_NOTIFIES: bool # уведомления от этого окна в тг бота
    NEED_CLAIM_DAILY: bool
    NEED_CLAIM_MAIL: bool
    NEED_CLAIM_ACHIV: bool
    NEED_CLAIM_CLAN: bool
    NEED_CLAIM_ALI: bool
    NEED_CLAIM_BATTLE_PASS: bool
    NEED_CLAIM_DONATE_SHOP: bool
    NEED_SHOP_AFTER_RIP: bool
    NEED_SHOP_AFTER_PVP_EVADE: bool
    NEED_BACK_TO_SPOT_PARTY_DUNGEON: bool
    FAST_DODGE: bool
    PVP_ANSWER_CHECK_HP_ITERATIONS: int
    DELAY_PVP_ANSWER: int
    MIN_SLEEP_AFTER_RIP: int
    MAX_SLEEP_AFTER_RIP: int
    MIN_LOW_HP_DODGE_SLEEP: int
    MAX_LOW_HP_DODGE_SLEEP: int
    MIN_PVP_DODGE_SLEEP: int
    MAX_PVP_DODGE_SLEEP: int
    AUTOHUNT_BEFORE_TP: bool


    def __post_init__(self):
        if any(x > 4 for x in (self.SPOT_OT, self.SPOT_DO)):
            raise ValueError("SPOT_OT и SPOT_DO не могут быть больше 4")

        regions = {Region.JP, Region.RU}
        if self.REGION not in regions:
            raise ValueError(f"REGION должен быть одним из: {', '.join(regions)}")

        if self.PVP_EVADE and self.PVP_ANSWER:
            raise ValueError("PVP_EVADE и PVP_ANSWER не могут быть одновременно True")

        self.SCHEDULE_BUYING = self._validate_schedule(self.SCHEDULE_BUYING, "SCHEDULE_BUYING")
        self.SCHEDULE_MAIL = self._validate_schedule(self.SCHEDULE_MAIL, "SCHEDULE_MAIL")
        self.SCHEDULE_REWARDS = self._validate_schedule(self.SCHEDULE_REWARDS, "SCHEDULE_REWARDS")
        self.SCHEDULE_AUCTION = self._validate_schedule(self.SCHEDULE_AUCTION, "SCHEDULE_AUCTION")
        self.SCHEDULE_PARTY_DUNGEON = self._validate_schedule(self.SCHEDULE_PARTY_DUNGEON, "SCHEDULE_PARTY_DUNGEON")
        self.SCHEDULE_SCHEDULE = self._validate_schedule_range(self.SCHEDULE_SCHEDULE)

    def _validate_schedule(self, schedule_str: str, field_name: str) -> str:
        if not schedule_str:
            return ""
        valid = []
        for time_str in schedule_str.split("|"):
            try:
                datetime.strptime(time_str.strip(), "%H:%M")
                valid.append(time_str.strip())
            except ValueError:
                pass
        return "|".join(valid)

    @staticmethod
    def _validate_schedule_range(schedule_str: str) -> str:
        if not schedule_str:
            return ""
        parts = schedule_str.split("-")
        if len(parts) != 2:
            return ""
        try:
            datetime.strptime(parts[0].strip(), "%H:%M")
            datetime.strptime(parts[1].strip(), "%H:%M")
            return f"{parts[0].strip()}-{parts[1].strip()}"
        except ValueError:
            return ""

    def get_schedule(self) -> Dict[str, list]:
        return {
            ScheduleAction.BUYING: self.SCHEDULE_BUYING.split('|') if self.SCHEDULE_BUYING else [],
            ScheduleAction.MAIL: self.SCHEDULE_MAIL.split('|') if self.SCHEDULE_MAIL else [],
            ScheduleAction.REWARDS: self.SCHEDULE_REWARDS.split('|') if self.SCHEDULE_REWARDS else [],
            ScheduleAction.AUCTION: self.SCHEDULE_AUCTION.split('|') if self.SCHEDULE_AUCTION else [],
            ScheduleAction.PARTY_DUNGEON: self.SCHEDULE_PARTY_DUNGEON.split('|') if self.SCHEDULE_PARTY_DUNGEON else [],
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
                        parts = line.split(":", 2)
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

            if end <= start:
                end += timedelta(days=1)

            return start <= now <= end
        except Exception as e:
            raise ValueError( f"Ошибка в SCHEDULE_SCHEDULE: {self.SCHEDULE_SCHEDULE} — {e}")

default_values = {
    "REGION": "RU",
    "PEACE_MODE": False,
    "PVP_EVADE": True,
    "PVP_ANSWER": False,
    "LOW_HP_DODGE": False,
    "HEALTH_BACK": [10, 20, 30, 40],
    "BUY_LOOT_TOWN": True,
    "BUY_LOOT_RIP": True,
    "HP_BANK_CHECKER": True,
    "SOSKA_CHECKER": False,
    "DEATH_CHECKER": True,
    "OVERWEIGHT_CHECKER": True,
    "OVERWEIGHT_AFK": 80,
    "SCHEDULE_BUYING": "10:30|13:30|20:20",
    "SCHEDULE_MAIL": "10:00|15:00|20:00|05:00",
    "SCHEDULE_REWARDS": "21:00",
    "SCHEDULE_SCHEDULE": "",
    "SCHEDULE_AUCTION": "",
    "SCHEDULE_PARTY_DUNGEON": "",
    "PARTY_DUNGEON_HARD": 1,
    "DONATE_SHOP_PAGES": "1|2",
    "ALLIANCE_BUTTON": 2,
    "SPOT_OT": 1,
    "SPOT_DO": 1,
    "TELEGRAM_NOTIFIES": True,
    "NEED_CLAIM_DAILY": True,
    "NEED_CLAIM_MAIL": True,
    "NEED_CLAIM_ACHIV": True,
    "NEED_CLAIM_CLAN": True,
    "NEED_CLAIM_ALI": True,
    "NEED_CLAIM_BATTLE_PASS": True,
    "NEED_CLAIM_DONATE_SHOP": True,
    "NEED_SHOP_AFTER_RIP": True,
    "NEED_SHOP_AFTER_PVP_EVADE": True,
    "NEED_BACK_TO_SPOT_PARTY_DUNGEON": True,
    "FAST_DODGE": True,
    "PVP_ANSWER_CHECK_HP_ITERATIONS": 3,
    "DELAY_PVP_ANSWER": 50,
    "MIN_SLEEP_AFTER_RIP": 150,
    "MAX_SLEEP_AFTER_RIP": 300,
    "MIN_LOW_HP_DODGE_SLEEP": 60,
    "MAX_LOW_HP_DODGE_SLEEP": 300,
    "MIN_PVP_DODGE_SLEEP": 120,
    "MAX_PVP_DODGE_SLEEP": 240,
    "AUTOHUNT_BEFORE_TP": True,
}

