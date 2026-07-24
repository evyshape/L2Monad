import os
import ctypes

from screeninfo import get_monitors
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QGridLayout, QLayout
)
from PyQt5.QtGui import QIcon, QDrag, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QMimeData, QPoint, QRect, QSize, pyqtSignal

from bot.utils import findAllWindows
from gui.cache import load_cache, save_cache

FAVICON = os.path.join(os.path.dirname(__file__), 'images', 'favicon.ico')

CELL_W = 400
CELL_H = 265
TOP_OFFSET = 40
SIDEBAR_W = 56

HWND_TOP = 0
SWP_NOACTIVATE = 0x0010
SWP_NOSIZE = 0x0001
SetWindowPos = ctypes.windll.user32.SetWindowPos


def _move_window(hwnd, x, y):
    try:
        SetWindowPos(hwnd, HWND_TOP, x, y, CELL_W, 225, SWP_NOACTIVATE)
        return True
    except Exception:
        return False


class Panels:
    SW_HIDE = 0
    SW_SHOW = 5
    GW_OWNER = 4
    CLS = "CEFCLIENT"
    TITLE_MATCH = "index.html?type=live"

    def __init__(self):
        from ctypes import wintypes
        u = ctypes.windll.user32
        self._enum = u.EnumWindows
        self._cls = u.GetClassNameW
        self._title = u.GetWindowTextW
        self._vis = u.IsWindowVisible
        self._owner = u.GetWindow
        self._show = u.ShowWindow
        self._proc_t = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def find(self, hwnd):
        got = [None]
        def cb(h, _):
            buf = ctypes.create_unicode_buffer(64)
            self._cls(h, buf, 64)
            if buf.value != self.CLS:
                return True
            t = ctypes.create_unicode_buffer(128)
            self._title(h, t, 128)
            if self.TITLE_MATCH not in t.value:
                return True
            if self._owner(h, self.GW_OWNER) != hwnd:
                return True
            got[0] = h
            return False
        self._enum(self._proc_t(cb), 0)
        return got[0]

    def state(self, hwnd):
        p = self.find(hwnd)
        if not p:
            return None
        return bool(self._vis(p))

    def hide(self, hwnd):
        p = self.find(hwnd)
        if p and self._vis(p):
            self._show(p, self.SW_HIDE)
            return True
        return False

    def show(self, hwnd):
        p = self.find(hwnd)
        if p and not self._vis(p):
            self._show(p, self.SW_SHOW)
            return True
        return False


class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=3):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing

    def addItem(self, item):
        self._items.append(item)
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, idx):
        return self._items[idx] if 0 <= idx < len(self._items) else None

    def takeAt(self, idx):
        if 0 <= idx < len(self._items):
            item = self._items.pop(idx)
            self.invalidate()
            return item
        return None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._do_layout(QRect(0, 0, w, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize(0, 0)
        for item in self._items:
            s = s.expandedTo(item.minimumSize())
        return s

    def _do_layout(self, rect, apply):
        x, y = rect.x(), rect.y()
        row_h = 0
        for item in self._items:
            sz = item.sizeHint()
            if x + sz.width() > rect.right() and row_h > 0:
                x = rect.x()
                y += row_h + self._spacing
                row_h = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), sz))
            x += sz.width() + self._spacing
            row_h = max(row_h, sz.height())
        return y + row_h - rect.y()


