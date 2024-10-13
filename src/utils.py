import logging
import os
import platform
import subprocess
import sys
import winreg

from packaging.version import parse as parse_version

import requests

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
    """Определяет архитектуру системы."""
    return "x86_64" if platform.architecture()[0] == "64bit" else "x86"


GOODBYE_DPI_EXE = os.path.join(BASE_FOLDER, "bin", get_architecture(), "goodbyedpi.exe")
WIN_DIVERT_COMMAND = ["net", "stop", "WinDivert"]
GOODBYE_DPI_PROCESS_NAME = "goodbyedpi.exe"

current_version = "1.5.2"  # Версия приложения

SITES = [
    "youtube.com", "youtu.be", "yt.be", "discord.com", "gateway.discord.gg",
    "discord.gg", "discordcdn.com", "youtube-nocookie.com", "youtube-ui.l.google.com",
    "youtubeembeddedplayer.googleapis.com", "youtube.googleapis.com",
    "youtubei.googleapis.com", "yt-video-upload.l.google.com",
    "wide-youtube.l.google.com"
]

DISPLAY_NAMES = [
    "Основной сайт YouTube", "Короткие ссылки YouTube",
    "Альтернатива коротких ссылок YouTube", "Основной сайт Discord",
    "Веб-сокет Discord", "Приглашения на серверы Discord",
    "CDN сервис Discord по глобальной сети", "YouTube без cookies",
    "Интерфейс YouTube", "Встроенные видео YouTube", "YouTube API",
    "Внутренний API YouTube", "Загрузка видео на YouTube",
    "Служебный домен YouTube"
]


def get_site_by_name(display_name):
    """Получает URL сайта по его отображаемому имени."""
    try:
        return SITES[DISPLAY_NAMES.index(display_name)]
    except ValueError:
        logging.error(f"Сайт с именем {display_name} не найден.")
        return ""


def ensure_module_installed(module_name, version=None):
    """Проверяет, установлен ли модуль, и устанавливает его при необходимости."""
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
    """Устанавливает указанный модуль через pip."""
    try:
        cmd = [
            sys.executable, "-m", "pip", "install",
            f"{module_name}=={version}" if version else module_name
        ]
        subprocess.check_call(cmd)
        logging.info(f"Модуль {module_name} успешно установлен.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка установки модуля {module_name}: {e}")


def get_latest_version():
    """Получает последнюю доступную версию приложения с GitHub API."""
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
    """Сравнивает текущую версию с последней доступной."""
    return parse_version(latest) > parse_version(current)


SCRIPT_OPTIONS = {
    "Обход блокировок YouTube (Актуальный метод)": (
        GOODBYE_DPI_EXE, ["-5", "-e1 ", "-q", "--fake-gen","5","--fake-from-hex=160301FFFF01FFFFFF0303594F5552204144564552544953454D454E542048455245202D202431302F6D6F000000000009000000050003000000", "--blacklist", BLACKLIST_FILES[1]]
    ),

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


def is_autostart_enabled():
    """Проверяет, включен ли автозапуск приложения."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, "GoodbyeDPIApp")
        key.Close()
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logging.error(f"Ошибка при проверке автозапуска: {e}")
        return False


def enable_autostart():
    """Включает автозапуск приложения."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if getattr(sys, 'frozen', False):
            executable_path = sys.executable
        else:
            executable_path = os.path.abspath(__file__)
            executable_path = f'python "{executable_path}"'
        winreg.SetValueEx(key, "GoodbyeDPIApp", 0, winreg.REG_SZ, executable_path)
        key.Close()
        logging.info("Автозапуск успешно настроен.")
    except Exception as e:
        logging.error(f"Ошибка при настройке автозапуска: {e}")
        raise


def disable_autostart():
    """Выключает автозапуск приложения."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "GoodbyeDPIApp")
        key.Close()
        logging.info("Автозапуск успешно удален.")
   

    except FileNotFoundError:
        pass
    except Exception as e:
        logging.error(f"Error removing autostart: {e}")
        raise

def create_service():
    try:
        arch = 'x86_64' if platform.machine().endswith('64') else 'x86'
        binary_path = f'"{os.path.join(BASE_FOLDER, arch, "goodbyedpi.exe")}"'
        blacklist_path = f'"{os.path.join(BASE_FOLDER, "russia-blacklist.txt")}"'
        youtube_blacklist_path = f'"{os.path.join(BASE_FOLDER, "russia-youtube.txt")}"'

        subprocess.run([
            'sc', 'create', 'GoodbyeDPI',
            f'binPath= {binary_path} -9 --blacklist {blacklist_path} --blacklist {youtube_blacklist_path}',
            'start=', 'auto'
        ], check=True)

        subprocess.run([
            'sc', 'description', 'GoodbyeDPI',
            'Passive Deep Packet Inspection blocker and Active DPI circumvention utility'
        ], check=True)

        logging.info("Служба 'GoodbyeDPI' создана и настроена для автоматического запуска.")
        return "Служба 'GoodbyeDPI' создана и настроена для автоматического запуска."
    except subprocess.CalledProcessError:
        logging.error("Не удалось создать службу.")
        return "Не удалось создать службу."

def delete_service():
    try:
        subprocess.run(['sc', 'delete', 'GoodbyeDPI'], check=True)
        logging.info("Служба 'GoodbyeDPI' успешно удалена.")
        return "Служба 'GoodbyeDPI' успешно удалена."
    except subprocess.CalledProcessError:
        logging.error("Не удалось удалить службу.")
        return "Не удалось удалить службу."

def open_txt_file(file_path):
     if os.path.exists(file_path):
        try:
            subprocess.Popen(['notepad.exe', file_path])
            return None
        except Exception as e:
            return f"Не удалось открыть файл: {e}"