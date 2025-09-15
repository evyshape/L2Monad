from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QRadioButton, QButtonGroup,
    QPushButton, QHBoxLayout, QWidget, QScrollArea
)
from PyQt5.QtCore import Qt


class Selector(QDialog):
    def __init__(self, new_windows: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("L2Monad | region select")
        self.groups = {}

        main_layout = QVBoxLayout(self)

        msg = QLabel("Нашёл новые окна, настрой плиз регион:")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("font-weight: bold; font-size: 11pt; margin: 6px;")
        main_layout.addWidget(msg)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        vbox = QVBoxLayout(container)

        for nick in new_windows:
            #nasralo govnocodom
            row = QHBoxLayout()
            label = QLabel(nick)
            label.setFixedWidth(120)
            row.addWidget(label)
            group = QButtonGroup(self)
            ru_btn = QRadioButton("RU")
            jp_btn = QRadioButton("JP")
            ru_btn.setChecked(True)
            group.addButton(ru_btn)
            group.addButton(jp_btn)
            row.addWidget(ru_btn)
            row.addWidget(jp_btn)
            row.addStretch()
            row_widget = QWidget()
            row_widget.setLayout(row)
            vbox.addWidget(row_widget)
            self.groups[nick] = group

        vbox.addStretch()
        container.setLayout(vbox)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        main_layout.addWidget(ok, alignment=Qt.AlignCenter)

        self.adjustSize()
        self.resize(self.width() + 40, min(self.height(), 400))

    def get_regions(self) -> dict[str, str]:
        result = {}
        for nick, group in self.groups.items():
            checked = group.checkedButton()
            result[nick] = checked.text() if checked else "RU"
        return result
