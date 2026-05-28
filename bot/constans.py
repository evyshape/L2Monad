import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(ROOT_DIR, "logs")
PROFILES_DIR = os.path.join(ROOT_DIR, "profiles")
SETTINGS_DIR = os.path.join(ROOT_DIR, "settings")
SCREENSHOT_DIR = os.path.join(ROOT_DIR, "screenshots")

# методом getNPCposition - получим список доступных нпс и их позиции
NPCS = [
    "stash", "shop", "buyer"
]

# кнопки в интерфейсе каждого нпс, по ним проверяем что дошли
NPC_CHECK_BUTTONS = {
    "stash": "npc_stash_button_1",
    "shop": "npc_shop_button_1",
    "buyer": "npc_buyer_button_1",
}

PARTY_DUNGEON_CONS = {
    "RU": {
        "need": ["163, 166, 171", "78, 83, 90", "153, 155, 157", "65, 68, 72", "190, 193, 197"],
        "x": 174,
        "scroll": [45, 200],
        "portal": ["75-170, 25", "255, 255, 255"],
    },
    "JP": {
        "need": ["163, 166, 171", "78, 83, 90", "153, 155, 157", "65, 68, 72", "190, 193, 197"],
        "x": 166,
        "scroll": [45, 200],
        "portal": ["75-170, 26", "255, 255, 255"],
    },
}


BATTLE_PASS = {
    "red_dot_clr_podvkladka": ["140, 17, 13"], # красная точка на подвкладке
    "red_dot_clr_vkladka": ["184, 13, 10"], # красные точки по всей ширине основных вкладок сверху
    "y_vkladki": 25, # высота от левого верхного края окна игры, на этой высоте ищем от 1 координаты до 425 красные точки чтоб поняыть сколько вкладок бп актуально
    "x_podvkladki": 15 # ширина окна, по вертикали бегаем ищем подвкладки
}

DAILY = {
    "RU": {
        "red_dot_clr": ["182, 4, 5"], # красная точка на вкладке
        "y_vkladki": 395,  # ширина окна

        "almaz_donate": ["156, 174, 198"], # внутри вкладки дейлика алмазик в кнопке
        "monetka_donate": ["247, 200, 112"], # внутри вкладки дейлика монетка в кнопке
        "donate_monetka_supermonetka": ["117, 79, 36"], # говно донатное не адена
        "monetka_proverka": ["246, 114", "176, 119, 33"],
        "confirm_buy_daily": ["234, 151", "206, 89, 8"],

        "claim_daily": ["207, 90, 8"],

        "start_button_1": 94,
        "end_button_1": 105,
        "start_button_2": 182,
        "end_button_2": 193
    },

    "JP": {
        "red_dot_clr": ["182, 4, 5"], # красная точка на вкладке
        "y_vkladki": 395,  # ширина окна

        "almaz_donate": ["156, 174, 198"], # внутри вкладки дейлика алмазик в кнопке
        "monetka_donate": ["247, 200, 112"], # внутри вкладки дейлика монетка в кнопке
        "donate_monetka_supermonetka": ["117, 79, 36"], # говно донатное не адена
        "monetka_proverka": ["246, 114", "176, 119, 33"],
        "confirm_buy_daily": ["234, 151", "206, 89, 8"],

        "claim_daily": ["207, 90, 8"],

        "start_button_1": 94,
        "end_button_1": 105,
        "start_button_2": 182,
        "end_button_2": 193
    }
}

GLOBAL_STATES = [
    "null",
    "afk",
    "combat",
    "shopping",
    "stashing",
    "death",
    "claiming",
    "schedule",
    "pvp",
    "alchemy"
]

#todo мб добавить поддержку других? а надо ли?
SUPPORTED_REZ = [
    "400x225"
]
ALCH_BUTTONS = {}