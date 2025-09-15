import pygetwindow as gw
from bot.clogger import log
import os
import importlib.util
from profiles.base import BaseProfile
from interception.inputs import _g_context

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
        }
        if nick != "No":
            window_info[nick] = info

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


def checkDriver() -> bool:
    if not _g_context.valid:
        log("Драйвер не найден или не удалось чекнуть!")
        return None, None

    kb = any(
        _g_context.devices[i].get_HWID() is not None
        for i in range(0, 10)
    )

    m = any(
        _g_context.devices[i].get_HWID() is not None
        for i in range(10, 20)
    )

    if not kb and not m:
        log("Не найдена ни клавиатура, ни мышь")
        return None, None
    elif not kb:
        log("Не найдена клавиатура, но мышь присутствует")
        return None, _g_context.mouse
    elif not m:
        log("Не найдена мышь, бот не сможет работать")
        return None, None

    log(f"Драйвер работает! | Клава={_g_context.keyboard} | Мышь={_g_context.mouse}")
    return _g_context.keyboard, _g_context.mouse

def getLogs():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    lpath = os.path.join(base_dir, "logs")
    all_logs = []

    if not os.path.exists(lpath) or not os.path.isdir(lpath):
        #log(f"Папка {lpath} не найдена", level="ERROR")
        return all_logs

    for fname in os.listdir(lpath):
        fpath = os.path.join(lpath, fname)
        if os.path.isfile(fpath):
            all_logs.append({
                "Name": fname,
                "Path": fpath
            })

    return all_logs