class NickTile(QLabel):
    def __init__(self, nick, parent=None):
        super().__init__(nick, parent)
        self.nick = nick
        self.setFixedSize(72, 22)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.OpenHandCursor)
        self._update_style()
        self._drag_start = None

    def _update_style(self):
        #todo закинуть в стили
        self.setStyleSheet("""
            QLabel {
                background: #1c1c28;
                border: 1px solid #444;
                border-radius: 2px;
                color: #aaa;
                font: 7pt "Segoe UI";
                padding: 0 2px;
            }
            QLabel:hover { background: #252535; color: #00ffcc; border-color: #00ffcc; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._drag_start is None:
            return
        if (event.pos() - self._drag_start).manhattanLength() < 8:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.nick)
        mime.setData("x-source", b"pool")
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)


class GridCell(QFrame):
    dropped = pyqtSignal(str, str, str)

    def __init__(self, row, col, cell_w, cell_h, mon_idx, dialog=None):
        super().__init__()
        self.grid_row = row
        self.grid_col = col
        self.mon_idx = mon_idx
        self.nick = None
        self._dlg = dialog
        self.setFixedSize(cell_w, cell_h)
        self.setAcceptDrops(True)
        self._hover = False
        self._drag_start = None
        self._btn = QPushButton("<", self)
        self._btn.setFixedSize(14, 14)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setStyleSheet(
            "QPushButton { background: #0d1418; border: 1px solid #00ccaa; color: #00ffcc;"
            " font: bold 7pt 'Segoe UI'; padding: 0; border-radius: 2px; }"
            "QPushButton:hover { background: #142428; }"
        )
        self._btn.move(cell_w - 16, 2)
        self._btn.hide()
        self._btn.clicked.connect(self._toggle)
        self._update_style()

    def _update_style(self):
        #todo закинуть в стили
        if self.nick:
            self.setStyleSheet("QFrame { background: #1a2a2a; border: 1px solid #00ccaa; }")
        else:
            self.setStyleSheet("QFrame { background: #161620; border: 1px solid #2a2a2a; }")

    def assign(self, nick):
        self.nick = nick
        self.setToolTip(nick or "")
        self._update_style()
        self._refresh_btn()
        self.update()

    def unassign(self):
        n = self.nick
        self.nick = None
        self.setToolTip("")
        self._update_style()
        self._btn.hide()
        self.update()
        return n

    def _refresh_btn(self):
        dlg = self._dialog()
        if not self.nick or not dlg:
            self._btn.hide()
            return
        info = dlg.windows.get(self.nick)
        if not info:
            self._btn.hide()
            return
        state = dlg.panels.state(info["ID"])
        if state is None:
            self._btn.hide()
            return
        self._btn.setText("<" if state else ">")
        self._btn.setToolTip("Свернуть" if state else "Развернуть")
        self._btn.show()

    def _toggle(self):
        dlg = self._dialog()
        if not self.nick or not dlg:
            return
        info = dlg.windows.get(self.nick)
        if not info:
            return
        hwnd = info["ID"]
        state = dlg.panels.state(hwnd)
        if state is True:
            dlg.panels.hide(hwnd)
        elif state is False:
            dlg.panels.show(hwnd)
        self._refresh_btn()

    def cell_key(self):
        return f"{self.mon_idx}:{self.grid_col},{self.grid_row}"

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hover and not self.nick:
            p.fillRect(self.rect().adjusted(1, 1, -1, -1), QColor(0, 255, 204, 25))
        if self.nick:
            p.setPen(QColor("#00ffcc"))
            f = QFont("Segoe UI", 7, QFont.Bold)
            p.setFont(f)
            fm = p.fontMetrics()
            elided = fm.elidedText(self.nick, Qt.ElideRight, self.rect().width() - 6)
            p.drawText(self.rect(), Qt.AlignCenter, elided)
        else:
            p.setPen(QColor("#333"))
            p.setFont(QFont("Segoe UI", 6))
            p.drawText(self.rect(), Qt.AlignCenter, f"{self.grid_col + 1},{self.grid_row + 1}")
        p.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self._hover = True
            self.update()

    def dragLeaveEvent(self, event):
        self._hover = False
        self.update()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self._hover = False
        nick = event.mimeData().text()
        source = bytes(event.mimeData().data("x-source")).decode()
        src_key = bytes(event.mimeData().data("x-cell-key")).decode() if source == "grid" else ""
        self.dropped.emit(nick, source, src_key)
        event.acceptProposedAction()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.nick:
            self._drag_start = event.pos()
        elif event.button() == Qt.RightButton and self.nick:
            dlg = self._dialog()
            if dlg:
                dlg._cell_to_pool(self)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or not self.nick or self._drag_start is None:
            return
        if (event.pos() - self._drag_start).manhattanLength() < 8:
            return
        saved_nick = self.nick
        self.unassign()
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(saved_nick)
        mime.setData("x-source", b"grid")
        mime.setData("x-cell-key", self.cell_key().encode())
        drag.setMimeData(mime)
        result = drag.exec_(Qt.MoveAction)
        if result == Qt.IgnoreAction:
            self.assign(saved_nick)
        dlg = self._dialog()
        if dlg:
            dlg._update_counter()

    def _dialog(self):
        if self._dlg:
            return self._dlg
        w = self.parent()
        while w:
            if isinstance(w, TilingDialog):
                return w
            w = w.parent()
        return None


class TilingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("L2Monad | Расстановка окон")
        self.setWindowIcon(QIcon(FAVICON))
        self.setMinimumSize(480, 480)

        self.monitors = []
        self.windows = {}
        self.current_monitor_idx = 0
        self.cells = {}
        self.pool_tiles = {}
        self.assigned_nicks = set()
        self.panels = Panels()

        self._cache = load_cache()
        self.keep_panels = bool(self._cache.get("tiling", {}).get("keep_panels", False))

        self._detect()
        self._auto_detect()
        self._build_ui()
        self._update_counter()

    @property
    def pitch_x(self):
        return CELL_W + (SIDEBAR_W if self.keep_panels else 0)

    def _save_cfg(self):
        self._cache["tiling"] = {"keep_panels": self.keep_panels}
        save_cache(self._cache)

    def _sync_mode(self):
        self.b_narrow.setChecked(not self.keep_panels)
        self.b_wide.setChecked(self.keep_panels)

    def _set_mode(self, keep):
        if keep == self.keep_panels:
            self._sync_mode()
            return
        self.keep_panels = keep
        self._save_cfg()
        self._sync_mode()
        self._rebuild()
        self._auto_fill()

    def _detect(self):
        self.monitors.clear()
        raw = get_monitors()
        for i, m in enumerate(raw):
            cols = m.width // self.pitch_x
            rows = (m.height - TOP_OFFSET) // CELL_H
            self.monitors.append({
                "idx": i, "x": m.x, "y": m.y,
                "w": m.width, "h": m.height,
                "cols": cols, "rows": rows,
            })
        self.windows = findAllWindows()

    def _auto_detect(self):
        taken = set()
        for nick, info in self.windows.items():
            if info.get("Width") != CELL_W or info.get("Height") != 225:
                continue
            pos = info.get("Position")
            if not pos:
                continue
            wx, wy = pos[0], pos[1]
            for mon in self.monitors:
                if mon["cols"] == 0 or mon["rows"] == 0:
                    continue
                for r in range(mon["rows"]):
                    for c in range(mon["cols"]):
                        ex = mon["x"] + c * self.pitch_x
                        ey = mon["y"] + r * CELL_H + TOP_OFFSET
                        if abs(wx - ex) <= 2 and abs(wy - ey) <= 2:
                            key = (mon["idx"], c, r)
                            if key not in taken:
                                taken.add(key)
                                self.assigned_nicks.add(nick)
                            break
                    else:
                        continue
                    break

    def _build_ui(self):
        # в стили
        self.setStyleSheet("""
            QDialog { background: #111217; }
            QPushButton {
                background: #1c1c28;
                border: 1px solid #333;
                border-radius: 3px;
                color: #ccc;
                font-size: 9pt;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #252535; border-color: #555; }
            QPushButton:checked { background: #1a2a2a; border: 1px solid #00ffcc; color: #00ffcc; }
            QLabel { color: #999; font-size: 9pt; }
        """)

        ml = QVBoxLayout(self)
        ml.setSpacing(6)
        ml.setContentsMargins(8, 8, 8, 8)

        top = QHBoxLayout()
        top.setSpacing(4)
        self._mon_btns = []
        for mon in self.monitors:
            b = QPushButton(f"Монитор {mon['idx']}  {mon['w']}x{mon['h']}  [{mon['cols']}x{mon['rows']}]")
            b.setCheckable(True)
            b.setFixedHeight(28)
            b.setCursor(Qt.PointingHandCursor)
            idx = mon["idx"]
            b.clicked.connect(lambda _, i=idx: self._switch_monitor(i))
            top.addWidget(b)
            self._mon_btns.append(b)
        ml.addLayout(top)

        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("""
            QScrollArea { border: none; background: #0d0d12; }
            QScrollBar:vertical { width: 6px; background: #111; }
            QScrollBar::handle:vertical { background: #333; border-radius: 3px; }
            QScrollBar:horizontal { height: 6px; background: #111; }
            QScrollBar::handle:horizontal { background: #333; border-radius: 3px; }
        """)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_scroll.setWidget(self.grid_container)
        ml.addWidget(self.grid_scroll, stretch=1)

        self._build_all()
        self._place_auto()
        if self.monitors:
            self._switch_monitor(0)

        pool_hdr = QHBoxLayout()
        pool_hdr.setSpacing(6)
        pool_hdr.setContentsMargins(0, 6, 0, 0)

        lab_pool = QLabel("Свободные окна")
        lab_pool.setStyleSheet("color: #888; font-weight: 600;")
        pool_hdr.addWidget(lab_pool)

        pool_hdr.addStretch(1)

        self.counter = QLabel()
        self.counter.setStyleSheet("color: #666;")
        pool_hdr.addWidget(self.counter)

        ml.addLayout(pool_hdr)

        self.pool_scroll = QScrollArea()
        self.pool_scroll.setFixedHeight(80)
        self.pool_scroll.setWidgetResizable(True)
        self.pool_scroll.setStyleSheet("""
            QScrollArea { border: 1px solid #1a1a1a; background: #0d0d12; }
            QScrollBar:vertical { width: 5px; background: #111; }
            QScrollBar::handle:vertical { background: #333; border-radius: 2px; }
        """)
        self.pool_widget = QWidget()
        self.pool_widget.setAcceptDrops(True)
        pool_sp = self.pool_widget.sizePolicy()
        pool_sp.setHeightForWidth(True)
        self.pool_widget.setSizePolicy(pool_sp)
        self.pool_widget.dragEnterEvent = self._pool_drag_enter
        self.pool_widget.dropEvent = self._pool_drop
        self.pool_widget.dragMoveEvent = self._pool_drag_move
        self.pool_layout = FlowLayout(self.pool_widget, spacing=3)
        self.pool_scroll.setWidget(self.pool_widget)
        ml.addWidget(self.pool_scroll)

        LAB_STYLE = "color: #777; min-width: 80px;"
        BTN_W = 130

        g1 = QHBoxLayout()
        g1.setSpacing(6)
        g1.setContentsMargins(0, 6, 0, 0)
        lab_a = QLabel("Действия:")
        lab_a.setStyleSheet(LAB_STYLE)
        g1.addWidget(lab_a)

        b_fill = QPushButton("Расставить")
        b_fill.setFixedHeight(26)
        b_fill.setFixedWidth(BTN_W)
        b_fill.setCursor(Qt.PointingHandCursor)
        b_fill.setToolTip("Заполнить сетку окнами из пула")
        b_fill.clicked.connect(self._auto_fill)
        g1.addWidget(b_fill)

        b_refresh = QPushButton("Обновить")
        b_refresh.setFixedHeight(26)
        b_refresh.setFixedWidth(BTN_W)
        b_refresh.setCursor(Qt.PointingHandCursor)
        b_refresh.setToolTip("Обновить список окон")
        b_refresh.clicked.connect(self._refresh)
        g1.addWidget(b_refresh)

        g1.addStretch(1)
        ml.addLayout(g1)

        g2 = QHBoxLayout()
        g2.setSpacing(6)
        lab_p = QLabel("Панельки:")
        lab_p.setStyleSheet(LAB_STYLE)
        g2.addWidget(lab_p)

        b_hide = QPushButton("Свернуть")
        b_hide.setFixedHeight(26)
        b_hide.setFixedWidth(BTN_W)
        b_hide.setCursor(Qt.PointingHandCursor)
        b_hide.setToolTip("Свернуть панельки у всех расставленных окон")
        b_hide.clicked.connect(self._hide_all)
        g2.addWidget(b_hide)

        b_show = QPushButton("Развернуть")
        b_show.setFixedHeight(26)
        b_show.setFixedWidth(BTN_W)
        b_show.setCursor(Qt.PointingHandCursor)
        b_show.setToolTip("Развернуть панельки у всех расставленных окон")
        b_show.clicked.connect(self._show_all)
        g2.addWidget(b_show)

        g2.addStretch(1)
        ml.addLayout(g2)

        g3 = QHBoxLayout()
        g3.setSpacing(6)
        lab_m = QLabel("Режим сетки:")
        lab_m.setStyleSheet(LAB_STYLE)
        g3.addWidget(lab_m)

        self.b_narrow = QPushButton("Плотный")
        self.b_narrow.setCheckable(True)
        self.b_narrow.setFixedHeight(26)
        self.b_narrow.setFixedWidth(BTN_W)
        self.b_narrow.setCursor(Qt.PointingHandCursor)
        self.b_narrow.setToolTip("Панельки скрываются автоматически, колонка 400 px")
        self.b_narrow.clicked.connect(lambda: self._set_mode(False))
        g3.addWidget(self.b_narrow)

        self.b_wide = QPushButton("С панельками")
        self.b_wide.setCheckable(True)
        self.b_wide.setFixedHeight(26)
        self.b_wide.setFixedWidth(BTN_W)
        self.b_wide.setCursor(Qt.PointingHandCursor)
        self.b_wide.setToolTip("Панельки остаются видимыми, колонка 456 px")
        self.b_wide.clicked.connect(lambda: self._set_mode(True))
        g3.addWidget(self.b_wide)

        self._sync_mode()

        g3.addStretch(1)
        ml.addLayout(g3)

        for nick in sorted(self.windows.keys()):
            if nick not in self.assigned_nicks:
                self._pool_add(nick)

        self._refresh_btns()
        self.resize(560, 560)

    def _build_all(self):
        for mon in self.monitors:
            idx = mon["idx"]
            cols, rows = mon["cols"], mon["rows"]
            if cols == 0 or rows == 0:
                continue
            scale = self._scale(mon)
            cw = max(int(self.pitch_x * scale), 36)
            ch = max(int(CELL_H * scale), 22)
            for r in range(rows):
                for c in range(cols):
                    cell = GridCell(r, c, cw, ch, idx, dialog=self)
                    cell.dropped.connect(self._on_drop)
                    self.cells[(idx, c, r)] = cell

    def _place_auto(self):
        for nick, info in self.windows.items():
            if nick not in self.assigned_nicks:
                continue
            pos = info.get("Position")
            if not pos:
                continue
            wx, wy = pos[0], pos[1]
            for mon in self.monitors:
                for r in range(mon["rows"]):
                    for c in range(mon["cols"]):
                        ex = mon["x"] + c * self.pitch_x
                        ey = mon["y"] + r * CELL_H + TOP_OFFSET
                        if abs(wx - ex) <= 2 and abs(wy - ey) <= 2:
                            cell = self.cells.get((mon["idx"], c, r))
                            if cell and not cell.nick:
                                cell.assign(nick)
                            break
                    else:
                        continue
                    break

    def _scale(self, mon):
        tw = mon["cols"] * self.pitch_x
        th = mon["rows"] * CELL_H
        if tw == 0 or th == 0:
            return 0.15
        return min(540 / tw, 260 / th, 0.25)

    def _switch_monitor(self, idx):
        self.current_monitor_idx = idx
        for i, b in enumerate(self._mon_btns):
            b.setChecked(i == idx)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        mon = self.monitors[idx]
        for r in range(mon["rows"]):
            for c in range(mon["cols"]):
                cell = self.cells.get((idx, c, r))
                if cell:
                    self.grid_layout.addWidget(cell, r, c)

    def _on_drop(self, nick, source, src_key):
        target = self.sender()
        if not isinstance(target, GridCell):
            return

        if source == "grid" and src_key == target.cell_key():
            target.assign(nick)
            self._update_counter()
            return

        if target.nick and source == "grid":
            old = target.nick
            src = self._cell_by_key(src_key)
            if src:
                src.assign(old)
                self._live_move(src)
        elif target.nick and source == "pool":
            old = target.nick
            free = self._nearest_free(target)
            if free:
                free.assign(old)
                self._live_move(free)
            else:
                self._pool_add(old)

        target.assign(nick)

        if source == "pool":
            self._pool_remove(nick)

        self._live_move(target)
        self._update_counter()

    def _refresh(self):
        self.windows = findAllWindows()
        new_nicks = set(self.windows.keys())

        for nick in list(self.pool_tiles.keys()):
            if nick not in new_nicks:
                self._pool_remove(nick)

        for cell in self.cells.values():
            if not cell.nick:
                continue
            if cell.nick not in new_nicks:
                cell.unassign()
                continue
            info = self.windows.get(cell.nick)
            if not info:
                cell.unassign()
                continue
            if info.get("Width") != CELL_W or info.get("Height") != 225:
                self._pool_add(cell.unassign())
                continue
            pos = info.get("Position")
            if pos:
                mon = self.monitors[cell.mon_idx]
                ex = mon["x"] + cell.grid_col * self.pitch_x
                ey = mon["y"] + cell.grid_row * CELL_H + TOP_OFFSET
                if abs(pos[0] - ex) > 2 or abs(pos[1] - ey) > 2:
                    self._pool_add(cell.unassign())

        grid_nicks = {cell.nick for cell in self.cells.values() if cell.nick}

        for nick in sorted(new_nicks):
            if nick in grid_nicks or nick in self.pool_tiles:
                continue
            if self._try_place(nick):
                pass
            else:
                self._pool_add(nick)

        self._update_counter()

    def _try_place(self, nick):
        info = self.windows.get(nick)
        if not info:
            return False
        if info.get("Width") != CELL_W or info.get("Height") != 225:
            return False
        pos = info.get("Position")
        if not pos:
            return False
        wx, wy = pos[0], pos[1]
        for mon in self.monitors:
            for r in range(mon["rows"]):
                for c in range(mon["cols"]):
                    ex = mon["x"] + c * self.pitch_x
                    ey = mon["y"] + r * CELL_H + TOP_OFFSET
                    if abs(wx - ex) <= 2 and abs(wy - ey) <= 2:
                        cell = self.cells.get((mon["idx"], c, r))
                        if cell and not cell.nick:
                            cell.assign(nick)
                            return True
        return False

    def _cell_to_pool(self, cell):
        if cell.nick:
            nick = cell.unassign()
            self._pool_add(nick)
            self._update_counter()

    def _nearest_free(self, origin):
        best = None
        best_dist = float("inf")
        for key, cell in self.cells.items():
            if cell.nick or cell is origin:
                continue
            if cell.mon_idx != origin.mon_idx:
                continue
            dr = cell.grid_row - origin.grid_row
            dc = cell.grid_col - origin.grid_col
            dist = dr * dr + dc * dc
            if dist < best_dist:
                best_dist = dist
                best = cell
        if not best:
            for key, cell in self.cells.items():
                if cell.nick or cell is origin:
                    continue
                return cell
        return best

    def _cell_by_key(self, key):
        try:
            mon_part, pos_part = key.split(":")
            c, r = pos_part.split(",")
            return self.cells.get((int(mon_part), int(c), int(r)))
        except (ValueError, IndexError):
            return None

    def _live_move(self, cell):
        if not cell.nick:
            return
        info = self.windows.get(cell.nick)
        if not info:
            return
        mon = self.monitors[cell.mon_idx]
        x = mon["x"] + cell.grid_col * self.pitch_x
        y = mon["y"] + cell.grid_row * CELL_H + TOP_OFFSET
        _move_window(info["ID"], x, y)
        if not self.keep_panels:
            self.panels.hide(info["ID"])
        cell._refresh_btn()

    def _placed(self):
        for cell in self.cells.values():
            if not cell.nick:
                continue
            info = self.windows.get(cell.nick)
            if info:
                yield info["ID"]

    def _hide_all(self):
        for hwnd in self._placed():
            self.panels.hide(hwnd)
        self._refresh_btns()

    def _show_all(self):
        for hwnd in self._placed():
            self.panels.show(hwnd)
        self._refresh_btns()

    def _refresh_btns(self):
        for cell in self.cells.values():
            cell._refresh_btn()

    def _rebuild(self):
        for nick in list(self.pool_tiles.keys()):
            self._pool_remove(nick)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        for cell in list(self.cells.values()):
            cell.setParent(None)
            cell.deleteLater()
        self.cells.clear()
        self.assigned_nicks.clear()
        self._detect()
        self._auto_detect()
        self._build_all()
        self._place_auto()
        for nick in sorted(self.windows.keys()):
            if nick not in self.assigned_nicks:
                self._pool_add(nick)
        if self.monitors:
            idx = self.current_monitor_idx if self.current_monitor_idx < len(self.monitors) else 0
            self._switch_monitor(idx)
        self._refresh_btns()
        self._update_counter()

    def _pool_add(self, nick):
        if nick in self.pool_tiles:
            return
        tile = NickTile(nick, self.pool_widget)
        self.pool_layout.addWidget(tile)
        self.pool_tiles[nick] = tile

    def _pool_remove(self, nick):
        tile = self.pool_tiles.pop(nick, None)
        if tile:
            self.pool_layout.removeWidget(tile)
            tile.setParent(None)
            tile.deleteLater()

    def _pool_drag_enter(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def _pool_drag_move(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def _pool_drop(self, event):
        nick = event.mimeData().text()
        source = bytes(event.mimeData().data("x-source")).decode()
        if source == "grid":
            src = self._cell_by_key(bytes(event.mimeData().data("x-cell-key")).decode())
            if src:
                src.unassign()
        self._pool_add(nick)
        self._update_counter()
        event.acceptProposedAction()

    def _update_counter(self):
        placed = sum(1 for c in self.cells.values() if c.nick)
        total = len(self.windows)
        pool = total - placed
        self.counter.setText(f"В пуле: {pool}  |  На сетке: {placed}/{total}")

    def _auto_fill(self):
        all_nicks = list(self.pool_tiles.keys()) + [c.nick for c in self.cells.values() if c.nick]
        for cell in self.cells.values():
            if cell.nick:
                cell.unassign()
        for nick in list(self.pool_tiles.keys()):
            self._pool_remove(nick)

        pending = []
        for nick in all_nicks:
            info = self.windows.get(nick)
            if info and info.get("Position"):
                pending.append((nick, info["Position"][0], info["Position"][1]))
            else:
                pending.append((nick, 0, 0))
        pending.sort(key=lambda e: (e[2], e[1]))

        free = [c for c in self.cells.values()]

        while pending and free:
            best_score = None
            best_nick_idx = 0
            best_cell_idx = 0
            for ni, (_, wx, wy) in enumerate(pending):
                for ci, cell in enumerate(free):
                    mon = self.monitors[cell.mon_idx]
                    cx = mon["x"] + cell.grid_col * self.pitch_x
                    cy = mon["y"] + cell.grid_row * CELL_H + TOP_OFFSET
                    d = (cx - wx) ** 2 + (cy - wy) ** 2
                    if best_score is None or d < best_score:
                        best_score = d
                        best_nick_idx = ni
                        best_cell_idx = ci
            nick = pending.pop(best_nick_idx)[0]
            cell = free.pop(best_cell_idx)
            cell.assign(nick)
            self._live_move(cell)

        for nick, _, _ in pending:
            self._pool_add(nick)

        self._apply_mode()
        self._refresh_btns()
        self._update_counter()

    def _apply_mode(self):
        for hwnd in self._placed():
            if self.keep_panels:
                self.panels.show(hwnd)
            else:
                self.panels.hide(hwnd)

