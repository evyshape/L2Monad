import sys
import os
from PyQt5.QtWidgets import QApplication
from gui.maingui import NedoGui
import getpass
from pathlib import Path

def main():
    user = getpass.getuser()
    p = Path(sys.prefix) / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins" / "platforms"

    if any(ord(c) > 127 for c in user):
        # костыль для челов с ру символами в юзере, ну че поделать
        # либо так, либо запускать из пути где нет кирилицы
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(p)

    app = QApplication(sys.argv)
    gui = NedoGui()
    gui.show()
    sys.exit(app.exec_())

main()
