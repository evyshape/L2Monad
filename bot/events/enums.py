from enum import StrEnum, IntEnum

# класс описывающий перевес, он в целом не нужен но добавлен для удобства юза. бот умеет определять все 3 события и сохранять в рантайм дату (bot.windows.runtime.py)
class OverWeight(IntEnum):
    ZERO = 0
    FIFTY = 50
    EIGHTY = 80

# все возможные ивенты которые бот умеет отслеживать. смотрите в bot.events.checker.py
class MonitorType(StrEnum):
    PVP = "pvp"
    DEATH = "death"
    HP_BANK = "hp_bank"
    SOSKA = "soska"
    HEALTH = "health"
    OVERWEIGHT = "overweight"
    CLAIM_REWARDS = "claim_rewards"
    CLAIM_MAIL = "claim_mail"
    SPOT_BACK = "spot_back"
    SELL_STASH_BUY = "sell_stash_buy"
    SCHEDULE = "schedule"
    AUCTION = "auction"

# приорететы, если одновременно прилетает 2 ивента условный пвп и условный клайм мейл сначала обработается пвп
PRIORITIES = {
    MonitorType.PVP: 1,
    MonitorType.DEATH: 2,
    MonitorType.HP_BANK: 3,
    MonitorType.SOSKA: 4,
    MonitorType.HEALTH: 5,
    MonitorType.OVERWEIGHT: 6,
    MonitorType.CLAIM_REWARDS: 7,
    MonitorType.CLAIM_MAIL: 8,
    MonitorType.SPOT_BACK: 9,
    MonitorType.SELL_STASH_BUY: 10,
    MonitorType.SCHEDULE: 11,
    MonitorType.AUCTION: 12,
}