from PyQt5.QtWidgets import QMessageBox
from gui.styles import ERROR_STYLE

MOUSE_ERROR_TEXT = (
    "Драйвер Interception для мыши не найден\n\n"
    "Сделайте следующее:\n"
    "1. Откройте папку installer\n"
    "2. Запустите installer.ps1 от имени администратора\n"
    "3. Перезагрузите ПК"
)

KEYBOARD_WARNING_TEXT = (
    "Драйвер клавиатуры/сама клавиатура не обнаружена.\n"
    "Текущая версия бота работает без клавиатуры, "
    "но в дальнейшем она может понадобиться."
)


def show_message(critical: bool = True):
    msg = QMessageBox()
    msg.setStyleSheet(ERROR_STYLE)
    msg.setWindowTitle("Interception")
    if critical:
        msg.setIcon(QMessageBox.Critical)
        msg.setText(MOUSE_ERROR_TEXT)
    else:
        msg.setIcon(QMessageBox.Information)
        msg.setText(KEYBOARD_WARNING_TEXT)
    msg.exec_()
