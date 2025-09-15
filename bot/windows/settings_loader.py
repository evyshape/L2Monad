import json
import os
from bot.windows.base import BaseSettings, default_values
from bot.constans import SETTINGS_DIR

def load_settings(nickname: str, region: str | None = None) -> BaseSettings | None:
    path = os.path.join(SETTINGS_DIR, f"{nickname}.json")
    if not os.path.exists(path):
        if region is None:
            return None

        settings_data = default_values.copy()
        settings_data["REGION"] = region
        settings = BaseSettings(**settings_data)
        save_settings(nickname, settings)
        return settings

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, val in default_values.items():
            data.setdefault(key, val)
        settings = BaseSettings(**data)
        save_settings(nickname, settings)
        return settings
    except Exception:
        return None


def save_settings(nickname: str, settings: BaseSettings) -> None:
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    path = os.path.join(SETTINGS_DIR, f"{nickname}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings.__dict__, f, indent=2, ensure_ascii=False)
