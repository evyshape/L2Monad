from PyQt5.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QCheckBox, QLineEdit, QSpinBox, QDialogButtonBox, QScrollArea, QWidget,
    QTabWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QObject, QEvent
from bot.windows.settings_loader import save_settings
from bot.clogger import log
from gui.styles import STYLE, SCROLL
from PyQt5.QtGui import QIcon
import os

FAVICON = os.path.join(os.path.dirname(__file__), 'images', 'favicon.ico')

class Blocker(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and isinstance(obj, (QComboBox, QSpinBox)):
            event.ignore()
            return True
        return super().eventFilter(obj, event)

class ComboBox(QComboBox):
    pass

class SpinBox(QSpinBox):
    pass

class Editor(QDialog):
    def __init__(self, nick, settings, p=None, apply_to=None):
        super().__init__(p)
        self.blocker = Blocker(self)
        self.nick = nick
        self.settings = settings
        self.apply_to = apply_to or [nick] # оч жесткий костыль #todo починить и добавить mode=some
        if len(self.apply_to) == 1:
            self.setWindowTitle(f"⚙️ Настройки {self.apply_to[0]}")
        else:
            self.setWindowTitle(f"⚙️ Настройки множества ({len(self.apply_to)})")
        self.resize(520, 620)
        self.setMinimumWidth(50)
        self.setWindowIcon(QIcon(FAVICON))
        self.widgets = {}

        ml = QVBoxLayout()
        ml.setAlignment(Qt.AlignTop)
        ml.setContentsMargins(10, 10, 10, 10)
        ml.setSpacing(8)

        rb = self._spawn("🌍 Регион")
        rl = QHBoxLayout()
        self.region_ru = QCheckBox("RU")
        self.region_jp = QCheckBox("JP")
        self.region_group = QButtonGroup(self)
        self.region_group.setExclusive(True)
        self.region_group.addButton(self.region_ru)
        self.region_group.addButton(self.region_jp)
        if settings.REGION == "RU":
            self.region_ru.setChecked(True)
        else:
            self.region_jp.setChecked(True)
        self.region_ru.stateChanged.connect(self._region_changed)
        self.region_jp.stateChanged.connect(self._region_changed)
        rl.addWidget(self.region_ru)
        rl.addWidget(self.region_jp)
        rb.setLayout(rl)
        ml.addWidget(rb)

        self.mirka = self._spawn("🕊 Мирный режим")
        mirkaa = QHBoxLayout()
        self.mirka_mode = QCheckBox("Включить")
        self.mirka_mode.setChecked(settings.PEACE_MODE)
       #self.mirka_mode.stateChanged.connect(self._mirka_change)
        mirkaa.addWidget(self.mirka_mode)
        self.mirka.setLayout(mirkaa)
        ml.addWidget(self.mirka)

        pb = self._spawn("⚔️ PVP")
        pl = QVBoxLayout()
        pl_row = QHBoxLayout()
        self.pvp_evade = QCheckBox("Додж")
        self.pvp_answer = QCheckBox("Ответ")
        self.pvp_evade.setChecked(settings.PVP_EVADE)
        self.pvp_answer.setChecked(settings.PVP_ANSWER)
        self.pvp_evade.stateChanged.connect(self._pvp_changed)
        self.pvp_answer.stateChanged.connect(self._pvp_changed)
        pl_row.addWidget(self.pvp_evade)
        pl_row.addWidget(self.pvp_answer)
        pl.addLayout(pl_row)
        self.autohunt_before_tp = QCheckBox("Автобой ДО телепорта")
        self.autohunt_before_tp.setChecked(settings.AUTOHUNT_BEFORE_TP)
        pl.addWidget(self.autohunt_before_tp)
        pb.setLayout(pl)
        ml.addWidget(pb)

        self.low_hp_box = self._spawn("💔 Уход при малом HP")
        low_hp_layout = QHBoxLayout()
        self.low_hp_cb = QCheckBox("Включить")
        self.low_hp_cb.setChecked(settings.LOW_HP_DODGE)
        self.low_hp_cb.stateChanged.connect(self._health)  # HEALTH_BACK обновлялка
        low_hp_layout.addWidget(self.low_hp_cb)
        self.fast_dodge_cb = QCheckBox("Быстрый додж (не терпеть)")
        self.fast_dodge_cb.setChecked(settings.FAST_DODGE)
        low_hp_layout.addWidget(self.fast_dodge_cb)
        self.low_hp_box.setLayout(low_hp_layout)
        ml.addWidget(self.low_hp_box)

        self.hb = self._spawn("❤️ Пороги для улета (% хп)")
        self.hg = QGridLayout()
        self.hc = []
        for i, val in enumerate(range(10, 100, 10)):
            cb = QCheckBox(str(val))
            if val in settings.HEALTH_BACK:
                cb.setChecked(True)
            self.hc.append(cb)
            self.hg.addWidget(cb, i // 5, i % 5, Qt.AlignCenter)
        self.hb.setLayout(self.hg)
        ml.addWidget(self.hb)

        self._health() # если включено пвп в ответе то монитор хп над показывать

        sb = self._spawn("📍 Споты")
        sl = QHBoxLayout()
        self.spot_ot = SpinBox()
        self.spot_ot.setRange(1, 4)
        self.spot_ot.setValue(settings.SPOT_OT)
        self.spot_do = SpinBox()
        self.spot_do.setRange(1, 4)
        self.spot_do.setValue(settings.SPOT_DO)
        sl.addWidget(QLabel("От:"))
        sl.addWidget(self.spot_ot)
        sl.addWidget(QLabel("До:"))
        sl.addWidget(self.spot_do)
        sb.setLayout(sl)
        ml.addWidget(sb)

        self._add_pack(ml, "🧪 Переключалки", {
            "HP_BANK_CHECKER": settings.HP_BANK_CHECKER,
            "BUY_LOOT_TOWN": settings.BUY_LOOT_TOWN,
            "BUY_LOOT_RIP": settings.BUY_LOOT_RIP,
            "SOSKA_CHECKER": settings.SOSKA_CHECKER,
            "DEATH_CHECKER": settings.DEATH_CHECKER,
            "OVERWEIGHT_CHECKER": settings.OVERWEIGHT_CHECKER,
            "TELEGRAM_NOTIFIES": settings.TELEGRAM_NOTIFIES
        })

        self.owb = self._spawn("⚖️ Перевес")
        owl = QHBoxLayout()
        self.ow_combo = ComboBox()
        self.ow_combo.addItems(["0", "50", "80"])
        self.ow_combo.setCurrentText(str(settings.OVERWEIGHT_AFK if settings.OVERWEIGHT_CHECKER else "80"))
        owl.addWidget(QLabel("АФК при:"))
        owl.addWidget(self.ow_combo)
        self.owb.setLayout(owl)
        self.owb.setVisible(settings.OVERWEIGHT_CHECKER)
        ml.addWidget(self.owb)

        self.widgets["OVERWEIGHT_CHECKER"].stateChanged.connect(lambda state: self.owb.setVisible(state == 2))

        self._fields(ml, "📅 Расписания", {
            "SCHEDULE_BUYING": settings.SCHEDULE_BUYING,
            "SCHEDULE_MAIL": settings.SCHEDULE_MAIL,
            "SCHEDULE_REWARDS": settings.SCHEDULE_REWARDS,
            "SCHEDULE_SCHEDULE": settings.SCHEDULE_SCHEDULE,
            "SCHEDULE_AUCTION": settings.SCHEDULE_AUCTION,
            "SCHEDULE_PARTY_DUNGEON": settings.SCHEDULE_PARTY_DUNGEON,
        })

        alliance = self._spawn("💥 Кнопка альянса")
        al = QHBoxLayout()
        self.alliance_btn = SpinBox()
        self.alliance_btn.setValue(int(settings.ALLIANCE_BUTTON))
        self.alliance_btn.setRange(0, 2)
        al.addWidget(QLabel("Куда жмем? (2 центр)"))
        al.addWidget(self.alliance_btn)
        alliance.setLayout(al)
        ml.addWidget(alliance)
        self.alliance_box = alliance
        self.alliance_box.setVisible(settings.REGION == "RU")

        pd_box = self._spawn("🏰 Сложность пати данжа (1-4)")
        pd_layout = QHBoxLayout()
        self.party_dungeon_hard = SpinBox()
        self.party_dungeon_hard.setRange(1, 4)
        self.party_dungeon_hard.setValue(settings.PARTY_DUNGEON_HARD)
        pd_layout.addWidget(QLabel("Сложность:"))
        pd_layout.addWidget(self.party_dungeon_hard)
        pd_box.setLayout(pd_layout)
        ml.addWidget(pd_box)

        db = self._spawn("💰 Страницы донат шопа")
        dl = QHBoxLayout()
        self.dc = []
        pages = settings.DONATE_SHOP_PAGES.split("|")
        for i in range(1, 5):
            cb = QCheckBox(str(i))
            if str(i) in pages:
                cb.setChecked(True)
            self.dc.append(cb)
            dl.addWidget(cb)
        db.setLayout(dl)
        ml.addWidget(db)

        rl2 = QVBoxLayout()
        rl2.setAlignment(Qt.AlignTop)
        rl2.setContentsMargins(10, 10, 10, 10)
        rl2.setSpacing(8)

        self._add_pack(rl2, "🎁 Что собирать", {
            "NEED_CLAIM_DAILY": settings.NEED_CLAIM_DAILY,
            "NEED_CLAIM_MAIL": settings.NEED_CLAIM_MAIL,
            "NEED_CLAIM_ACHIV": settings.NEED_CLAIM_ACHIV,
            "NEED_CLAIM_CLAN": settings.NEED_CLAIM_CLAN,
            "NEED_CLAIM_ALI": settings.NEED_CLAIM_ALI,
            "NEED_CLAIM_BATTLE_PASS": settings.NEED_CLAIM_BATTLE_PASS,
            "NEED_CLAIM_DONATE_SHOP": settings.NEED_CLAIM_DONATE_SHOP,
        })

        self._add_pack(rl2, "🛒 Магазин по расписанию", {
            "NEED_SHOP_AFTER_RIP": settings.NEED_SHOP_AFTER_RIP,
            "NEED_SHOP_AFTER_PVP_EVADE": settings.NEED_SHOP_AFTER_PVP_EVADE,
            "NEED_BACK_TO_SPOT_PARTY_DUNGEON": settings.NEED_BACK_TO_SPOT_PARTY_DUNGEON,
            "USE_STASH": settings.USE_STASH,
            "USE_SHOP": settings.USE_SHOP,
            "USE_SELLER": settings.USE_SELLER,
        })

        tl = QVBoxLayout()
        tl.setAlignment(Qt.AlignTop)
        tl.setContentsMargins(10, 10, 10, 10)
        tl.setSpacing(8)

        tb1 = self._spawn("⏱ Таймаут ответа на пвп (сек)")
        tb1_l = QHBoxLayout()
        self.delay_pvp_answer = SpinBox()
        self.delay_pvp_answer.setRange(1, 300)
        self.delay_pvp_answer.setValue(int(settings.DELAY_PVP_ANSWER))
        tb1_l.addWidget(QLabel("Секунд:"))
        tb1_l.addWidget(self.delay_pvp_answer)
        tb1.setLayout(tb1_l)
        tl.addWidget(tb1)

        tb2 = self._spawn("🔁 Итераций проверки хп после пвп")
        tb2_l = QHBoxLayout()
        self.pvp_answer_check = SpinBox()
        self.pvp_answer_check.setRange(1, 30)
        self.pvp_answer_check.setValue(int(settings.PVP_ANSWER_CHECK_HP_ITERATIONS))
        tb2_l.addWidget(QLabel("Кол-во:"))
        tb2_l.addWidget(self.pvp_answer_check)
        tb2.setLayout(tb2_l)
        tl.addWidget(tb2)

        tb3 = self._spawn("💀 Сон после смерти (сек)")
        tb3_l = QHBoxLayout()
        self.min_sleep_rip = SpinBox()
        self.min_sleep_rip.setRange(0, 3600)
        self.min_sleep_rip.setValue(int(settings.MIN_SLEEP_AFTER_RIP))
        self.max_sleep_rip = SpinBox()
        self.max_sleep_rip.setRange(0, 3600)
        self.max_sleep_rip.setValue(int(settings.MAX_SLEEP_AFTER_RIP))
        tb3_l.addWidget(QLabel("Мин:"))
        tb3_l.addWidget(self.min_sleep_rip)
        tb3_l.addWidget(QLabel("Макс:"))
        tb3_l.addWidget(self.max_sleep_rip)
        tb3.setLayout(tb3_l)
        tl.addWidget(tb3)

        tb4 = self._spawn("💔 Сон после лоу-хп доджа (сек)")
        tb4_l = QHBoxLayout()
        self.min_low_hp = SpinBox()
        self.min_low_hp.setRange(0, 3600)
        self.min_low_hp.setValue(int(settings.MIN_LOW_HP_DODGE_SLEEP))
        self.max_low_hp = SpinBox()
        self.max_low_hp.setRange(0, 3600)
        self.max_low_hp.setValue(int(settings.MAX_LOW_HP_DODGE_SLEEP))
        tb4_l.addWidget(QLabel("Мин:"))
        tb4_l.addWidget(self.min_low_hp)
        tb4_l.addWidget(QLabel("Макс:"))
        tb4_l.addWidget(self.max_low_hp)
        tb4.setLayout(tb4_l)
        tl.addWidget(tb4)

        tb5 = self._spawn("⚔️ Сон после пвп-доджа (сек)")
        tb5_l = QHBoxLayout()
        self.min_pvp_dodge = SpinBox()
        self.min_pvp_dodge.setRange(0, 3600)
        self.min_pvp_dodge.setValue(int(settings.MIN_PVP_DODGE_SLEEP))
        self.max_pvp_dodge = SpinBox()
        self.max_pvp_dodge.setRange(0, 3600)
        self.max_pvp_dodge.setValue(int(settings.MAX_PVP_DODGE_SLEEP))
        tb5_l.addWidget(QLabel("Мин:"))
        tb5_l.addWidget(self.min_pvp_dodge)
        tb5_l.addWidget(QLabel("Макс:"))
        tb5_l.addWidget(self.max_pvp_dodge)
        tb5.setLayout(tb5_l)
        tl.addWidget(tb5)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._confirm)
        btn_box.rejected.connect(self.reject)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #333;
                background: #151515;
                top: -1px;
            }
            QTabBar {
                background: #111217;
            }
            QTabBar::tab {
                background: #1c1c28;
                color: #bbb;
                padding: 6px 14px;
                border: 1px solid #333;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:hover {
                background: #252535;
                color: #ddd;
            }
            QTabBar::tab:selected {
                background: #151515;
                color: #00ffcc;
                border: 1px solid #00ffcc;
                border-bottom: none;
            }
        """)

        tab1 = QWidget()
        tab1.setLayout(ml)
        scroll1 = QScrollArea()
        scroll1.setWidgetResizable(True)
        scroll1.setWidget(tab1)
        scroll1.setStyleSheet(SCROLL + """
             QScrollArea {
                 border: none;
                 background-color: #151515;
             }
         """)

        tab2 = QWidget()
        tab2.setLayout(rl2)
        scroll2 = QScrollArea()
        scroll2.setWidgetResizable(True)
        scroll2.setWidget(tab2)
        scroll2.setStyleSheet(SCROLL + """
             QScrollArea {
                 border: none;
                 background-color: #151515;
             }
         """)

        tab3 = QWidget()
        tab3.setLayout(tl)
        scroll3 = QScrollArea()
        scroll3.setWidgetResizable(True)
        scroll3.setWidget(tab3)
        scroll3.setStyleSheet(SCROLL + """
             QScrollArea {
                 border: none;
                 background-color: #151515;
             }
         """)

        tabs.addTab(scroll1, "⚙️ Основное")
        tabs.addTab(scroll2, "🎁 Награды и шоп")
        tabs.addTab(scroll3, "⏱ Тайминги")

        main_layout = QVBoxLayout()
        main_layout.addWidget(tabs)
        main_layout.addWidget(btn_box)
        self.setLayout(main_layout)

        self.setStyleSheet(STYLE)

        self.ow_combo.installEventFilter(self.blocker)
        self.spot_ot.installEventFilter(self.blocker)
        self.spot_do.installEventFilter(self.blocker)
        self.alliance_btn.installEventFilter(self.blocker)
        self.party_dungeon_hard.installEventFilter(self.blocker)
        self.delay_pvp_answer.installEventFilter(self.blocker)
        self.pvp_answer_check.installEventFilter(self.blocker)
        self.min_sleep_rip.installEventFilter(self.blocker)
        self.max_sleep_rip.installEventFilter(self.blocker)
        self.min_low_hp.installEventFilter(self.blocker)
        self.max_low_hp.installEventFilter(self.blocker)
        self.min_pvp_dodge.installEventFilter(self.blocker)
        self.max_pvp_dodge.installEventFilter(self.blocker)

    def _spawn(self, title: str):
        box = QGroupBox(title)
        box.setAlignment(Qt.AlignCenter)
        return box

    def _region_changed(self, state=None):
        if self.region_ru.isChecked():
            self.alliance_box.setVisible(True)
        else:
            self.alliance_box.setVisible(False)
            self.alliance_btn.setValue(0)

    def _add_pack(self, layout, title, fields: dict):
        box = self._spawn(title)
        inner = QGridLayout()
        for i, (key, val) in enumerate(fields.items()):
            cb = QCheckBox("Вкл")
            cb.setChecked(val)
            inner.addWidget(QLabel(key + ":"), i, 0)
            inner.addWidget(cb, i, 1)
            self.widgets[key] = cb
        box.setLayout(inner)
        layout.addWidget(box)

    def _fields(self, layout, title, fields: dict):
        box = self._spawn(title)
        inner = QGridLayout()
        for i, (key, val) in enumerate(fields.items()):
            edit = QLineEdit(str(val))
            if key == "SCHEDULE_SCHEDULE":
                edit.setPlaceholderText("10:00-18:00")
            else:
                edit.setPlaceholderText("10:00|12:00|...")
            inner.addWidget(QLabel(key + ":"), i, 0)
            inner.addWidget(edit, i, 1)
            self.widgets[key] = edit
        box.setLayout(inner)
        layout.addWidget(box)

    def _uniq(self, src, other):
        if src.isChecked():
            other.setChecked(False)
        elif not src.isChecked() and not other.isChecked():
            src.setChecked(True)

        self._health()

    def _pvp_changed(self, state=None):
        if not self.pvp_evade.isChecked() and not self.pvp_answer.isChecked():
            self._health()
            return

        if self.sender() == self.pvp_evade and self.pvp_evade.isChecked():
            self.pvp_answer.setChecked(False)
        elif self.sender() == self.pvp_answer and self.pvp_answer.isChecked():
            self.pvp_evade.setChecked(False)

        self._health()

    def _health(self):
        show_health = self.pvp_answer.isChecked() or self.low_hp_cb.isChecked()

        if self.pvp_evade.isChecked() and not show_health:
            self.hb.setVisible(False)
            for cb in self.hc:
                cb.setChecked(False)
            for val in [20, 30, 40]:
                for cb in self.hc:
                    if int(cb.text()) == val:
                        cb.setChecked(True)
        else:
            self.hb.setVisible(show_health)

    def _confirm(self):
        try:
            if self.region_ru.isChecked():
                self.settings.REGION = "RU"
            elif self.region_jp.isChecked():
                self.settings.REGION = "JP"
            else:
                self.region_ru.setChecked(True)
                self.settings.REGION = "RU"

            self.settings.LOW_HP_DODGE = self.low_hp_cb.isChecked()
            self.settings.PEACE_MODE = self.mirka_mode.isChecked()
            self.settings.PVP_EVADE = self.pvp_evade.isChecked()
            self.settings.PVP_ANSWER = self.pvp_answer.isChecked()
            self.settings.HEALTH_BACK = [int(cb.text()) for cb in self.hc if cb.isChecked()]
            self.settings.AUTOHUNT_BEFORE_TP = self.autohunt_before_tp.isChecked()
            self.settings.FAST_DODGE = self.fast_dodge_cb.isChecked()

            for key in ["HP_BANK_CHECKER", "SOSKA_CHECKER", "DEATH_CHECKER", "OVERWEIGHT_CHECKER", "TELEGRAM_NOTIFIES", "BUY_LOOT_TOWN", "BUY_LOOT_RIP"]:
                self.settings.__dict__[key] = self.widgets[key].isChecked()

            self.settings.OVERWEIGHT_AFK = int(self.ow_combo.currentText()) if self.settings.OVERWEIGHT_CHECKER else 80
            for key in ["SCHEDULE_BUYING", "SCHEDULE_MAIL", "SCHEDULE_REWARDS", "SCHEDULE_SCHEDULE", "SCHEDULE_AUCTION"]:
                self.settings.__dict__[key] = self.widgets[key].text()

            self.settings.PARTY_DUNGEON_HARD = self.party_dungeon_hard.value()
            self.settings.SCHEDULE_PARTY_DUNGEON = self.widgets["SCHEDULE_PARTY_DUNGEON"].text()

            self.settings.DONATE_SHOP_PAGES = "|".join([cb.text() for cb in self.dc if cb.isChecked()])
            self.settings.SPOT_OT = self.spot_ot.value()
            self.settings.SPOT_DO = self.spot_do.value()

            if self.settings.REGION == "RU":
                self.settings.ALLIANCE_BUTTON = self.alliance_btn.value()
            else:
                self.settings.ALLIANCE_BUTTON = 0

            for key in ["NEED_CLAIM_DAILY", "NEED_CLAIM_MAIL", "NEED_CLAIM_ACHIV",
                        "NEED_CLAIM_CLAN", "NEED_CLAIM_ALI", "NEED_CLAIM_BATTLE_PASS",
                        "NEED_CLAIM_DONATE_SHOP", "NEED_SHOP_AFTER_RIP",
                        "NEED_SHOP_AFTER_PVP_EVADE", "NEED_BACK_TO_SPOT_PARTY_DUNGEON",
                        "USE_STASH", "USE_SHOP", "USE_SELLER"]:
                self.settings.__dict__[key] = self.widgets[key].isChecked()

            self.settings.DELAY_PVP_ANSWER = self.delay_pvp_answer.value()
            self.settings.PVP_ANSWER_CHECK_HP_ITERATIONS = self.pvp_answer_check.value()

            min_rip = self.min_sleep_rip.value()
            max_rip = self.max_sleep_rip.value()
            if min_rip > max_rip:
                min_rip, max_rip = max_rip, min_rip
            self.settings.MIN_SLEEP_AFTER_RIP = min_rip
            self.settings.MAX_SLEEP_AFTER_RIP = max_rip

            min_lh = self.min_low_hp.value()
            max_lh = self.max_low_hp.value()
            if min_lh > max_lh:
                min_lh, max_lh = max_lh, min_lh
            self.settings.MIN_LOW_HP_DODGE_SLEEP = min_lh
            self.settings.MAX_LOW_HP_DODGE_SLEEP = max_lh

            min_pd = self.min_pvp_dodge.value()
            max_pd = self.max_pvp_dodge.value()
            if min_pd > max_pd:
                min_pd, max_pd = max_pd, min_pd
            self.settings.MIN_PVP_DODGE_SLEEP = min_pd
            self.settings.MAX_PVP_DODGE_SLEEP = max_pd

            for nick in self.apply_to: # срет в логи сильно потом оптимизирую
                save_settings(nick, self.settings)
                log(f"Сохранил {nick}: {self.settings.__dict__}")

            self.accept()

        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ахтунг!", str(e))
