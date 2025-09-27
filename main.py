import sys
import os
from pathlib import Path
import asyncio
import PyQt5
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
    base = Path(PyQt5.__file__).resolve().parent
    plugs = base / "Qt5" / "plugins" / "platforms"
    
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugs)

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

    with loop:
        loop.run_forever()
