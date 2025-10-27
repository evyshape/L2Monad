import os
import requests
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QCursor
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QWidget,
    QApplication,
    QScrollArea,
)

from gui.styles import STYLE, SCROLL, PAYMENT_CARD_STYLE, PAYMENT_VALUE_LABEL_STYLE

FAVICON = os.path.join(os.path.dirname(__file__), 'images', 'favicon.ico')

class CLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.orig = text
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(PAYMENT_VALUE_LABEL_STYLE)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cb = QApplication.clipboard()
            cb.setText(self.orig)
            self.setText("✓ Скопировано!")
            self.setStyleSheet(PAYMENT_VALUE_LABEL_STYLE + "QLabel { color: #00ff00; }")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, self._back)
        super().mousePressEvent(event)

    def _back(self):
        self.setText(self.orig)
        self.setStyleSheet(PAYMENT_VALUE_LABEL_STYLE)


class Donate(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("L2Monad | Donate")
        self.setWindowIcon(QIcon(FAVICON))
        self.resize(550, 650)
        self.setStyleSheet(STYLE + PAYMENT_CARD_STYLE)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header = QLabel("💰 Поддержать Раз Раба")
        header.setFont(QFont("Calibri", 14, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        hint = QLabel("💡 Нажмите на нужное значение, чтобы скопировать")
        hint.setFont(QFont("Calibri", 6))
        hint.setStyleSheet("color: #888888; font-style: italic;")
        hint.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL)

        scroll_c = QWidget()
        scroll_layout = QVBoxLayout(scroll_c)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(15, 8, 15, 8)

        try:
            resp = requests.get("https://gist.githubusercontent.com/evyshape/38de60e1fec5ead6d562451b776c1874/raw/donatilka.json", timeout=5)
            payments = resp.json()
        except Exception:
            payments = {"Методы не загрузились =(": ["Проверь инет либо пиши разрабу в лс (tg: @evyshape)"]}

        for title, vals in payments.items():
            self._add(scroll_layout, title, vals)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_c)
        main_layout.addWidget(scroll)
        hint2 = QLabel("🎩 Возможно когда-то донатерам будут различные плюшки, хз =)")
        hint2.setFont(QFont("Calibri", 12))
        hint2.setStyleSheet("color: #888888; font-style: italic;")
        hint2.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hint2)

    def _add(self, layout, title, value):
        card = QWidget()
        card.setObjectName("payment_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(8)

        label_title = QLabel(title)
        label_title.setFont(QFont("Calibri", 11, QFont.Bold))
        label_title.setStyleSheet(
            "color: #ffffff; background: transparent; border: none;")
        label_title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(label_title)

        # вероятно никогда не случится но пусть будет, вдруг забуду
        if isinstance(value, str):
            value = [value]

        for val in value:
            label_value = CLabel(val)
            label_value.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(label_value)

        layout.addWidget(card)
