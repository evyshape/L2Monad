import sys
import os
import getpass
from pathlib import Path
import asyncio

from PyQt5.QtWidgets import QApplication
from qasync import QEventLoop

from gui.maingui import NedoGui
from tgbot.bot import TgBot
from gui.driver_error import show_message
from bot.utils import checkDriver

async def main():
    tg = TgBot()
    tg.start_polling()
    gui = NedoGui(kb, m)
    gui.show()

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    user = getpass.getuser()
    p = Path(sys.prefix) / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins" / "platforms"

    if any(ord(c) > 127 for c in user):
        # костыль для челов с ру символами в юзере, ну че поделать
        # либо так, либо запускать из пути где нет кирилицы
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(p)

    kb, m = checkDriver()
    app = QApplication(sys.argv)

    if m is None:
        show_message(critical=True)
        sys.exit(1)
    elif kb is None:
        show_message(critical=False)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()