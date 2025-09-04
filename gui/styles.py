STYLE = """
    QWidget {
        background-color: #111217;
        color: #00ffcc;
    }
    QPushButton {
        background-color: #1f1f2f;
        border: 1px solid #00ffcc;
        border-radius: 4px;
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