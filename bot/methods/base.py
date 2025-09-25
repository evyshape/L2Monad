from bot.constans import CBT_JP, CBT_RU
from bot.alchemy.alch_cons import ALCH_BUTTONS
from bot.clogger import log

CBT_VERSIONS = {
    "JP": CBT_JP,
    "RU": CBT_RU,
}

def parseCBT(trigger_name, profile=None):
    version = "JP"
    if profile is not None:
        version = getattr(profile.settings, "REGION", "JP").upper()
    d = CBT_VERSIONS.get(version, CBT_JP)

    try:
        coordinates = d[trigger_name]

        if len(coordinates) == 2:
            xy = tuple(map(int, coordinates[0].split(", ")))
            if coordinates[1] == "no":
                rgb = "no"
            else:
                rgb = tuple(map(int, coordinates[1].split(", ")))

            return xy, rgb

    except (KeyError, ValueError, IndexError) as e:
        log(f"parseCBT error: {e} | {trigger_name} | version={version}")

    log(f"parseCBT error | {trigger_name} | version={version}")
    return None, None

def parseAlch(trigger_name):
    try:
        coordinates = ALCH_BUTTONS[trigger_name]

        if len(coordinates) == 2:
            xy = tuple(map(int, coordinates[0].split(", ")))
            if coordinates[1] == "no":
                rgb = "no"
            else:
                rgb = tuple(map(int, coordinates[1].split(", ")))

            return xy, rgb

    except (KeyError, ValueError, IndexError) as e:
        log(f"parseALCH error: {e} | {trigger_name}")

    log(f"parseALCH error | {trigger_name}")
    return None, None
