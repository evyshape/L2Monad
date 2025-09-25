import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QScrollArea, QWidget, QFrame
)
from PyQt5.QtGui import (
    QFont, QColor, QSyntaxHighlighter, QTextCharFormat,
    QPixmap, QPainter, QIcon
)
from PyQt5.QtCore import Qt, QSize, QRegExp
from gui.styles import STYLE, SCROLL

PRESET_DIR = os.path.join("settings", "alchemy")


class Highlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.rules = []

        key_fmt = QTextCharFormat()
        key_fmt.setForeground(QColor("#FFA500"))
        key_fmt.setFontWeight(QFont.Bold)

        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#00FF88"))

        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#33CCFF"))

        bool_fmt = QTextCharFormat()
        bool_fmt.setForeground(QColor("#FF5555"))
        bool_fmt.setFontWeight(QFont.Bold)

        self.rules.append((QRegExp('"(\\\\.|[^"\\\\])*"(?=\\s*:)'), key_fmt))
        self.rules.append((QRegExp('"(\\\\.|[^"\\\\])*"(?=\\s*[,}\\]])'), str_fmt))
        self.rules.append((QRegExp('\\b(-?\\d+(\\.\\d*)?)\\b'), num_fmt))
        self.rules.append((QRegExp('\\b(true|false|null)\\b'), bool_fmt))
        #хвала регуляркам

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            idx = pattern.indexIn(text)
            while idx >= 0:
                self.setFormat(idx, pattern.matchedLength(), fmt)
                idx = pattern.indexIn(text, idx + pattern.matchedLength())


class LineNums(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_width(), 0)

    def paintEvent(self, e):
        self.editor.paint_numbers(e)


class JsonEdit(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 10))
        self.setTabStopDistance(4 * self.fontMetrics().width(' '))
        self.highlighter = Highlighter(self.document())

        self.nums = LineNums(self)
        self.blockCountChanged.connect(self.update_width)
        self.updateRequest.connect(self.update_nums)
        self.update_width(0)

    def line_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().width('9') * digits

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.nums.setGeometry(cr.left(), cr.top(), self.line_width(), cr.height())

    def update_width(self, _):
        self.setViewportMargins(self.line_width(), 0, 0, 0)

    def update_nums(self, rect, dy):
        if dy:
            self.nums.scroll(0, dy)
        else:
            self.nums.update(0, rect.y(), self.nums.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_width(0)

    def paint_numbers(self, e):
        painter = QPainter(self.nums)
        painter.fillRect(e.rect(), QColor(30, 30, 30))
        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= e.rect().bottom():
            if block.isVisible() and bottom >= e.rect().top():
                painter.setPen(Qt.white)
                painter.drawText(0, top, self.nums.width() - 2, self.fontMetrics().height(), Qt.AlignRight, str(num + 1))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            num += 1


class EditPreset(QDialog):
    def __init__(self, path):
        super().__init__()
        self.setWindowTitle(f"L2Monad | {os.path.basename(path)}")
        self.resize(600, 450)
        self.path = path
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)

        self.editor = JsonEdit()
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(json.dumps(json.load(f), indent=2, ensure_ascii=False))
        except Exception as e:
            self.editor.setPlainText(f"Ошибка загрузки: {e}")

        label = QLabel(
            "BLESS - свечение, может быть gold,white,blue ЛИБО всем сразу через запятую"
        )
        label.setAlignment(Qt.AlignCenter)
        label.setFixedHeight(28)
        label.setStyleSheet(
            "background:#FFD700; color:black; border-radius:6px; font-weight:bold; padding:4px 8px;"
        )
        layout.addWidget(label)
        layout.addWidget(self.editor)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Сохранить")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(STYLE)
        save_btn.clicked.connect(self.save)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(STYLE)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def save(self):
        try:
            data = json.loads(self.editor.toPlainText())
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.accept()
        except Exception as e:
            self.editor.appendPlainText(f"\nОшибка сохранения: {e}")


def icon(svg, color):
    pix = QPixmap(svg)
    painter = QPainter(pix)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pix.rect(), QColor(color))
    painter.end()
    return QIcon(pix)

# можно было не костылить этот треш а просто скачать сразу покрашенные иконки 0_0
class SvgBtn(QPushButton):
    def __init__(self, svg, base, hover, tip=""):
        super().__init__()
        self.svg, self.base, self.hover = svg, base, hover
        self.setToolTip(tip) # не придумал подсказки потом добавлю
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(icon(svg, base))
        self.setIconSize(QSize(18, 18))
        self.setStyleSheet("border:none; border-radius:14px; background:rgba(50,50,50,0.3);")

    def enterEvent(self, e):
        self.setIcon(icon(self.svg, self.hover))
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setIcon(icon(self.svg, self.base))
        super().leaveEvent(e)


class Card(QFrame):
    def __init__(self, name, desc, dlg):
        super().__init__()
        self.setStyleSheet("QFrame{background:rgba(255,255,255,0.035); border-radius:12px;} QFrame:hover{background:rgba(255,255,255,0.07);}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        lbl = QLabel(name)
        lbl.setStyleSheet("font-weight:600; font-size:10.5pt; color:#eee;")
        top.addWidget(lbl)
        top.addStretch()

        ok_btn = QPushButton()
        ok_btn.setIcon(icon("gui/images/ok.svg", "#00ff88"))
        ok_btn.setIconSize(QSize(16, 16))
        ok_btn.setFixedSize(28, 28)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("border:none; border-radius:14px; background:rgba(50,50,50,0.3);")
        ok_btn.clicked.connect(lambda: dlg.select(name))
        top.addWidget(ok_btn)

        edit_btn = QPushButton()
        edit_btn.setIcon(icon("gui/images/pen.svg", "#ffaa00"))
        edit_btn.setIconSize(QSize(16, 16))
        edit_btn.setFixedSize(28, 28)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet("border:none; border-radius:14px; background:rgba(50,50,50,0.3);")
        edit_btn.clicked.connect(lambda: dlg.edit(name))
        top.addWidget(edit_btn)

        layout.addLayout(top)
        d_lbl = QLabel(desc)
        d_lbl.setWordWrap(True)
        d_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        d_lbl.setStyleSheet("font-size:9pt; color:rgba(220,220,220,0.55);")
        layout.addWidget(d_lbl)


class PresetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("L2Monad | Alchemy")
        self.resize(400, 460)
        self.sel = None
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(SCROLL)
        self.content = QWidget()
        self.vbox = QVBoxLayout(self.content)
        self.vbox.setSpacing(12)
        self.vbox.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self.scroll)
        self.setLayout(layout)

        self.reload_cards()

    def reload_cards(self):
        for i in reversed(range(self.vbox.count())):
            item = self.vbox.takeAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if os.path.exists(PRESET_DIR):
            for f in os.listdir(PRESET_DIR):
                if f.endswith(".json"):
                    path = os.path.join(PRESET_DIR, f)
                    try:
                        data = json.load(open(path, encoding="utf-8"))
                    except:
                        continue
                    card = Card(f, data.get("DESCRIPTION", "Без описания, добавь ченить плиз..."), self)
                    self.vbox.addWidget(card)

        self.vbox.addStretch()
        self.scroll.setWidget(self.content)

    def select(self, name):
        self.sel = name
        self.accept()

    def edit(self, name):
        path = os.path.join(PRESET_DIR, name)
        dlg = EditPreset(path)
        if dlg.exec_():
            self.reload_cards()

    def get_selected(self):
        if not self.sel:
            return None
        path = os.path.join(PRESET_DIR, self.sel)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as ex:
            return None

