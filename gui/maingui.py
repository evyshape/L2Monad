from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox, QInputDialog, QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import keyboard
import time
from bot.utils import findAllWindows
from gui.styles import STYLE
from gui.cache import load_cache, save_cache
from gui.single import WindowControlDialog
from bot.controller import ProfileController


class NedoGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("L2Monad")
        self.resize(400, 150)

        self.controller = ProfileController()
        self.cache = load_cache()
        self.profiles = self.controller.profiles

        self.init_ui()
        keyboard.add_hotkey("F10", self.stop_profile)

    def init_ui(self):
        layout = QVBoxLayout()
        font_btn = QFont("Orbitron", 9, QFont.Bold)

        self.btn_otdel = QPushButton("Отдельное управление")
        self.btn_stop_all = QPushButton("STOP ВСЕ")
        self.btn_otdel.setFont(font_btn)
        self.btn_otdel.setCursor(Qt.PointingHandCursor)
        self.btn_otdel.setFixedHeight(25)
        self.btn_otdel.clicked.connect(self.open_otdel)
        layout.addWidget(self.btn_otdel)

        for name, cls in self.profiles.items():
            btn = QPushButton(f"{name} ВСЕ")
            btn.setFont(font_btn)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(25)
            btn.clicked.connect(lambda _, c=cls: self.start_all(c))
            layout.addWidget(btn)

        self.btn_stop_all.setFont(font_btn)
        self.btn_stop_all.setCursor(Qt.PointingHandCursor)
        self.btn_stop_all.setFixedHeight(25)
        self.btn_stop_all.clicked.connect(self.stop_profile)
        layout.addWidget(self.btn_stop_all)

        self.setLayout(layout)
        self.setStyleSheet(STYLE)

    def open_otdel(self):
        self.dlg = WindowControlDialog(self)
        self.dlg.show()

    def start_windows(self, profile_class, nicks):
        self.controller.start_windows(profile_class, nicks)

    def stop_windows(self, nicks):
        self.controller.stop_windows(nicks)

    def start_all(self, profile_class):
        windows = list(findAllWindows().keys())
        if not windows:
            QMessageBox.information(self, "Info", "Окон не найдено")
            return

        profile_name = profile_class.__name__
        if profile_name == "PvPDodge":
            self.start_windows(profile_class, windows)
            return
        else:
            last_value = self.cache.get(profile_name, 1)
            num, ok = QInputDialog.getInt(
                self, "Батчер для ВСЕХ",
                f"Сколько окон запускать одновременно для {profile_name}?",
                last_value, 1
            )
        if not ok:
            return

        self.cache[profile_name] = num
        save_cache(self.cache)

        batches = [windows[i:i + num] for i in range(0, len(windows), num)]

        for batch in batches:
            self.start_windows(profile_class, batch)

            while any(self.controller.is_running(nick) for nick in batch):
                QApplication.processEvents()
                time.sleep(1)

    def stop_profile(self):
        nicks = list(self.controller.bot_manager.bots.keys())
        self.stop_windows(nicks)
