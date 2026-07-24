from bot.cbt.cbt import CBT


def _parse_val(coordinates):
    try:
        if len(coordinates) == 2:
            xy = tuple(map(int, coordinates[0].split(", ")))
            if coordinates[1] == "no":
                rgb = "no"
            else:
                rgb = tuple(map(int, coordinates[1].split(", ")))
            return xy, rgb
    except (ValueError, KeyError):
        pass
    return None, None


def _build(region):
    out = {}
    for name, val in CBT.items():
        if isinstance(val, dict):
            raw = val.get(region)
        else:
            raw = val
        out[name] = _parse_val(raw) if raw is not None else (None, None)
    return out


CBT_RU = {k: (v.get("ru") if isinstance(v, dict) else v) for k, v in CBT.items()}
CBT_JP = {k: (v.get("jp") if isinstance(v, dict) else v) for k, v in CBT.items()}

CBT_RU_PARSED = _build("ru")
CBT_JP_PARSED = _build("jp")
