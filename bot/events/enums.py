from enum import StrEnum, IntEnum

# класс описывающий перевес, он в целом не нужен но добавлен для удобства юза. бот умеет определять все 3 события и сохранять в рантайм дату (bot.windows.runtime.py)
class OverWeight(IntEnum):
    ZERO = 0
    FIFTY = 50
    EIGHTY = 80


class ErrorTypes(StrEnum):
    DISCONNECT_TO_MENU = "connect_to_server" # выбросило просто в меню без таблички
    DISCONNECT_FULL = "check_disconnect_full" # фулл выбросило в меню + из игры app closed todo
    ETHERNET_ERROR = "close_ethernet1_error" # ошибка на ру сервах с цифрами (P:3102:500)
    ETHERNET2_ERROR = "close_ethernet2_error" # выбросило в меню с табличкой, если ее ловим то вручную надо отправить ивент дисконект ту меню


# все возможные ивенты которые бот умеет отслеживать. смотрите в bot.events.checker.py
class MonitorType(StrEnum):
    PVP = "pvp"
    DEATH = "death"
    HP_BANK = "hp_bank"
    ERROR = "error"
    SOSKA = "soska"
    HEALTH = "health"
    OVERWEIGHT = "overweight"
    CLAIM_REWARDS = "claim_rewards"
    CLAIM_MAIL = "claim_mail"
    SPOT_BACK = "spot_back"
    SELL_STASH_BUY = "sell_stash_buy"
    SCHEDULE = "schedule"
    AUCTION = "auction"
    LOW_HP_DODGE = "low_hp_dodge"
    PARTY_DUNGEON = "party_dungeon"


class BotState(StrEnum):
    NULL = "null"
    AFK = "afk"
    COMBAT = "combat"
    SHOPPING = "shopping"
    STASHING = "stashing"
    DEATH = "death"
    CLAIMING = "claiming"
    SCHEDULE = "schedule"
    PVP = "pvp"
    ALCHEMY = "alchemy"


class ScheduleAction(StrEnum):
    BUYING = "buying"
    MAIL = "mail"
    REWARDS = "rewards"
    AUCTION = "auction"
    PARTY_DUNGEON = "party_dungeon"


class Region(StrEnum):
    RU = "RU"
    JP = "JP"


class NotifyLevel(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    TRASH = "trash"


# приорететы, если одновременно прилетает 2 ивента условный пвп и условный клайм мейл сначала обработается пвп
PRIORITIES = {
    MonitorType.PVP: 1,
    MonitorType.DEATH: 2,
    MonitorType.ERROR: 3,
    MonitorType.HP_BANK: 4,
    MonitorType.SOSKA: 5,
    MonitorType.HEALTH: 6,
    MonitorType.OVERWEIGHT: 7,
    MonitorType.CLAIM_REWARDS: 8,
    MonitorType.CLAIM_MAIL: 9,
    MonitorType.SPOT_BACK: 10,
    MonitorType.SELL_STASH_BUY: 11,
    MonitorType.SCHEDULE: 12,
    MonitorType.AUCTION: 13,
    MonitorType.LOW_HP_DODGE: 14,
    MonitorType.PARTY_DUNGEON: 15,
}