import requests
import os
import zipfile
import io
import shutil
import configparser
import sys
import subprocess
from bot.clogger import log

VERSION_FILE = os.path.join(os.path.dirname(__file__), "version.txt")
REPO_VERSION = "https://raw.githubusercontent.com/evyshape/L2Monad/main/bot/version.txt"
REPO_ZIP = "https://github.com/evyshape/L2Monad/archive/refs/heads/main.zip"

def get_my_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"

def parse_version(v: str):
    return tuple(map(int, v.split(".")))

def needs_update() -> bool:
    try:
        local = parse_version(get_my_version())
        remote = parse_version(requests.get(REPO_VERSION, timeout=2).text.strip())
        return remote > local
    except Exception:
        return False

def backup():
    version = get_my_version()
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    backups_dir = os.path.join(root_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    archive_path = os.path.join(backups_dir, f"update_backup_{version}.zip")

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            if any(skip in root for skip in ("backups", "logs")):
                continue
            for file in files:
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, root_dir)
                zipf.write(path, rel_path)

    log(f"Сделан бэкап текущей версии в {archive_path}")
    return archive_path

def install_req(req_path):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_path])
        log(f"Установил зависимости: {req_path}")
    except Exception as e:
        log(f"Ошибка при установке зависимостей: {e}")

def update_delays(local_path, new_path):
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            local_lines = f.readlines()
        with open(new_path, "r", encoding="utf-8") as f:
            new_lines = f.readlines()

        local_map = {}
        for line in local_lines:
            if "=" in line and line.split("=")[0].strip().isupper():
                key = line.split("=")[0].strip()
                local_map[key] = line

        merged = []
        seen = set()

        for line in new_lines:
            if "=" in line and line.split("=")[0].strip().isupper():
                key = line.split("=")[0].strip()
                if key in local_map:
                    merged.append(local_map[key].rstrip() + "\n")
                else:
                    merged.append(line)
                seen.add(key)
            else:
                merged.append(line)

        for key, line in local_map.items():
            if key not in seen:
                merged.append("\n" + line)

        with open(local_path, "w", encoding="utf-8") as f:
            f.writelines(merged)

        log(f"Обновил и смержил: {local_path}")

    except Exception as e:
        log(f"Шось злое: {e}")


def update_misc(local_path, new_path):
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            local_lines = f.readlines()
        with open(new_path, "r", encoding="utf-8") as f:
            new_lines = f.readlines()

        local_map = {}
        for line in local_lines:
            if "=" in line and line.split("=")[0].strip().isupper():
                key = line.split("=")[0].strip()
                local_map[key] = line

        merged = []
        seen = set()

        for line in new_lines:
            if "=" in line and line.split("=")[0].strip().isupper():
                key = line.split("=")[0].strip()
                if key in local_map:
                    merged.append(local_map[key].rstrip() + "\n")
                else:
                    merged.append(line)
                seen.add(key)
            else:
                merged.append(line)

        for key, line in local_map.items():
            if key not in seen:
                merged.append("\n" + line)

        with open(local_path, "w", encoding="utf-8") as f:
            f.writelines(merged)

        log(f"Обновил и смержил: {local_path}")

    except Exception as e:
        log(f"Шось злое: {e}")


def ini(local_path, new_path):
    config_local = configparser.ConfigParser()
    config_new = configparser.ConfigParser()
    config_local.read(local_path, encoding="utf-8")
    config_new.read(new_path, encoding="utf-8")

    for section in config_new.sections():
        if not config_local.has_section(section):
            config_local.add_section(section)
        for key, val in config_new.items(section):
            if not config_local.has_option(section, key):
                config_local.set(section, key, val)

    with open(local_path, "w", encoding="utf-8") as f:
        config_local.write(f)

def update():
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        backup()

        r = requests.get(REPO_ZIP, timeout=10)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))

        temp_dir = os.path.join(root_dir, "temp_update")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        z.extractall(temp_dir)
        main_repo = os.path.join(temp_dir, "L2Monad-main")

        for root, dirs, files in os.walk(main_repo):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), main_repo)
                dst_path = os.path.join(root_dir, rel_path)

                if "settings" in rel_path.split(os.sep):
                    if not os.path.exists(dst_path):
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(os.path.join(root, file), dst_path)
                    continue

                if dst_path.endswith(".ini") and os.path.exists(dst_path):
                    ini(dst_path, os.path.join(root, file))
                    continue

                if dst_path.endswith("bot{}delays.py".format(os.sep)) and os.path.exists(dst_path):
                    update_delays(dst_path, os.path.join(root, file))
                    continue

                if dst_path.endswith("bot{}misc.py".format(os.sep)) and os.path.exists(dst_path):
                    update_misc(dst_path, os.path.join(root, file))
                    continue

                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(os.path.join(root, file), dst_path)

        shutil.rmtree(temp_dir)

        req_path = os.path.join(root_dir, "requirements.txt")
        if os.path.exists(req_path):
            install_req(req_path)

        log("Накатил обнову, рестарчусь")

        try:
            ppath = sys.executable

            if not os.path.exists(ppath):
                ppath = shutil.which("python") or shutil.which(
                    "python3") or ppath

            log(f"Рестарт через: {ppath}")
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            bot = os.path.join(root, "main.py")

            clean = os.environ.copy()
            # ebat costyl
            for bad in ("PYTHONHOME", "PYTHONEXECUTABLE", "PYTHONPATH"):
                clean.pop(bad, None)

            subprocess.Popen([ppath, bot] + sys.argv[1:], env=clean)
            print("NE TROGAI NI4EGO")
            sys.exit(0)

        except Exception as e:
            log(f"Не смог рестартануть: {e}")
            sys.exit(1)

    except Exception as e:
        log(f"Обнова бахнула: {e}")
        sys.exit(1)