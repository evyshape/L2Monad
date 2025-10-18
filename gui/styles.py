STYLE = """
QWidget {
    background-color: #111217;
    color: #00ffcc;
    font-family: 'Segoe UI', 'JetBrains Mono', 'Segoe UI Emoji', monospace;
    font-size: 11pt;
}

QPushButton {
    background-color: #1f1f2f;
    border: 1px solid #00ffcc;
    border-radius: 4px;
    color: #00ffcc;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2c2c3f;
}

QPushButton:pressed {
    background-color: #00ffcc;
    color: #000000;
}
"""

SCROLL = """
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #888;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #555;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
}
"""

NICK_STYLE = """
    QFrame { border: 1px solid white; border-radius: 12px; background-color: transparent; }
"""

UPD = """
    QPushButton {
        background-color: #ffcc00;
        color: black;
        font-size: 8pt;
        font-weight: bold;
        border: 1px solid #aaa;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #ffd633;
    }
"""

ERROR_STYLE = """
QWidget {
    background-color: #1c1c1c;
    color: #ff4c4c;
    font-family: 'Consolas', monospace;
    font-size: 11pt;
}

QMessageBox QLabel {
    color: #ff4c4c;
}

QPushButton {
    background-color: #2e2e2e;
    color: #ff4c4c;
    border: 1px solid #ff4c4c;
    border-radius: 4px;
    padding: 4px 8px;
}

QPushButton:hover {
    background-color: #ff4c4c;
    color: #1c1c1c;
}

QPushButton:pressed {
    background-color: #ff1c1c;
    color: #ffffff;
}
"""

CARD = """
    QFrame {
        border: 1px solid #666;
        border-radius: 2px;
        background-color: #3a3a3a;
    }
    QFrame[selected="true"] {
        background-color: #2a82da;
        border: 2px solid #0077ff;
    }
    QLabel {
        font-size: 9px;
        color: #f0f0f0;
    }
"""

WINDOWS_FRAME = """
    QFrame {
        border: 1px solid #444;
        border-radius: 6px;
        background-color: #151515;
    }
"""

MONITOR = """
    QPushButton {
        background-color: #1f1f2f;
        border: 1px solid #444;
        border-radius: 4px;
        color: #00ffcc;
        font-size: 9pt;
    }
    QPushButton:hover {
        background-color: #2c2c3f;
    }
    QPushButton:checked {
        border: 2px solid #00aaff;
        background-color: #222831;
        color: #ffffff;
    }
"""

PAYMENT_CARD_STYLE = """
QWidget#payment_card {
    background-color: #2a2a2a;
    border: 2px solid #3a3a3a;
    border-radius: 12px;
    padding: 8px;
}
QWidget#payment_card:hover {
    border: 2px solid #4a9eff;
    background-color: #2f2f2f;
}
"""

PAYMENT_VALUE_LABEL_STYLE = """
QLabel {
    color: #4a9eff;
    font-weight: bold;
    padding: 6px 12px;
    background-color: #1a1a1a;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
}
QLabel:hover {
    background-color: #252525;
    border: 1px solid #4a9eff;
}
"""