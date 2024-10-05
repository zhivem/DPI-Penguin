import os
import platform
import subprocess
import sys
import logging

def get_architecture():
    return "x86_64" if platform.architecture()[0] == "64bit" else "x86"

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

BLACKLIST_FILES = [
    os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt"),
    os.path.join(BASE_FOLDER, "black", "russia-youtube.txt")
]

GOODBYE_DPI_EXE = os.path.join(BASE_FOLDER, "bin", get_architecture(), "goodbyedpi.exe")

WIN_DIVERT_COMMAND = ["net", "stop", "WinDivert"]

GOODBYE_DPI_PROCESS_NAME = "goodbyedpi.exe"

current_version = '1.2'

def ensure_module_installed(module_name):
    try:
        __import__(module_name)
    except ImportError:
        logging.warning(f"Модуль {module_name} не найден, установка...")
        install_module(module_name)

def install_module(module_name):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка установки модуля {module_name}: {e}")

def get_latest_version():
    import requests
    url = 'https://api.github.com/repos/{owner}/{repo}/releases/latest'.format(owner='zhivem', repo='GoodByDPI-GUI-by-Zhivem')
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['tag_name']
        logging.warning(f"Не удалось получить последнюю версию. Код ответа: {response.status_code}")
        return None
    except requests.RequestException as e:
        logging.error(f"Ошибка запроса к GitHub API: {e}")
        return None

def is_newer_version(latest, current):
    from packaging.version import parse as parse_version
    return parse_version(latest) > parse_version(current)
