from constans import CBT_JP
from clogger import log

def parseCBT(trigger_name):
    try:
        coordinates = CBT_JP[trigger_name]

        if len(coordinates) == 2:
            xy = tuple(map(int, coordinates[0].split(", ")))
            if coordinates[1] == "no":
                rgb = "no"
            else:
                rgb = tuple(map(int, coordinates[1].split(", ")))

            return xy, rgb

    except (KeyError, ValueError, IndexError) as e:
        log(f"parseCBT error: {e} | {trigger_name}")

    log(f"parseCBT error | {trigger_name}")
    return None, None