import json
import os
import time
import keyboard

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QSize
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QDialog,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bot.controller import ProfileController
from bot.utils import findAllWindows
from bot.windows.settings_loader import load_settings
from bot.clogger import log
from gui.cache import load_cache, save_cache
from gui.single import WindowControlDialog
from gui.alch_gui import AlchemyDialog
from gui.alch_presets import PresetDialog
from gui.settings_changer import SettingsChanger
from gui.styles import STYLE, UPD
from gui.donate import Donate
from gui.windows_selector import WorkAccs
from gui.windows_selector import load_workaccs
from gui.region_selector import Selector
from bot.updater import needs_update, update, get_my_version


PROJECT_ROOT = os.getcwd()
WINDOWS_CACHE = os.path.join(PROJECT_ROOT, "settings", "gui", "windows_cache.json")
FAVICON = os.path.join(os.path.dirname(__file__), 'images', 'favicon.ico')


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
        if m is not None:
            self.setWindowTitle(f"L2Monad | OK | Клава {kb} | Мышь {m}")
        else:
            # жаль никогда не случится =(
            self.setWindowTitle("L2Monad | Драйвер не найден!")

        self.resize(400, 150)
        self.setWindowIcon(QIcon(FAVICON))
        self.controller = ProfileController()
        self.cache = load_cache()
        self.profiles = self.controller.profiles
        self.load_window_position()
        self.init_ui()
        keyboard.add_hotkey("F10", self.stop_profile) # это кто-то юзает?
        self.update_checker = UpdateChecker()
        self.update_checker.update_available.connect(self.show_update_button)
        self.update_checker.start()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_state)
        self.update_timer.start(1000)

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

            if name == "MainAlchemy":
                btn.clicked.connect(lambda _, c=cls: self.start_alchemy(c))
            else:
                btn.clicked.connect(lambda _, c=cls: self.start_all(c))

            self.layout_main.addWidget(btn)

        self.btn_stop_all = QPushButton("STOP ВСЕ")
        self.btn_stop_all.setFont(font_btn)
        self.btn_stop_all.setCursor(Qt.PointingHandCursor)
        self.btn_stop_all.setFixedHeight(25)
        self.btn_stop_all.clicked.connect(self.stop_profile)
        self.layout_main.addWidget(self.btn_stop_all)

        layout_mini = QHBoxLayout()

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setFixedSize(30, 30)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.clicked.connect(self.open_settings)
        layout_mini.addWidget(self.btn_settings, alignment=Qt.AlignLeft)

        self.windows_sel = QPushButton("👤")
        self.windows_sel.setFixedSize(30, 30)
        self.windows_sel.setCursor(Qt.PointingHandCursor)
        self.windows_sel.clicked.connect(self.winsel)
        layout_mini.addWidget(self.windows_sel, alignment=Qt.AlignLeft)

        self.don = QPushButton("💰")
        self.don.setFixedSize(30, 30)
        self.don.setCursor(Qt.PointingHandCursor)
        self.don.clicked.connect(self.donate)
        layout_mini.addWidget(self.don, alignment=Qt.AlignLeft)

        version = QLabel(f"v{get_my_version()} | tg: @BotLineage2M")
        version.setStyleSheet("color: gray; font-size: 8pt;")
        version.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout_mini.addWidget(version, stretch=1)

        self.layout_main.addLayout(layout_mini)

        self.setLayout(self.layout_main)
        self.setStyleSheet(STYLE)

        if needs_update():
            self.show_update_button()

    def start_alchemy(self, profile_class):
        dlg = AlchemyDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return

        selected = dlg.get_selected()
        if not selected:
            QMessageBox.information(self, "Info", "Окна не выбраны")
            return

        preset_dlg = PresetDialog(self)
        if preset_dlg.exec_() != QDialog.Accepted:
            return

        preset = preset_dlg.get_selected()
        if not preset:
            QMessageBox.information(self, "Info", "Пресет не выбран")
            return

        windows_map = findAllWindows()
        nicks = [nick for nick in selected if nick in windows_map]
        if not nicks:
            QMessageBox.information(self, "Info", "Выбранные окна не найдены")
            return

        new_windows = [nick for nick in nicks if load_settings(nick) is None]
        if new_windows:
            regions = self.ask_region(new_windows)
            for nick, region in regions.items():
                load_settings(nick, region=region)

        self.start_windows(profile_class, nicks, preset=preset)

    def open_settings(self):
        self.settings_win = SettingsChanger()
        self.settings_win.setWindowModality(Qt.NonModal)
        self.settings_win.show()

    def winsel(self):
        dlg = WorkAccs(self)
        dlg.exec_()

    def donate(self):
        dlg = Donate(self)
        dlg.exec_()

    def open_otdel(self):
        self.dlg = WindowControlDialog(self)
        self.dlg.show()

    def start_windows(self, profile_class, nicks, **kwargs):
        self.controller.start_windows(profile_class, nicks, **kwargs)

    def stop_windows(self, nicks):
        self.controller.stop_windows(nicks)

    def start_all(self, profile_class):
        windows = list(findAllWindows().keys())
        if not windows:
            QMessageBox.information(self, "Info", "Окон не найдено")
            return

        work = load_workaccs()
        enabled = set(work.get("enabled", []))
        windows = [w for w in windows if w in enabled]

        if not windows:
            QMessageBox.information(self, "Info", "Готовых к запуску окон не найдено\nНастрой их в кнопке на 1 правее настроек!")
            return

        new_windows = [nick for nick in windows if load_settings(nick) is None]
        if new_windows:
            regions = self.ask_region(new_windows)
            for nick, region in regions.items():
                load_settings(nick, region=region)

        profile_name = profile_class.__name__

        if profile_name == "PvPDodge":
            self.start_windows(profile_class, windows)
            return

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

        def process_batch(batch_idx=0):
            if batch_idx >= len(batches):
                return

            batch = batches[batch_idx]
            self.start_windows(profile_class, batch)

            def wait_c():
                if any(self.controller.bot_manager.get_bot(nick) is None for nick in batch):
                    QTimer.singleShot(500, wait_c)
                else:
                    wait_f()

            def wait_f():
                if any(self.controller.is_running(nick) for nick in batch):
                    QTimer.singleShot(1000, wait_f)
                else:
                    process_batch(batch_idx + 1)

            wait_c()
        process_batch()

    def stop_profile(self):
        nicks = list(self.controller.bot_manager.bots.keys())
        self.stop_windows(nicks)

    def ask_region(self, new_windows: list[str]) -> dict[str, str]:
        dlg = Selector(new_windows, self)
        if dlg.exec_() == QDialog.Accepted:
            return dlg.get_regions()

        return {nick: "RU" for nick in new_windows}

    def update_state(self):
        active = self.controller.bot_manager.bots
        running = {}

        for bot in active.values():
            profile_name = type(bot).__name__
            running[profile_name] = running.get(profile_name, 0) + 1

        for i in range(self.layout_main.count()):
            item = self.layout_main.itemAt(i)
            w = item.widget()
            if isinstance(w, QPushButton) and "ВСЕ" in w.text() and not "STOP ВСЕ" in w.text(): # эбат накостылил, потом переделать #todo
                base_text = w.text().split(" (")[0]
                profile_name = base_text.replace(" ВСЕ", "")
                count = running.get(profile_name, 0)
                w.setText(f"{base_text} ({count})")

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
            "Качаем и ставим?\n\nСохраненный бэкап будет в папочке /backups",
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