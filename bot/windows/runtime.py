from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from constans import GLOBAL_STATES
from bot.events.enums import OverWeight

@dataclass
class RuntimeData:
    """
    Класс для хранения временных данных (за сессию)
    """

    current_state: str = "null"                     # текущий статус (валидные значения в GLOBAL_STATES)
    stashing_count: int = 0                         # количество попыток стешнуть шмотки
    buy_count: int = 0                              # количество попыток закупиться
    purc_count: int = 0                             # количество попыток продаться
    last_return_spot: Optional[str] = None          # время последнего возврата на спот
    spot_time: Optional[str] = None                 # время для тп на рандомный спот
    dodge_attempts: int = 0                         # количество попыток доджа пвп
    last_dodge: Optional[str] = None                # последняя попытка доджа пвп
    last_succ_dodge: Optional[str] = None           # последняя успешная попытка доджа пвп
    has_quiver: Optional[bool] = None               # есть ли колчан (двигаются гуи элементы в энерего)
    last_mapping: Optional[Dict[str, str]] = None   # последний полученный маппинг
    overweight: OverWeight = OverWeight.ZERO
    overweight_sended: Dict[int, bool] = field(default_factory=lambda: {0: False, 50: False, 80: False})

    def __post_init__(self):
        if self.current_state not in GLOBAL_STATES:
            raise ValueError(f"Невалидный стейт при ините: {self.current_state} / Валидные: {GLOBAL_STATES}")

    def update_overweight(self, value: OverWeight) -> None:
        self.overweight = value
        current = self.overweight.value

        for level in self.overweight_sended:
            if current < level:
                self.overweight_sended[level] = False

        if current >= 80:
            self.overweight_sended[80] = True
        elif current >= 50:
            self.overweight_sended[50] = True
        else:
            self.overweight_sended[0] = True

    def need_overweight(self, uv: int) -> Optional[int]:
        for level in sorted(self.overweight_sended):
            if self.overweight_sended[level] and level <= uv:
                return level
        return None

    def update_last_mapping(self, mapping: Optional[Dict[str, Any]]) -> None:
        """
        Ожидается словарь {"stash": "...", "shop": "...", "buyer": "..."} или None.
        """
        if mapping is not None:
            req = {"stash", "shop", "buyer"}
            if not req.issubset(mapping.keys()):
                raise ValueError(
                    f"Некорректный маппинг: {mapping}. "
                    f"Ожидается: {req}"
                )
        self.last_mapping = mapping

    def update_dodge_attempt(self) -> None:
        self.dodge_attempts += 1

    def update_last_return(self) -> None:
        self.last_return_spot = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    def update_last_dodge(self) -> None:
        self.last_dodge = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    def update_last_succ_dodge(self) -> None:
        self.last_succ_dodge = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    def update_stashing(self) -> None:
        self.stashing_count += 1

    def update_buy(self) -> None:
        self.buy_count += 1

    def update_purc(self) -> None:
        self.purc_count += 1

    def time_to_back(self) -> bool:
        """
        Проверяет, не пора ли бекаться на спот.
        Возвращает тру, если текущее время находится в пределах 10 минут после spot_time.
        """
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

    def set_state(self, new_state: str) -> None:
        #todo replace all to set state
        if new_state not in GLOBAL_STATES:
            raise ValueError(f"Невалидный стейт: {new_state} / Валидные: {GLOBAL_STATES}")
        self.current_state = new_state

    def reset(self) -> None:
        """Сброс всего кэша"""
        self.stashing_count = 0
        self.buy_count = 0
        self.purc_count = 0
        self.last_return_spot = None
        self.spot_time = None
        self.dodge_attempts = 0
        self.last_dodge = None
        self.last_succ_dodge = None
        self.has_quiver = None
        self.last_mapping = None