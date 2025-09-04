from dataclasses import dataclass
from configparser import ConfigParser

parser = ConfigParser()
parser.read("tg.ini")


@dataclass
class Config:
    BOT_TOKEN: str
    ADMINS: list[int]

    #special for my gay bro lime
    PROXY_HOST: str | None = None
    PROXY_PORT: int | None = None
    PROXY_USER: str | None = None
    PROXY_PASS: str | None = None

    STATE: bool = True

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
)
