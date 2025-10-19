import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGridLayout, QFrame, QMessageBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from bot.utils import findAllWindows
from gui.styles import STYLE, SCROLL, CARD, WINDOWS_FRAME, MONITOR

FAVICON = os.path.join(os.path.dirname(__file__), 'images', 'favicon.ico')
WORKACCS_PATH = os.path.join(os.getcwd(), "settings", "gui", "workaccs.json")


def load_workaccs() -> dict:
    if os.path.exists(WORKACCS_PATH):
        try:
            with open(WORKACCS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # ну а хули вы хотели, хотя мб можно просто все текущие окна вернуть да и все потом подумаю
    return {"enabled": []}


def save_workaccs(data: dict):
    os.makedirs(os.path.dirname(WORKACCS_PATH), exist_ok=True)
    with open(WORKACCS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class WorkAccs(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("L2Monad | Windows selector")
        self.resize(400, 440)
        self.setWindowIcon(QIcon(FAVICON))
        self.setStyleSheet(STYLE)

        self.windows = findAllWindows()
        self.workaccs = load_workaccs()
        self.enabled = set(self.workaccs.get("enabled", []))

        self.layout = QVBoxLayout(self)
        self.window_buttons = {}
        self.init_ui()

    def init_ui(self):
        top_label = QLabel("Выбирай рабочие окна:")
        top_label.setStyleSheet("color: #00ffcc; font-size: 9pt;")
        top_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(top_label)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #333;")
        self.layout.addWidget(line)

        windows_frame = QFrame()
        windows_frame.setStyleSheet(WINDOWS_FRAME)
        windows_layout = QVBoxLayout(windows_frame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL)

        scroll_content = QWidget()
        scroll_layout = QGridLayout(scroll_content)
        scroll_layout.setHorizontalSpacing(6)
        scroll_layout.setVerticalSpacing(4)
        scroll_layout.setContentsMargins(6, 6, 6, 6)

        row, col = 0, 0
        for nick, info in self.windows.items():
            if not nick or nick == "Lineage2M": # DA ETO JESKO
                continue

            btn = QPushButton(nick)
            btn.setCheckable(True)
            btn.setFixedSize(110, 30)
            btn.setStyleSheet(MONITOR)
            btn.window_info = info
            btn.setChecked(nick in self.enabled)
            btn.clicked.connect(self.on_clicked)
            scroll_layout.addWidget(btn, row, col)
            self.window_buttons[nick] = btn

            col += 1
            if col >= 3:
                col = 0
                row += 1

        scroll.setWidget(scroll_content)
        windows_layout.addWidget(scroll)
        self.layout.addWidget(windows_frame)

        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("color: #333;")
        self.layout.addWidget(line2)

        btns = QHBoxLayout()

        self.btn_toggle_all = QPushButton()
        self.update_text()
        self.btn_toggle_all.clicked.connect(self.toggle_all)
        btns.addWidget(self.btn_toggle_all)

        self.btn_ok = QPushButton("Сохранить (не забудь нажать)")
        self.btn_ok.clicked.connect(self.accept)
        btns.addWidget(self.btn_ok)

        self.layout.addLayout(btns)

    def toggle_all(self):
        if any(btn.isChecked() for btn in self.window_buttons.values()):
            for btn in self.window_buttons.values():
                btn.setChecked(False)
            self.enabled.clear()
        else:
            for nick, btn in self.window_buttons.items():
                btn.setChecked(True)
                self.enabled.add(nick)

        self.update_text()

    def update_text(self):
        if any(btn.isChecked() for btn in self.window_buttons.values()):
            self.btn_toggle_all.setText("Снять все")
        else:
            self.btn_toggle_all.setText("Выбрать все")

    def on_clicked(self):
        nick = self.sender().text()
        if self.sender().isChecked():
            self.enabled.add(nick)
        else:
            self.enabled.discard(nick)

        self.update_text()

    def select_all(self):
        self.enabled = set(self.window_buttons.keys())
        for btn in self.window_buttons.values():
            btn.setChecked(True)

    def clear_all(self):
        self.enabled.clear()
        for btn in self.window_buttons.values():
            btn.setChecked(False)

    def accept(self):
        if not self.enabled:
            reply = QMessageBox.question(
                self, "Подтверждалка",
                "Ты не окон выбрал, ниче не будет работать, все ок?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        save_workaccs({"enabled": list(self.enabled)})
        super().accept()

    def get_enabled(self):
        return list(self.enabled)
