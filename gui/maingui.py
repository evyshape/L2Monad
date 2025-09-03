import asyncio
import threading

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QInputDialog, QMessageBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import keyboard

from clogger import log
from constans import SUPPORTED_REZ
from profiles.BuyerProfile.buyer import Buyer
from profiles.RewardsProfile.rewards import Rewards
from profiles.PvpProfile.pvp import PvPDodge
from bot.utils import findAllWindows
from bot.windows.base import BaseSettings, default_values
from bot.windows.settings_loader import load_settings, save_settings
from .styles import STYLE
from settings.gui.cache import load_cache, save_cache

class NedoGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("nedo vremennoe gui")
        self.resize(270, 50)

        self.current_profile = None
        self.bots = []
        self.tasks = []
        self.loop = asyncio.new_event_loop()
        self.cache = load_cache()

        self.init_ui()
        self.forever()
        keyboard.add_hotkey("F10", self.stop_profile)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        font_btn = QFont("Orbitron", 9, QFont.Bold)

        self.btn_pvp = QPushButton("Dodger")
        self.btn_rewards = QPushButton("Claimer")
        self.btn_buyer = QPushButton("Buyer")
        self.btn_stop = QPushButton("STOP")

        for btn in [self.btn_pvp, self.btn_rewards, self.btn_buyer, self.btn_stop]:
            btn.setFont(font_btn)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(20)

        layout.addWidget(self.btn_pvp)
        layout.addWidget(self.btn_rewards)
        layout.addWidget(self.btn_buyer)
        layout.addWidget(self.btn_stop)

        self.setLayout(layout)

        self.btn_pvp.clicked.connect(lambda: self.start_profile(PvPDodge))
        self.btn_rewards.clicked.connect(lambda: self.ask_bat(Rewards))
        self.btn_buyer.clicked.connect(lambda: self.ask_bat(Buyer))
        self.btn_stop.clicked.connect(self.stop_profile)

        self.setStyleSheet(STYLE)

    async def start_bots(self, pr, bat=None):
        tname = "-Zapuskator-"
        windows = list(findAllWindows().items())
        self.bots.clear()
        self.tasks.clear()
        self.current_profile = pr

        if bat:
            for i in range(0, len(windows), bat):
                batch = windows[i:i + bat]
                batch_bots, batch_tasks = [], []
                for window_nick, window_info in batch:
                    size = window_info["Size"]
                    if size not in SUPPORTED_REZ:
                        log(f"[{window_nick}] Почини разрешение...", tname, "ERROR")
                        continue

                    settings = load_settings(window_nick) or BaseSettings(
                        **default_values)
                    save_settings(window_nick, settings)
                    bot = pr({window_nick: window_info}, settings=settings)
                    batch_bots.append(bot)
                    batch_tasks.append(await bot.on_start())

                self.bots.extend(batch_bots)
                self.tasks.extend(batch_tasks)
                await asyncio.gather(*batch_tasks)
        else:
            for window_nick, window_info in windows:
                size = window_info["Size"]
                if size not in SUPPORTED_REZ:
                    log(f"[{window_nick}] Почини разрешение...", tname, "ERROR")
                    continue

                settings = load_settings(window_nick) or BaseSettings(**default_values)
                save_settings(window_nick, settings)
                bot = pr({window_nick: window_info}, settings=settings)
                self.bots.append(bot)
                self.tasks.append(await bot.on_start())

            await asyncio.gather(*self.tasks)

        self.current_profile = None
        self.bots.clear()
        self.tasks.clear()

    async def stoper(self):
        if self.bots:
            for bot in self.bots:
                await bot.on_stop()
        self.bots.clear()
        self.tasks.clear()
        self.current_profile = None

    def forever(self):
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

    def start_profile(self, pr, bat=None):
        if self.current_profile:
            QMessageBox.information(self, "Info", "Уже запущено какоет говно, жми стоп")
            return
        asyncio.run_coroutine_threadsafe(self.start_bots(pr, bat), self.loop)

    def stop_profile(self):
        if self.current_profile:
            asyncio.run_coroutine_threadsafe(self.stoper(), self.loop)

    def ask_bat(self, pr):
        profile_name = pr.__name__
        last_value = self.cache.get(profile_name, 1)

        num, ok = QInputDialog.getInt(
            self,
            "Батчер",
            f"Сколько обрабатываем за раз для {profile_name}?",
            last_value,
            1
        )
        if ok:
            self.cache[profile_name] = num
            save_cache(self.cache)
            self.start_profile(pr, bat=num)

