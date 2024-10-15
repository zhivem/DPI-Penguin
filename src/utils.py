import logging
import os
import platform
import subprocess
import sys
import winreg
from typing import Optional, List

from packaging.version import parse as parse_version

import requests


# Константы и пути
BASE_FOLDER = os.path.abspath(os.path.dirname(__file__))

current_version: str = "1.5.3"  # Версия приложения

BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "icon")
ZAPRET_FOLDER = os.path.join(BASE_FOLDER, "zapret")

BLACKLIST_FILES: List[str] = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "russia-youtube.txt"),
    os.path.join(BLACKLIST_FOLDER, "discord-blacklist.txt")
]

SITES: List[str] = [
    "youtube.com", "youtu.be", "yt.be", "discord.com", "gateway.discord.gg",
    "discord.gg", "discordcdn.com", "youtube-nocookie.com", "youtube-ui.l.google.com",
    "youtubeembeddedplayer.googleapis.com", "youtube.googleapis.com",
    "youtubei.googleapis.com", "yt-video-upload.l.google.com",
    "wide-youtube.l.google.com"
]

DISPLAY_NAMES: List[str] = [
    "Основной сайт YouTube", "Короткие ссылки YouTube",
    "Альтернатива коротких ссылок YouTube", "Основной сайт Discord",
    "Веб-сокет Discord", "Приглашения на серверы Discord",
    "CDN сервис Discord по глобальной сети", "YouTube без cookies",
    "Интерфейс YouTube", "Встроенные видео YouTube", "YouTube API",
    "Внутренний API YouTube", "Загрузка видео на YouTube",
    "Служебный домен YouTube"
]


def get_architecture() -> str:
    """
    Определяет архитектуру системы.

    Returns:
        str: "x86_64" для 64-битных систем, "x86" для 32-битных.
    """
    return "x86_64" if platform.architecture()[0] == "64bit" else "x86"

GOODBYE_DPI_EXE: str = os.path.join(BASE_FOLDER, "bin", get_architecture(), "goodbyedpi.exe")
WIN_DIVERT_COMMAND: List[str] = ["net", "stop", "WinDivert"]
GOODBYE_DPI_PROCESS_NAME: str = "goodbyedpi.exe"

