import json
import os
import time

import keyboard
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bot.controller import ProfileController
from bot.utils import findAllWindows
from clogger import log
from gui.cache import load_cache, save_cache
from gui.single import WindowControlDialog
from gui.styles import STYLE, UPD
from updater import needs_update, update, get_my_version


PROJECT_ROOT = os.getcwd()
WINDOWS_CACHE = os.path.join(PROJECT_ROOT, "settings", "gui", "cache", "windows_cache.json")

class UpdateChecker(QThread):
    update_available = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        log("Запустил чекер обнов")
        while self._running:
            try:
                log("Проверяю обновы...")
                if needs_update():
                    log("Доступна обнова! Спавню кнопку")
                    self.update_available.emit()
                else:
                    log(f"Установлена последняя версия бота | {get_my_version()}")
            except Exception:
                pass
            for _ in range(3600):
                if not self._running:
                    break
                time.sleep(1)

    def stop(self):
        log("Стопнул чекер обнов")
        self._running = False

class NedoGui(QWidget):
    def __init__(self, kb: str, m: str):
        super().__init__()
        if kb is not None and m is not None:
            self.setWindowTitle(f"L2Monad | Драйвер OK | Клава {kb} | Мышь {m}")
        else:
            self.setWindowTitle("L2Monad | Драйвер не найден!")

        self.resize(400, 150)
        self.controller = ProfileController()
        self.cache = load_cache()
        self.profiles = self.controller.profiles
        self.load_window_position()
        self.init_ui()
        keyboard.add_hotkey("F10", self.stop_profile)
        self.update_checker = UpdateChecker()
        self.update_checker.update_available.connect(self.show_update_button)
        self.update_checker.start()

    def load_window_position(self):
        if os.path.exists(WINDOWS_CACHE):
            try:
                with open(WINDOWS_CACHE, "r") as f:
                    data = json.load(f)
                pos = data.get("main", {}).get("pos")
                size = data.get("main", {}).get("size")
                if pos:
                    self.move(QPoint(pos[0], pos[1]))
                if size:
                    self.resize(QSize(size[0], size[1]))
            except:
                pass

    def save_window_position(self):
        data = {"main": {}, "single": {}}
        if os.path.exists(WINDOWS_CACHE):
            try:
                with open(WINDOWS_CACHE, "r") as f:
                    data = json.load(f)
            except:
                pass
        data["main"]["pos"] = [self.pos().x(), self.pos().y()]
        data["main"]["size"] = [self.size().width(), self.size().height()]
        os.makedirs(os.path.dirname(WINDOWS_CACHE), exist_ok=True)
        with open(WINDOWS_CACHE, "w") as f:
            json.dump(data, f, indent=2)

    def closeEvent(self, event):
        try:
            self.save_window_position()
        except Exception:
            pass
        if hasattr(self, 'update_checker') and self.update_checker.isRunning():
            self.update_checker.stop()
            self.update_checker.wait(100)
        super().closeEvent(event)

    def init_ui(self):
        self.layout_main = QVBoxLayout()
        font_btn = QFont("Orbitron", 9, QFont.Bold)

        self.btn_otdel = QPushButton("Отдельное управление")
        self.btn_otdel.setFont(font_btn)
        self.btn_otdel.setCursor(Qt.PointingHandCursor)
        self.btn_otdel.setFixedHeight(25)
        self.btn_otdel.clicked.connect(self.open_otdel)
        self.layout_main.addWidget(self.btn_otdel)


        for name, cls in self.profiles.items():
            btn = QPushButton(f"{name} ВСЕ")
            btn.setFont(font_btn)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(25)
            btn.clicked.connect(lambda _, c=cls: self.start_all(c))
            self.layout_main.addWidget(btn)

        self.btn_stop_all = QPushButton("STOP ВСЕ")
        self.btn_stop_all.setFont(font_btn)
        self.btn_stop_all.setCursor(Qt.PointingHandCursor)
        self.btn_stop_all.setFixedHeight(25)
        self.btn_stop_all.clicked.connect(self.stop_profile)
        self.layout_main.addWidget(self.btn_stop_all)

        version = QLabel(f"v{get_my_version()} | tg: @BotLineage2M")
        version.setStyleSheet("color: gray; font-size: 8pt;")
        version.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        self.layout_main.addWidget(version)

        self.setLayout(self.layout_main)
        self.setStyleSheet(STYLE)

        if needs_update():
            self.show_update_button()

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

    def show_update_button(self):
        if hasattr(self, 'btn_update'):
            return

        self.btn_update = QPushButton("♿️ Доступна обнова! (жми)")
        self.btn_update.setCursor(Qt.PointingHandCursor)
        self.btn_update.setFixedHeight(18)
        self.btn_update.setFixedWidth(180)
        self.btn_update.setStyleSheet(UPD)
        self.btn_update.clicked.connect(self.show_update)
        self.layout().addWidget(self.btn_update, alignment=Qt.AlignRight)

    def show_update(self):
        reply = QMessageBox.question(
            self,
            "Обнова!",
            "Качаем и ставим?\nНа всякий случай сохрани\nвсю папочку settings и файл tg.ini",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            msg = QMessageBox(self)
            msg.setWindowTitle("Обнове быть!")
            msg.setText("Все гуд, бот сам перезапустится через несколько секунд\nТекущее окно зависнет, НЕ ТРОГАЙ ЕГО")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setModal(False)
            msg.show()
            QTimer.singleShot(10, update)