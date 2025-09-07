import sys
import os
import getpass
from pathlib import Path
import asyncio

from PyQt5.QtWidgets import QApplication, QMessageBox
from qasync import QEventLoop

from gui.maingui import NedoGui
from gui.styles import ERROR_STYLE
from tgbot.bot import TgBot
from bot.utils import checkDriver

async def main():
    tg = TgBot()
    tg.start_polling()
    gui = NedoGui(kb, m)
    gui.show()

if __name__ == "__main__":
    user = getpass.getuser()
    p = Path(sys.prefix) / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins" / "platforms"

    if any(ord(c) > 127 for c in user):
        # костыль для челов с ру символами в юзере, ну че поделать
        # либо так, либо запускать из пути где нет кирилицы
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(p)

    kb, m = checkDriver()
    if kb is None or m is None:
        app = QApplication(sys.argv)
        app.setStyleSheet(ERROR_STYLE)
        QMessageBox.critical(
            None,
            "Interception",
            "Драйвер Interception не найден\n\n"
            "Сделайте следующее:\n"
            "1. Откройте папку installer\n"
            "2. Запустите installer.ps1 от имени администратора\n"
            "3. Перезагрузите ПК",
        )
        sys.exit(1)

    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()