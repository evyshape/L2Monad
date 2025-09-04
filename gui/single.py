from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget as QW, QFrame, QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from functools import partial
from .styles import STYLE, NICK_STYLE, SCROLL
from bot.utils import findAllWindows
from bot.controller import ProfileController  # синглтон

class WindowControlDialog(QDialog):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.controller = ProfileController()
        self.setWindowTitle("L2Monad | Single")
        self.resize(540, 200)
        self.setStyleSheet(STYLE)

        self.window_buttons = {}
        self.window_status = {}
        self.profiles = self.controller.profiles

        self._init_ui()
        self._start_timer()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QW()
        self.windows_layout = QVBoxLayout(container)
        self.windows_layout.setSpacing(15)
        self.windows_layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(self.windows_layout)
        scroll.setStyleSheet(SCROLL)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.render()

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
        layout.setSpacing(5)
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        nick_label = self._create_label(nick, width=120, bold=True, style=NICK_STYLE)
        status_label = self._create_label("Остановлено", width=80, bold=True, color="red")
        profile_buttons = [self._create_button(name, partial(self.start_profile, nick, cls))
                           for name, cls in self.profiles.items()]
        stop_button = self._create_button("STOP", partial(self.stop_profile, nick))

        layout.addWidget(nick_label)
        layout.addWidget(status_label)
        for btn in profile_buttons:
            layout.addWidget(btn)
        layout.addWidget(stop_button)
        layout.addStretch()

        self.window_buttons[nick] = {"profiles": profile_buttons, "stop": stop_button}
        self.window_status[nick] = status_label
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
        btn.setFixedWidth(60)
        btn.clicked.connect(callback)
        return btn

    def refresh_status(self):
        for nick in self.window_buttons:
            self.update_buttons(nick)

    def update_buttons(self, nick):
        running = self.controller.is_running(nick)
        buttons = self.window_buttons[nick]
        for btn in buttons["profiles"]:
            btn.setVisible(not running)
        buttons["stop"].setVisible(running)

        status = self.window_status[nick]
        status.setText("Запущено" if running else "Остановлено")
        status.setStyleSheet(f"color: {'#00ff00' if running else '#ff0000'}; font-weight: bold;")

    def start_profile(self, nick, profile_class):
        self.update_buttons(nick)
        self.controller.start_windows(profile_class, [nick])

    def stop_profile(self, nick):
        self.controller.stop_windows([nick])
        QTimer.singleShot(100, lambda: self.update_buttons(nick))
