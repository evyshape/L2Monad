from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Union

from bot.constans import GLOBAL_STATES, CBT_JP, CBT_RU
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

    last_overweight: OverWeight = OverWeight.ZERO
    overweight: OverWeight = OverWeight.ZERO
    overweight_sended: Dict[int, bool] = field(default_factory=lambda: {0: False, 50: False, 80: False})

    health: int = 0

    captures: dict[str, list[dict]] = field(default_factory=lambda: dict())
    CAPTURE_LIMIT: int = 10

    def __post_init__(self):
        if self.current_state not in GLOBAL_STATES:
            raise ValueError(f"Невалидный стейт при ините: {self.current_state} / Валидные: {GLOBAL_STATES}")

    def update_overweight(self, value: OverWeight) -> None:
        self.last_overweight = self.overweight
        self.overweight = value

    def need_notify(self) -> Optional[int]:
        prev = self.last_overweight.value
        curr = self.overweight.value

        if prev < 50 <= curr:
            return 50
        if prev < 80 <= curr:
            return 80
        if prev >= 80 and curr < 80 and curr >= 50:
            return 50
        if prev >= 50 and curr < 50:
            return 0
        if prev >= 80 and curr < 50:
            return 0

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
        """Сброс всего кэша (не всего, мне впадлу)"""
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

    def record_capture(self, xy: Tuple[int, int], rgb: Union[Tuple[int,int,int], str], profile: Optional[Any] = None) -> None:
        xy_str = f"{xy[0]}, {xy[1]}"
        matched_key = None

        if profile is not None:
            region = getattr(getattr(profile, "settings", {}), "REGION", "").upper()

        cbt_map = CBT_JP if region == "JP" else CBT_RU

        for key, value in cbt_map.items():
            if value is ...:
                continue
            if xy_str in value or (isinstance(rgb, str) and rgb in value):
                matched_key = key
                break

        if matched_key is None:
            matched_key = f"bug {xy_str}"

        if matched_key not in self.captures:
            self.captures[matched_key] = []

        self.captures[matched_key].append({
            "xy": xy_str,
            "rgb": rgb,
            "time": datetime.now().strftime("%H:%M:%S")
        })

    def get_top_captures(self, top_n: int = 10) -> str:
        sorted_items = sorted(
            self.captures.items(),
            key=lambda item: len(item[1]),
            reverse=True
        )

        lines = [
            f"<b>{key}</b>: {len(records)}"
            for key, records in sorted_items[:top_n]
        ]
        return "\n".join(lines)