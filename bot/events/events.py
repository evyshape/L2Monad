from typing import Dict, Any
from profiles.base import BaseProfile
from clogger import log

tname = "-EventsManager-"

class EventsManager:
    _instances: Dict[str, BaseProfile] = {}

    @classmethod
    def register(cls, window_id: str, profile: BaseProfile) -> None:
        cls._instances[window_id] = profile

    @classmethod
    def unregister(cls, window_id: str) -> None:
        cls._instances.pop(window_id, None)

    @classmethod
    def send_event(cls, window_id: str, event: Any) -> None:
        profile = cls._instances.get(window_id)
        if profile:
            log(f"Ивент отправлен в {window_id}: {event}", tname)
            profile.send_event(event)