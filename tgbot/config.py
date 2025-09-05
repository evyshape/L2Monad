from dataclasses import dataclass
from configparser import ConfigParser
from pathlib import Path

INI_PATH = Path("tg.ini")
parser = ConfigParser()
parser.read(INI_PATH)

def load_notify() -> dict[str, bool]:
    if parser.has_section("notifications"):
        return {
            level.lower(): parser.getboolean("notifications", level, fallback=True)
            for level, _ in parser.items("notifications")
        }
    return {
        "info": True,
        "warning": True,
        "error": True,
        "trash": False,
        "photo": True,
    }

def save_notify(levels: dict[str, bool]) -> dict[str, bool]:
    if not parser.has_section("notifications"):
        parser.add_section("notifications")

    for level, enabled in levels.items():
        parser.set("notifications", level.lower(), str(enabled))

    with open(INI_PATH, "w") as f:
        parser.write(f)

    return levels

notify_levels = load_notify()

@dataclass
class Config:
    BOT_TOKEN: str
    ADMINS: list[int]

    PROXY_HOST: str | None = None
    PROXY_PORT: int | None = None
    PROXY_USER: str | None = None
    PROXY_PASS: str | None = None

    STATE: bool = True
    NOTIFY_LEVELS: dict[str, bool] = None

    @property
    def proxy_url(self) -> str | None:
        if not self.PROXY_HOST or not self.PROXY_PORT:
            return None

        auth = ""
        if self.PROXY_USER and self.PROXY_PASS:
            auth = f"{self.PROXY_USER}:{self.PROXY_PASS}@"

        return f"http://{auth}{self.PROXY_HOST}:{self.PROXY_PORT}"

config = Config(
    BOT_TOKEN=parser.get("bot", "token"),
    ADMINS=[int(i.strip()) for i in parser.get("bot", "admins").split(",")],
    PROXY_HOST=parser.get("proxy", "host", fallback=None),
    PROXY_PORT=int(parser.get("proxy", "port", fallback=0)) if parser.get("proxy", "port") else None,
    PROXY_USER=parser.get("proxy", "user", fallback=None),
    PROXY_PASS=parser.get("proxy", "pass", fallback=None),
    STATE=parser.getboolean("bot", "state", fallback=True),
    NOTIFY_LEVELS=notify_levels,
)
