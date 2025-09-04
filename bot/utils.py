import pygetwindow as gw
from clogger import log
import os
import importlib.util
from profiles.base import BaseProfile

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
            log(f"Не будем обрабатывать окно без ника ({window.title})", level="ERROR")

    #log(len(window_info))
    return window_info

def getProfiles(profiles_path="profiles"):
    pr = {}

    for fold in os.listdir(profiles_path):
        fpath = os.path.join(profiles_path, fold)
        if not os.path.isdir(fpath):
            continue

        for f in os.listdir(fpath):
            if not f.endswith(".py") or f.lower() == "base.py":
                continue

            prof_path = os.path.join(fpath, f)
            prof_name = f"{fold}.{f[:-3]}"

            spec = importlib.util.spec_from_file_location(prof_name, prof_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for at in dir(module):
                attr = getattr(module, at)
                if isinstance(attr, type) and issubclass(attr, BaseProfile) and attr is not BaseProfile:
                    pr[at] = attr

    return pr