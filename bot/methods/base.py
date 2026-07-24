from bot.cbt import CBT_JP, CBT_RU, CBT_JP_PARSED, CBT_RU_PARSED
from bot.alchemy.alch_cons import ALCH_BUTTONS
from bot.clogger import log
from bot.events.enums import Region

CBT_VERSIONS = {
    Region.JP: CBT_JP,
    Region.RU: CBT_RU,
}

CBT_VERSIONS_PARSED = {
    Region.JP: CBT_JP_PARSED,
    Region.RU: CBT_RU_PARSED,
}

def parseCBT(trigger_name, profile=None):
    version = "JP"
    if profile is not None:
        version = getattr(profile.settings, "REGION", "JP").upper()
    d = CBT_VERSIONS_PARSED.get(version, CBT_JP_PARSED)

    result = d.get(trigger_name, (None, None))
    if result[0] is None and result[1] is None:
        log(f"parseCBT error | {trigger_name} | version={version}")
    return result

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
