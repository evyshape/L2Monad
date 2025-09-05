import requests
import os
import zipfile
import io
import shutil
import configparser
import sys
from clogger import log
import subprocess

VERSION_FILE = os.path.join("bot", "version.txt")
REPO_VERSION = "https://raw.githubusercontent.com/evyshape/L2Monad/main/bot/version.txt"
REPO_ZIP = "https://github.com/evyshape/L2Monad/archive/refs/heads/main.zip"

def backup():
    version = get_my_version()
    backup_dir = os.path.join("backups", f"update_backup_{version}")
    os.makedirs(backup_dir, exist_ok=True)
    archive_path = shutil.make_archive(backup_dir, 'zip', ".")
    log(f"Сделан бэкап текущей версии в {archive_path}")
    return archive_path

def install_req(req_path="requirements.txt"):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
        log(f"Установил зависимости: {req_path}")
    except Exception as e:
        log(f"Ошибка в апдейтере: {e}")

def get_my_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"

def get_repo_version():
    try:
        r = requests.get(REPO_VERSION, timeout=1)
        r.raise_for_status()
        return r.text.strip()
    except Exception:
        return get_my_version()

def parse_version(v: str):
    return tuple(map(int, v.split(".")))

def needs_update() -> bool:
    try:
        local = parse_version(get_my_version())
        remote = parse_version(get_repo_version())
        return remote > local
    except Exception:
        return False

def ini(lp, np):
    # не трогает ваши настройки, никуда не отправляет, просто добавит новые столбики если они появились в обнове
    config_local = configparser.ConfigParser()
    config_new = configparser.ConfigParser()
    config_local.read(lp, encoding="utf-8")
    config_new.read(np, encoding="utf-8")

    for section in config_new.sections():
        if not config_local.has_section(section):
            config_local.add_section(section)
        for key, val in config_new.items(section):
            if not config_local.has_option(section, key):
                config_local.set(section, key, val)

    with open(lp, "w", encoding="utf-8") as f:
        config_local.write(f)

def update():
    try:
        backup()
        r = requests.get(REPO_ZIP, timeout=5)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        temp_dir = "temp"
        z.extractall(temp_dir)

        main_repo = os.path.join(temp_dir, "L2Monad-main")
        for root, dirs, files in os.walk(main_repo):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), main_repo)
                dst_path = os.path.join(".", rel_path)

                if "settings" in dst_path.split(os.sep):
                    if not os.path.exists(dst_path):
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(os.path.join(root, file), dst_path)
                    continue

                if dst_path.endswith(".ini") and os.path.exists(dst_path):
                    ini(dst_path, os.path.join(root, file))
                    continue

                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(os.path.join(root, file), dst_path)

        shutil.rmtree(temp_dir)

        rf = "requirements.txt"
        if os.path.exists(rf):
            install_req(rf)

        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        log(f"Обнова бахнула: {e}")
        exit()