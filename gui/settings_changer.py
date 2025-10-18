from typing import Dict, List

from PyQt5.QtWidgets import (
    QSizePolicy, QGraphicsDropShadowEffect, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QFrame, QMessageBox,
    QDialog, QCheckBox, QSpinBox, QFormLayout, QDialogButtonBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from bot.windows.settings_loader import load_settings, save_settings
from bot.constans import SETTINGS_DIR
from bot.clogger import log
from gui.styles import STYLE, CARD, SCROLL
from PyQt5.QtGui import QIcon
import os


FAVICON = os.path.join(os.path.dirname(__file__), 'images', 'favicon.ico')


class Windowbtnn(QFrame):
    def __init__(self, nick: str, pc: QWidget):
        super().__init__()
        self.nick = nick
        self.pc = pc
        self.selected = False
        self.setWindowIcon(QIcon(FAVICON))
        self.setMinimumHeight(30) # mb сделать ее адаптивной по размеру окна если окон мало будет красивее
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setStyleSheet(CARD)
        self.label = QLabel(nick, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.label.setStyleSheet("font-size: 10px; color: #f0f0f0;")
        self.label.setWordWrap(False)
        self.label.setMinimumWidth(40)
        self.label.setMaximumHeight(20)
        self.label.setToolTip(nick)
        self.label.setText(nick)
        self.label.setProperty("elide", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def resizeEvent(self, event):
        metrics = self.label.fontMetrics()
        elided = metrics.elidedText(self.nick, Qt.ElideRight, self.width() - 6)
        self.label.setText(elided)
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        self.toggle()
        super().mousePressEvent(event)

    def toggle(self):
        self.selected = not self.selected
        self.setProperty("selected", "true" if self.selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

        if self.selected:
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(6)
            glow.setColor(QColor("#3366ff"))
            glow.setOffset(0, 0)
            self.setGraphicsEffect(glow)
        else:
            self.setGraphicsEffect(None)

        self.update()
        self.pc.update_buttons()


class SettingsChanger(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("L2Monad | Settings Changer")
        self.setWindowIcon(QIcon(FAVICON))
        self.resize(600, 500)

        self.btns: Dict[str, Windowbtnn] = {}

        self.btn_edit = QPushButton("✎ Редактировать ")
        self.btn_mass_edit = QPushButton("⚡ Массовый редакт")
        self.btn_rassos = QPushButton("⏱️ Рассосать время")
        self.btn_edit.hide()

        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_mass_edit.clicked.connect(self.mass_apply)
        self.btn_rassos.clicked.connect(self.rassos_times)

        main_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_mass_edit)
        btn_layout.addWidget(self.btn_rassos)
        main_layout.addLayout(btn_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(SCROLL)
        self.jsons = QWidget()
        self.jsons_lay = QGridLayout()
        self.jsons_lay.setSpacing(5)
        self.jsons_lay.setContentsMargins(5, 5, 5, 5)

        self.jsons.setLayout(self.jsons_lay)
        self.scroll.setWidget(self.jsons)
        main_layout.addWidget(self.scroll)

        self.btn_select_all = QPushButton("✅ Выделить все")
        self.btn_select_all.clicked.connect(self.sel_all)
        main_layout.addWidget(self.btn_select_all)

        self.setLayout(main_layout)
        self.setStyleSheet(STYLE)

        self.load()

    def load(self):
        for i in reversed(range(self.jsons_lay.count())):
            widget = self.jsons_lay.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.btns.clear()

        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR, exist_ok=True)

        files = [fn[:-5] for fn in os.listdir(SETTINGS_DIR) if fn.endswith(".json")]
        count = len(files)
        if count == 0:
            return

        #todo подобрать чтоб было красиво и практично?
        max_stlb = 5
        space = 6
        btn_h = 33

        self.jsons_lay.setSpacing(space)
        self.jsons_lay.setContentsMargins(space, space, space, space)

        stlbs = min(count, max_stlb)

        for idx, nick in enumerate(files):
            btnn = Windowbtnn(nick, self)
            btnn.setMinimumHeight(btn_h)
            btnn.setMaximumHeight(btn_h)
            btnn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            row = idx // stlbs
            col = idx % stlbs
            self.jsons_lay.addWidget(btnn, row, col)
            self.btns[nick] = btnn

        for c in range(stlbs):
            self.jsons_lay.setRowStretch(c, 1) # когда окон мало с растягом оч по уродски, мб потом заменить #todo

    def get_selected(self) -> List[str]:
        return [nick for nick, btnn in self.btns.items() if btnn.selected]

    def sel_all(self):
        if len(self.get_selected()) == 0:
            for btnn in self.btns.values():
                if not btnn.selected:
                    btnn.toggle()
        else:
            for btnn in self.btns.values():
                if btnn.selected:
                    btnn.toggle()

        self.update_buttons()


    def update_buttons(self):
        selected = self.get_selected()
        self.btn_edit.setVisible(len(selected) == 1)

        if len(selected) == 0:
            self.btn_select_all.setText("✅ Выделить все")
        else:
            self.btn_select_all.setText("❌ Снять все")

    def edit_selected(self):
        from .editor import Editor
        nicks = self.get_selected()
        if not nicks:
            QMessageBox.warning(self, "Ничего не выбрано", "Выбирай окно")
            return

        nick = nicks[0]
        settings = load_settings(nick)
        #print(settings)
        #print(nick)
        dlg = Editor(nick, settings, self)
        dlg.exec_()
        self.load()
        self.update_buttons()

    def mass_apply(self):
        from .editor import Editor
        nicks = self.get_selected()
        if not nicks:
            QMessageBox.warning(self, "Ничего не выбрано", "Выбирай окна")
            return

        nick = nicks[0]
        settings = load_settings(nick)
        dlg = Editor(nick, settings, self, apply_to=nicks)
        dlg.exec_()
        self.load()
        self.update_buttons()

    def rassos_times(self):
        nicks = self.get_selected() or []
        if len(nicks) < 2:
            QMessageBox.warning(self, "Выбор окон", "Выбирай окнА (минимум 2)")
            return

        base_nick = nicks[0]
        base_settings = load_settings(base_nick)
        dlg = Rassoser(base_settings, nicks, self)
        dlg.exec_()
        self.load()
        self.update_buttons()


class Rassoser(QDialog):
    def __init__(self, base_settings, nicks: List[str], parent=None):
        super().__init__(parent)
        self.base_settings = base_settings
        self.nicks = nicks
        self.setWindowTitle("L2Monad | Settings Rassos")
        self.resize(400, 300)
        self.setWindowIcon(QIcon(FAVICON))

        self.checks: Dict[str, QCheckBox] = {}
        box = QGroupBox("Выбирай поля")
        box_layout = QVBoxLayout()
        for field in ["SCHEDULE_BUYING", "SCHEDULE_MAIL", "SCHEDULE_REWARDS",
                      "SCHEDULE_SCHEDULE", "SCHEDULE_AUCTION"]:
            cb = QCheckBox(field)
            box_layout.addWidget(cb)
            self.checks[field] = cb
        box.setLayout(box_layout)

        self.sbox = QSpinBox()
        self.sbox.setValue(1)
        self.sbox.setMinimum(1)
        self.sbox.setMaximum(100)

        self.sstep = QSpinBox()
        self.sstep.setValue(1)
        self.sstep.setMaximum(60)

        form = QFormLayout()
        form.addRow("Окон в пачке:", self.sbox)
        form.addRow("Шаг (минут):", self.sstep)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.apply)
        bbox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(box)
        layout.addLayout(form)
        layout.addWidget(bbox)
        self.setLayout(layout)
        self.setStyleSheet(STYLE)

    def apply(self):
        fields = [f for f, cb in self.checks.items() if cb.isChecked()]
        if not fields:
            QMessageBox.warning(self, "Втф?", "Рассасывать нечего, выбери поля")
            return

        bsize = self.sbox.value()
        step = self.sstep.value()

        for field in fields:
            base_val = getattr(self.base_settings, field, "")
            times = base_val.split("|")

            for idx, nick in enumerate(self.nicks):
                settings = load_settings(nick)
                if settings is None:
                    continue

                shifted = []
                for t in times:
                    try:
                        hh, mm = map(int, t.split(":"))
                        group_idx = idx // bsize
                        mm += group_idx * step
                        hh += mm // 60
                        mm = mm % 60
                        hh = hh % 24
                        shifted.append(f"{hh:02d}:{mm:02d}")
                    except:
                        shifted.append(t)

                setattr(settings, field, "|".join(shifted))
                save_settings(nick, settings)
                log(f"Рассосал {nick}: {field} = {getattr(settings, field)}")

        QMessageBox.information(self, "OK", "Рассосыч успешен!")
        self.accept()
