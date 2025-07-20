import pygetwindow as gw
from clogger import log

def findAllWindows():
    all_windows = gw.getWindowsWithTitle("Lineage2M")
    window_info = {}
    for window in all_windows:
        nick = window.title.split("l ")[1] if "l " in window.title else "No"
        info = {
            "Nickname": nick, # ник
            "Title": window.title,  # название окна фулл
            "ID": window._hWnd,  # айди окна
            "Position": window.topleft,  # позиция (верхний левый угол)
            "Width": window.width,  # ширина окна
            "Height": window.height,  # высота окна
            "Size": f"{window.width}x{window.height}",  # размер окна (ширина x высота)
            "Active": window.isActive,  # активно ли (булево)
            "Stashing": 0,
            "State": "null",
            "Energo": "null",
            "InHome": "null",
        }
        if nick != "No":
            window_info[nick] = info
        else:
            log(f"Не будем обрабатывать окно без ника ({window.title})")
    log(len(window_info))
    return window_info