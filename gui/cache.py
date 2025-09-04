import json
import os

CACHE_FILE = os.path.join("settings", "gui", "gui_cache.json")
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(data: dict):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"{e}")
        exit()
