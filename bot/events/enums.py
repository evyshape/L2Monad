from enum import StrEnum

class MonitorType(StrEnum):
    PVP = "pvp"
    DEATH = "death"
    HP_BANK = "hp_bank"
    SOSKA = "soska"
    OVERWEIGHT = "overweight"
    CLAIM_REWARDS = "claim_rewards"
    CLAIM_MAIL = "claim_mail"
    SPOT_BACK = "spot_back"
    SELL_STASH_BUY = "sell_stash_buy"
    SCHEDULE = "schedule"

PRIORITIES = {
    MonitorType.PVP: 1,
    MonitorType.DEATH: 2,
    MonitorType.HP_BANK: 3,
    MonitorType.SOSKA: 4,
    MonitorType.OVERWEIGHT: 5,
    MonitorType.CLAIM_REWARDS: 6,
    MonitorType.CLAIM_MAIL: 7,
    MonitorType.SPOT_BACK: 8,
    MonitorType.SELL_STASH_BUY: 9,
    MonitorType.SCHEDULE: 10,
}