import os
import platform
import subprocess
import sys
import logging
import requests
from packaging.version import parse as parse_version

BASE_FOLDER = os.path.abspath(os.path.dirname(__file__))

BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "icon")
ZAPRET_FOLDER = os.path.join(BASE_FOLDER, "zapret")

BLACKLIST_FILES = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "russia-youtube.txt"),
    os.path.join(BLACKLIST_FOLDER, "discord-blacklist.txt")
]

def get_architecture():
    return "x86_64" if platform.architecture()[0] == "64bit" else "x86"

GOODBYE_DPI_EXE = os.path.join(BASE_FOLDER, "bin", get_architecture(), "goodbyedpi.exe")
WIN_DIVERT_COMMAND = ["net", "stop", "WinDivert"]
GOODBYE_DPI_PROCESS_NAME = "goodbyedpi.exe"

current_version = "1.5" #Версия

SITES = [
    "youtube.com", "youtu.be", "yt.be", "googlevideo.com", "ytimg.com",
    "ggpht.com", "gvt1.com", "youtube-nocookie.com", "youtube-ui.l.google.com",
    "youtubeembeddedplayer.googleapis.com", "youtube.googleapis.com",
    "youtubei.googleapis.com", "yt-video-upload.l.google.com",
    "wide-youtube.l.google.com"
]

DISPLAY_NAMES = [
    "Основной сайт YouTube", "Короткие ссылки YouTube",
    "Альтернатива коротких ссылок YouTube", "Видеохостинг Google",
    "Изображения YouTube", "Изображения Google Photos",
    "Сервисы и обновления Google", "YouTube без cookies",
    "Интерфейс YouTube", "Встроенные видео YouTube", "YouTube API",
    "Внутренний API YouTube", "Загрузка видео на YouTube",
    "Служебный домен YouTube"
]

def get_site_by_name(display_name):
    try:
        return SITES[DISPLAY_NAMES.index(display_name)]
    except ValueError:
        logging.error(f"Сайт с именем {display_name} не найден.")
        return ""

def ensure_module_installed(module_name, version=None):
    try:
        module = __import__(module_name)
        if version:
            import pkg_resources
            if pkg_resources.get_distribution(module_name).version != version:
                raise ImportError
    except ImportError:
        logging.warning(f"Модуль {module_name} не найден или версия не соответствует, установка...")
        install_module(module_name, version)

def install_module(module_name, version=None):
    try:
        cmd = [sys.executable, "-m", "pip", "install", f"{module_name}=={version}" if version else module_name]
        subprocess.check_call(cmd)
        logging.info(f"Модуль {module_name} успешно установлен.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка установки модуля {module_name}: {e}")

def get_latest_version():
    url = 'https://api.github.com/repos/zhivem/GoodByDPI-GUI-by-Zhivem/releases/latest'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('tag_name')
        logging.warning(f"Не удалось получить последнюю версию. Код ответа: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Ошибка запроса к GitHub API: {e}")
    return None

def is_newer_version(latest, current):
    return parse_version(latest) > parse_version(current)

SCRIPT_OPTIONS = {
    "Обход блокировок YouTube (Актуальный метод)": (
        GOODBYE_DPI_EXE, ["-9", "--blacklist", BLACKLIST_FILES[1]]
    ),

    #"Обход блокировки Discord": (
    #  GOODBYE_DPI_EXE, ["-9", "--blacklist", BLACKLIST_FILES[2]]
    #),"

    #"Обход блокировки YouTube и Discord": (
    #    GOODBYE_DPI_EXE, ["-9", "--blacklist", BLACKLIST_FILES[1], "--blacklist", BLACKLIST_FILES[2]]
    #),

     "Обход Discord + YouTube": (
        os.path.join(ZAPRET_FOLDER, "winws.exe"),
        [
            "--wf-tcp=80,443,50000-65535",
            "--wf-udp=443,50000-65535",
            "--filter-udp=443",
            f'--hostlist={os.path.join(BASE_FOLDER, "black", "discord-blacklist.txt")}',
            "--dpi-desync=fake",
            "--dpi-desync-udplen-increment=10",
            "--dpi-desync-repeats=6",
            "--dpi-desync-udplen-pattern=0xDEADBEEF",
            f'--dpi-desync-fake-quic={os.path.join(ZAPRET_FOLDER, "quic_initial_www_google_com.bin")}',
            "--new",
            "--filter-udp=50000-65535",
            "--dpi-desync=fake,tamper",
            "--dpi-desync-any-protocol",
            f'--dpi-desync-fake-quic={os.path.join(ZAPRET_FOLDER, "quic_initial_www_google_com.bin")}',
            "--new",
            "--filter-tcp=80",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            f'--dpi-desync-fake-tls={os.path.join(ZAPRET_FOLDER, "tls_clienthello_www_google_com.bin")}',
            "--new",
            "--dpi-desync=fake,disorder2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig"
        ]
    ),

    "Обход блокировки Discord": (
        os.path.join(ZAPRET_FOLDER, "winws.exe"),
        [
            "--wf-tcp=443",
            "--wf-udp=443,50000-65535",
            "--filter-udp=443",
            f'--hostlist={os.path.join(BASE_FOLDER, "black", "discord-blacklist.txt")}',
            "--dpi-desync=fake",
            "--dpi-desync-udplen-increment=10",
            "--dpi-desync-repeats=6",
            "--dpi-desync-udplen-pattern=0xDEADBEEF",
            f'--dpi-desync-fake-quic={os.path.join(ZAPRET_FOLDER, "quic_initial_www_google_com.bin")}',
            "--new",
            "--filter-udp=50000-65535",
            "--dpi-desync=fake,tamper",
            "--dpi-desync-any-protocol",
            f'--dpi-desync-fake-quic={os.path.join(ZAPRET_FOLDER, "quic_initial_www_google_com.bin")}',
            "--new",
            "--filter-tcp=443",
            f'--hostlist={os.path.join(BASE_FOLDER, "black", "discord-blacklist.txt")}',
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            f'--dpi-desync-fake-tls={os.path.join(ZAPRET_FOLDER, "tls_clienthello_www_google_com.bin")}'
        ]
    ),

        "Обход блокировок для всех сайтов": (
        GOODBYE_DPI_EXE, ["-9", "--blacklist", BLACKLIST_FILES[0]]
    )
}