SCRIPT_OPTIONS: dict = {
    "Обход блокировок YouTube (Актуальный метод)": (
        GOODBYE_DPI_EXE, ["-9", "--blacklist", BLACKLIST_FILES[1]]
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


def get_site_by_name(display_name: str) -> str:
    """
    Получает URL сайта по его отображаемому имени.

    Args:
        display_name (str): Отображаемое имя сайта.

    Returns:
        str: URL сайта, если найден, иначе пустая строка.
    """
    try:
        return SITES[DISPLAY_NAMES.index(display_name)]
    except ValueError:
        logging.error(f"Сайт с именем '{display_name}' не найден.")
        return ""


def ensure_module_installed(module_name: str, version: Optional[str] = None) -> None:
    """
    Проверяет, установлен ли модуль с указанной версией. Если нет, устанавливает его.

    Args:
        module_name (str): Название модуля.
        version (Optional[str], optional): Необходимая версия модуля. По умолчанию None.
    """
    try:
        module = __import__(module_name)
        if version:
            import pkg_resources
            installed_version = pkg_resources.get_distribution(module_name).version
            if parse_version(installed_version) != parse_version(version):
                raise ImportError
    except ImportError:
        logging.warning(f"Модуль '{module_name}' не найден или версия не соответствует, установка...")
        install_module(module_name, version)


def install_module(module_name: str, version: Optional[str] = None) -> None:
    """
    Устанавливает указанный модуль с помощью pip.

    Args:
        module_name (str): Название модуля.
        version (Optional[str], optional): Необходимая версия модуля. По умолчанию None.

    Raises:
        subprocess.CalledProcessError: Если установка модуля завершилась неудачно.
    """
    try:
        cmd = [
            sys.executable, "-m", "pip", "install",
            f"{module_name}=={version}" if version else module_name
        ]
        subprocess.check_call(cmd)
        logging.info(f"Модуль '{module_name}' успешно установлен.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка установки модуля '{module_name}': {e}")


def get_latest_version() -> Optional[str]:
    """
    Получает последнюю версию приложения из GitHub API.

    Returns:
        Optional[str]: Тег последней версии, если успешно получен, иначе None.
    """
    url = 'https://github.com/zhivem/DPI-Penguin/releases/latest'
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            latest_version = response.json().get('tag_name')
            logging.debug(f"Получена последняя версия: {latest_version}")
            return latest_version
        logging.warning(f"Не удалось получить последнюю версию. Код ответа: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Ошибка запроса к GitHub API: {e}")
    return None


def is_newer_version(latest: str, current: str) -> bool:
    """
    Сравнивает версии приложения.

    Args:
        latest (str): Последняя доступная версия.
        current (str): Текущая версия приложения.

    Returns:
        bool: True, если последняя версия новее текущей, иначе False.
    """
    return parse_version(latest) > parse_version(current)


def is_autostart_enabled() -> bool:
    """
    Проверяет, включен ли автозапуск приложения при старте системы.

    Returns:
        bool: True, если автозапуск включен, иначе False.
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, "GoodbyeDPIApp")
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logging.error(f"Ошибка при проверке автозапуска: {e}")
        return False


def enable_autostart() -> None:
    """
    Включает автозапуск приложения при старте системы.
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            if getattr(sys, 'frozen', False):
                executable_path = sys.executable
            else:
                script_path = os.path.abspath(sys.argv[0])
                executable_path = f'python "{script_path}"'
            winreg.SetValueEx(key, "GoodbyeDPIApp", 0, winreg.REG_SZ, executable_path)
            logging.info("Autostart успешно установлен.")
    except Exception as e:
        logging.error(f"Ошибка при установке автозапуска: {e}")
        raise


def disable_autostart() -> None:
    """
    Отключает автозапуск приложения при старте системы.
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, "GoodbyeDPIApp")
            logging.info("Autostart успешно отключен.")
    except FileNotFoundError:
        logging.info("Autostart уже отключен.")
    except Exception as e:
        logging.error(f"Ошибка при отключении автозапуска: {e}")
        raise


def create_service() -> str:
    """
    Создает службу Windows для приложения GoodbyeDPI.

    Returns:
        str: Сообщение о результате создания службы.
    """
    try:
        arch = 'x86_64' if platform.machine().endswith('64') else 'x86'
        binary_path = f'"{os.path.join(BASE_FOLDER, arch, "goodbyedpi.exe")}"'
        blacklist_path = f'"{os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt")}"'
        youtube_blacklist_path = f'"{os.path.join(BLACKLIST_FOLDER, "russia-youtube.txt")}"'

        subprocess.run([
            'sc', 'create', 'GoodbyeDPI',
            f'binPath= {binary_path} -9 --blacklist {blacklist_path} --blacklist {youtube_blacklist_path}',
            'start=', 'auto'
        ], check=True)

        subprocess.run([
            'sc', 'description', 'GoodbyeDPI',
            'Passive Deep Packet Inspection blocker and Active DPI circumvention utility'
        ], check=True)

        logging.info("Служба создана и настроена для автоматического запуска.")
        return "Служба создана и настроена для автоматического запуска."
    except subprocess.CalledProcessError:
        logging.error("Не удалось создать службу.")
        return "Не удалось создать службу."
    except Exception as e:
        logging.error(f"Неизвестная ошибка при создании службы: {e}")
        return "Не удалось создать службу из-за неизвестной ошибки."


def delete_service() -> str:
    """
    Удаляет службу Windows для приложения GoodbyeDPI.

    Returns:
        str: Сообщение о результате удаления службы.
    """
    try:
        subprocess.run(['sc', 'delete', 'GoodbyeDPI'], check=True)
        logging.info("Служба успешно удалена.")
        return "Служба успешно удалена."
    except subprocess.CalledProcessError:
        logging.error("Не удалось удалить службу.")
        return "Не удалось удалить службу."
    except Exception as e:
        logging.error(f"Неизвестная ошибка при удалении службы: {e}")
        return "Не удалось удалить службу из-за неизвестной ошибки."


def open_txt_file(file_path: str) -> Optional[str]:
    """
    Открывает текстовый файл с помощью блокнота.

    Args:
        file_path (str): Путь к файлу.

    Returns:
        Optional[str]: Сообщение об ошибке, если не удалось открыть файл, иначе None.
    """
    if os.path.exists(file_path):
        try:
            subprocess.Popen(['notepad.exe', file_path])
            logging.info(f"Файл '{file_path}' открыт в блокноте.")
            return None
        except Exception as e:
            logging.error(f"Не удалось открыть файл '{file_path}': {e}")
            return f"Не удалось открыть файл: {e}"
    else:
        logging.warning(f"Файл не существует: {file_path}")
        return "Файл не существует."
