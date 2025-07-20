from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
from constans import GLOBAL_STATES

@dataclass
class RuntimeData:
    current_state: str = "null"                   # текущий статус (возможные в constans.py GLOBAL_STATES)
    stashing_count: int = 0                       # сколько раз пытались стешнуть шмотки за время работы бота
    last_return_spot: Optional[str] = None        # время последнего возврата на спот
    spot_time: Optional[str] = None               # время когда надо тп на рандом спот
    dodge_attempts: int = 0                       # попытки сдоджить пвп
    last_dodge: Optional[str] = None              # ластовая попытка доджа пвп

    #todo
    npc_list_spot1: Optional[Dict[str, str]] = None
    npc_list_spot2: Optional[Dict[str, str]] = None
    npc_list_spot3: Optional[Dict[str, str]] = None
    npc_list_spot4: Optional[Dict[str, str]] = None
    #todo

    def __post_init__(self):
        if self.current_state not in GLOBAL_STATES:
            raise ValueError(f"Невалидный стейт при ините: {self.current_state} / Валидные: {GLOBAL_STATES}")

    def update_return_spot(self):
        self.last_return_spot = datetime.now().strftime("%H:%M")

    def update_dodge_attempt(self):
        self.dodge_attempts += 1

    def update_last_dodge(self):
        self.last_dodge = datetime.now().strftime("%H:%M")

    def update_stashing(self):
        self.stashing_count += 1

    def reset_stashing(self):
        self.stashing_count = 0

    def time_to_back(self) -> bool:
        if not self.spot_time:
            return False

        now = datetime.now()
        try:
            scheduled = datetime.strptime(self.spot_time, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
        except ValueError:
            return False

        delta = now - scheduled
        return 0 <= delta.total_seconds() < 600

    def set_state(self, new_state: str):
        if new_state not in GLOBAL_STATES:
            raise ValueError(f"Невалидный стейт: {new_state} / Валидные: {GLOBAL_STATES}")
        self.current_state = new_state