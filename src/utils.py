import os
import platform
import subprocess
import sys
import logging
import requests

def get_architecture():
    return "x86_64" if platform.architecture()[0] == "64bit" else "x86"

BASE_FOLDER = os.path.abspath(os.path.dirname(__file__))

BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "icon")

BLACKLIST_FILES = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "russia-youtube.txt"),
    os.path.join(BLACKLIST_FOLDER, "discord-blacklist.txt")
]

GOODBYE_DPI_EXE = os.path.join(BASE_FOLDER, "bin", get_architecture(), "goodbyedpi.exe")

WIN_DIVERT_COMMAND = ["net", "stop", "WinDivert"]

GOODBYE_DPI_PROCESS_NAME = "goodbyedpi.exe"

current_version = "1.4"

SITES = [
    "youtube.com",
    "youtu.be",
    "yt.be",
    "googlevideo.com",
    "ytimg.com",
    "ggpht.com",
    "gvt1.com",
    "youtube-nocookie.com",
    "youtube-ui.l.google.com",
    "youtubeembeddedplayer.googleapis.com",
    "youtube.googleapis.com",
    "youtubei.googleapis.com",
    "yt-video-upload.l.google.com",
    "wide-youtube.l.google.com"
]

DISPLAY_NAMES = [
    "Основной сайт YouTube",
    "Короткие ссылки YouTube",
    "Альтернатива коротких ссылок YouTube",
    "Видеохостинг Google",
    "Изображения YouTube",
    "Изображения Google Photos",
    "Сервисы и обновления Google",
    "YouTube без cookies",
    "Интерфейс YouTube",
    "Встроенные видео YouTube",
    "YouTube API",
    "Внутренний API YouTube",
    "Загрузка видео на YouTube",
    "Служебный домен YouTube"
]

# Функция для сопоставления названия и домена
def get_site_by_name(display_name):
    index = DISPLAY_NAMES.index(display_name)
    return SITES[index]

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
