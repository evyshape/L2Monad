import json
import os
from functools import partial

from PyQt5.QtCore import QTimer, Qt, QPoint, QSize
from PyQt5.QtGui import QFont, QIcon, QFontMetrics
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget as QW,
    QSizePolicy,
)

from bot.windows.settings_loader import load_settings
from bot.controller import ProfileController
from bot.utils import findAllWindows
from gui.styles import STYLE, NICK_STYLE, SCROLL
from gui.region_selector import Selector


PROJECT_ROOT = os.getcwd()
WINDOWS_CACHE = os.path.join(PROJECT_ROOT, "settings", "gui", "cache", "windows_cache.json")
FAVICON = os.path.join(os.path.dirname(__file__), 'images', 'favicon.ico')


class WindowControlDialog(QDialog):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.controller = ProfileController()
        self.setWindowTitle("L2Monad | Single")
        self.setWindowIcon(QIcon(FAVICON))
        self.resize(540, 200)
        self.setStyleSheet(STYLE)
        self.window_buttons = {}
        self.window_status = {}
        self.profiles = self.controller.profiles
        self.window_active_profile = {}
        self.load_window_position()
        self._init_ui()
        self._start_timer()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QW()
        self.windows_layout = QVBoxLayout(container)
        self.windows_layout.setSpacing(6)
        self.windows_layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(self.windows_layout)
        scroll.setStyleSheet(SCROLL)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.render()

    def load_window_position(self):
        if os.path.exists(WINDOWS_CACHE):
            try:
                with open(WINDOWS_CACHE, "r") as f:
                    data = json.load(f)
                pos = data.get("single", {}).get("pos")
                size = data.get("single", {}).get("size")
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
        data["single"]["pos"] = [self.pos().x(), self.pos().y()]
        data["single"]["size"] = [self.size().width(), self.size().height()]
        os.makedirs(os.path.dirname(WINDOWS_CACHE), exist_ok=True)
        with open(WINDOWS_CACHE, "w") as f:
            json.dump(data, f, indent=2)

    def closeEvent(self, event):
        try:
            self.save_window_position()
        except Exception:
            pass
        super().closeEvent(event)

    def _start_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(100)

    def render(self):
        while self.windows_layout.count():
            w = self.windows_layout.takeAt(0).widget()
            if w:
                w.setParent(None)

        windows = list(findAllWindows().items())
        if not windows:
            self.windows_layout.addWidget(QLabel("Окон не найдено"))
            return

        for nick, info in windows:
            self.windows_layout.addWidget(self._row_spawn(nick))

    def _row_spawn(self, nick):
        row = QW()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        nick_label = self._create_label(nick, width=120, bold=True, style=NICK_STYLE)
        status_label = self._create_label("Остановлено", width=100, bold=True,
                                          color="red")

        active_profile = self._create_label("", width=120, bold=True, color="#00ff00")
        active_profile.setVisible(False)

        profile_buttons = []
        for name, cls in self.profiles.items():
            if name in ["MainAlchemy"]:
                continue

            btn = self._create_button(name, partial(self.start_profile, nick, cls,
                                                    active_profile, name))
            btn.setMinimumWidth(60)
            btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            profile_buttons.append(btn)

        stop_button = self._create_button("STOP", partial(self.stop_profile, nick,
                                                          active_profile))
        stop_button.setFixedWidth(70)

        layout.addWidget(nick_label)
        layout.addWidget(status_label)
        for btn in profile_buttons:
            layout.addWidget(btn)
        layout.addWidget(stop_button)
        layout.addWidget(active_profile)
        layout.addStretch()

        self.window_buttons[nick] = {"profiles": profile_buttons, "stop": stop_button}
        self.window_status[nick] = status_label
        self.window_active_profile = {nick: active_profile}
        self.update_buttons(nick)
        return row

    def _create_label(self, text, width=None, bold=False, color="white", style=None):
        label = QLabel(text)
        if width:
            label.setFixedWidth(width)
        label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(bold)
        label.setFont(font)
        if style:
            label.setStyleSheet(style)
        else:
            label.setStyleSheet(f"color: {color}; font-weight: {'bold' if bold else 'normal'};")
        return label

    def _create_button(self, text, callback):
        btn = QPushButton(text)
        fm = QFontMetrics(btn.font())
        text_width = fm.width(text) + 24
        btn.setMinimumWidth(text_width)
        btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn.clicked.connect(callback)
        return btn

    def refresh_status(self):
        for nick in list(self.window_buttons.keys()):
            self.update_buttons(nick)

    def update_buttons(self, nick):
        windows = findAllWindows()
        if nick not in windows:
            self._remove_window_row(nick)
            return

        running = self.controller.is_running(nick)
        buttons = self.window_buttons.get(nick)
        status = self.window_status.get(nick)
        label = self.window_active_profile.get(nick)

        if not buttons or not status:
            return

        for btn in buttons["profiles"]:
            btn.setVisible(not running)
        buttons["stop"].setVisible(running)

        status.setText("Запущено" if running else "Остановлено")
        status.setStyleSheet(
            f"color: {'#00ff00' if running else '#ff0000'}; font-weight: bold;")

        if label:
            label.setVisible(running)
            if not running:
                label.setText("")

    def _remove_window_row(self, nick):
        for i in reversed(range(self.windows_layout.count())):
            item = self.windows_layout.itemAt(i)
            widget = item.widget()
            if widget:
                label = widget.findChild(QLabel)
                if label and label.text() == nick:
                    self.windows_layout.takeAt(i)
                    widget.setParent(None)
                    break

        self.window_buttons.pop(nick, None)
        self.window_status.pop(nick, None)
        self.window_active_profile.pop(nick, None)

    def start_profile(self, nick, profile_class, label, profile_name):
        settings = load_settings(nick)
        if not settings:
            dlg = Selector([nick], self)
            if dlg.exec_() == QDialog.Accepted:
                regions = dlg.get_regions()
                region = regions.get(nick, "RU")
            else:
                region = "RU"  # дефолт

            load_settings(nick, region=region)

        label.setText(profile_name)
        self.controller.start_windows(profile_class, [nick])
        QTimer.singleShot(100, lambda: self.update_buttons(nick))

    def stop_profile(self, nick, label):
        self.controller.stop_windows([nick])
        label.setVisible(False)
        QTimer.singleShot(100, lambda: self.update_buttons(nick))

