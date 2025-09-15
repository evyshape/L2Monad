import asyncio
import threading
import ctypes
from bot.clogger import log

from bot.manager import BotManager
from bot.utils import findAllWindows, getProfiles
from bot.constans import SUPPORTED_REZ
from bot.windows.settings_loader import load_settings

class ProfileController:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.bot_manager = BotManager()
            cls._instance.loop = asyncio.new_event_loop()
            cls._instance.profiles = getProfiles()
            threading.Thread(target=cls._instance.loop.run_forever, daemon=True).start()
        return cls._instance

    def start_windows(self, profile_class, nicks):
        async def start_seq():
            windows = findAllWindows()
            tasks = []

            for nick in nicks:
                window_info = windows[nick]
                if window_info["Size"] not in SUPPORTED_REZ:
                    log(f"Окно {nick} имеет насраное разрешение, чини | {window_info['Size']}\nПоддерживаемые: {SUPPORTED_REZ}", level="ERROR")
                    continue

                settings = load_settings(nick)

                task = asyncio.create_task(
                    self.bot_manager.start_bot(profile_class, nick, window_info,
                                               settings)
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

        asyncio.run_coroutine_threadsafe(start_seq(), self.loop)

    def stop_windows(self, nicks):
        for nick in nicks:
            asyncio.run_coroutine_threadsafe(
                self.bot_manager.stop_bot(nick),
                self.loop
            )

    def get_runtime_info(self, nick):
        bot = self.bot_manager.get_bot(nick)
        if not bot:
            return None
        return getattr(bot, "runtime_data", None)

    def is_running(self, nick):
        return self.bot_manager.is_running(nick)

    def close_window(self, nick: str):
        self.stop_windows([nick])

        windows = findAllWindows()
        if nick not in windows:
            log(f"Окно для {nick} не найдено")
            return False

        hwnd = windows[nick]["ID"]
        if not ctypes.windll.user32.IsWindow(hwnd):
            log(f"HWND для {nick} недействителен")
            return False

        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
        log(f"Окно {nick} закрыто")
        return True

    def stop_and_close(self, nicks):
        for nick in nicks:
            self.close_window(nick)