from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QFrame, QScrollArea, QWidget, QGridLayout
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import os

from bot.alchemy.alch_utils import get_monitorss
from bot.utils import findAllWindows
from bot.controller import ProfileController
from gui.styles import STYLE, SCROLL, CARD, WINDOWS_FRAME, MONITOR

FAVICON = os.path.join(os.path.dirname(__file__), 'images', 'favicon.ico')


class AlchemyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("L2Monad | Alchemy")
        self.resize(400, 440)
        self.setWindowIcon(QIcon(FAVICON))
        self.setStyleSheet(STYLE)
        self.controller = ProfileController()
        self.layout = QVBoxLayout(self)
        self.selected_preset = None

        self.monitors = get_monitorss()
        self.windows = findAllWindows()
        self.window_buttons = {}
        self.max_selected = False

        top = QFrame()
        top_l = QHBoxLayout(top)
        for mon in self.monitors["monitors"]:
            card = QFrame()
            card.setProperty("selected", False)
            card.setStyleSheet(CARD)
            card_l = QVBoxLayout(card)
            card_l.setContentsMargins(4, 4, 4, 4)
            card_l.addWidget(QLabel(
                f"{mon['id']}\n"
                f"{mon['res']} | {mon['grid_size']}\n"
                f"Влезет: {mon['grid_all']}\n"
                f"Окон: {mon['l2_count']}"
            ))
            top_l.addWidget(card)
        self.layout.addWidget(top)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #333;")
        self.layout.addWidget(line)

        windows_frame = QFrame()
        windows_frame.setStyleSheet(WINDOWS_FRAME)
        windows_layout = QVBoxLayout(windows_frame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL + """
            QScrollArea {
                border: none;
                background-color: #151515;
            }
        """)
        scroll_content = QWidget()
        scroll_layout = QGridLayout(scroll_content)
        scroll_layout.setSpacing(4)
        scroll_layout.setContentsMargins(6, 6, 6, 6)

        row, col = 0, 0
        for mon in self.monitors["monitors"]:
            for w in mon["l2_windows"]:
                full_title = w["title"]
                nick = next((n for n, info in self.windows.items()
                             if info["Title"] == full_title), full_title)


                if nick == "Lineage2M" or not nick: #kostyl
                    continue

                running = self.controller.is_running(nick)
                if not running:
                    btn = QPushButton(nick)
                    btn.setCheckable(True)
                    btn.setFixedSize(100, 28)
                    btn.setStyleSheet(MONITOR)
                    btn.window_info = {"nick": nick, **w}
                    scroll_layout.addWidget(btn, row, col)
                    self.window_buttons[nick] = btn

                    col += 1
                    if col >= 4:
                        col = 0
                        row += 1

        scroll.setWidget(scroll_content)
        windows_layout.addWidget(scroll)
        self.layout.addWidget(windows_frame)

        hello = QLabel("работает на двух лошадиных силах")
        hello.setAlignment(Qt.AlignCenter)
        hello.setStyleSheet("color: #00ffcc; font-size: 9pt;")

        self.layout.addWidget(hello)

        btns = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btns.addWidget(btn_ok)

        self.btn_max = QPushButton("Выбрать максимум")
        self.btn_max.clicked.connect(self.select_max)
        btns.addWidget(self.btn_max)
        self.layout.addLayout(btns)

    def select_max(self):
        total = sum(mon["grid_all"] for mon in self.monitors["monitors"])
        if total <= 0:
            return

        if self.max_selected:
            for btn in self.window_buttons.values():
                btn.setChecked(False)
            self.max_selected = False
            self.btn_max.setText("Выбрать максимум")
        else:
            chosen = []
            for nick, info in self.windows.items():
                if len(chosen) >= total:
                    break
                chosen.append(nick)

            for btn in self.window_buttons.values():
                btn.setChecked(btn.window_info['nick'] in chosen)

            self.max_selected = True
            self.btn_max.setText("Снять со всех") # надо сделать чтоб окон 0 то просто не работала кнопка

    def get_selected(self):
        return [btn.window_info['nick'] for btn in self.window_buttons.values() if btn.isChecked()]

