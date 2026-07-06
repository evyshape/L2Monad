from bot.cbt.ru import CBT_RU
from bot.cbt.jp import CBT_JP


def _parse_cbt(d):
    parsed = {}
    for name, coordinates in d.items():
        try:
            if len(coordinates) == 2:
                xy = tuple(map(int, coordinates[0].split(", ")))
                if coordinates[1] == "no":
                    rgb = "no"
                else:
                    rgb = tuple(map(int, coordinates[1].split(", ")))
                parsed[name] = (xy, rgb)
            else:
                parsed[name] = (None, None)
        except (KeyError, ValueError):
            parsed[name] = (None, None)
    return parsed


CBT_RU_PARSED = _parse_cbt(CBT_RU)
CBT_JP_PARSED = _parse_cbt(CBT_JP)
