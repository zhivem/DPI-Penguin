import configparser
import logging
import os
import platform
import subprocess
import sys
import winreg
from typing import Optional, List, Dict, Tuple

from packaging.version import parse as parse_version
import requests

from PyQt6.QtGui import QColor, QIcon, QPixmap

BASE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ZAPRET_FOLDER = os.path.join(BASE_FOLDER, "zapret")
CONFIG_PATH = os.path.join(BASE_FOLDER, "config", 'config.ini')
CURRENT_VERSION: str = "1.6.2"

BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "resources", "icon")
BIN_FOLDER = os.path.join(BASE_FOLDER, "bin")

BLACKLIST_FILES: List[str] = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "russia-youtube.txt"),
    os.path.join(BLACKLIST_FOLDER, "discord-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "disk-youtube.txt")
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

GOODBYE_DPI_PROCESS_NAME: str = "goodbyedpi.exe"
WIN_DIVERT_COMMAND: List[str] = ["net", "stop", "WinDivert"]

def get_architecture() -> str:
    """
    Определяет архитектуру системы.

    Returns:
        str: "x86_64" для 64-битных систем, "x86" для 32-битных.
    """
    return "x86_64" if platform.architecture()[0] == "64bit" else "x86"

def get_goodbye_dpi_exe() -> str:
    """
    Возвращает путь к исполняемому файлу GoodbyeDPI в зависимости от архитектуры.

    Returns:
        str: Полный путь к goodbyedpi.exe.
    """
    return os.path.join(BIN_FOLDER, get_architecture(), "goodbyedpi.exe")

GOODBYE_DPI_EXE: str = get_goodbye_dpi_exe()

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

def open_path(path: str) -> Optional[str]:
    """
    Открывает указанный путь в файловом менеджере.

    Args:
        path (str): Путь к папке или файлу.

    Returns:
        Optional[str]: Сообщение об ошибке, если не удалось открыть путь, иначе None.
    """
    if not os.path.exists(path):
        logging.warning(f"Путь не существует: {path}")
        return f"Путь не существует: {path}"

    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin": 
            subprocess.Popen(["open", path])
        else: 
            subprocess.Popen(["xdg-open", path])
        logging.info(f"Путь '{path}' открыт.")
        return None
    except Exception as e:
        logging.error(f"Не удалось открыть путь '{path}': {e}")
        return f"Не удалось открыть путь: {e}"

def create_status_icon(color: str, size: Tuple[int, int] = (12, 12)) -> QIcon:
    """
    Создает иконку статуса заданного цвета.

    Args:
        color (str): Цвет иконки (например, 'gray', 'green', 'red').
        size (Tuple[int, int], optional): Размер иконки. По умолчанию (12, 12).

    Returns:
        QIcon: Созданная иконка.
    """
    pixmap = QPixmap(*size)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)

def ensure_module_installed(module_name: str, version: Optional[str] = None) -> None:
    """
    Проверяет, установлен ли модуль с указанной версией. Если нет, устанавливает его.

    Args:
        module_name (str): Название модуля.
        version (Optional[str], optional): Необходимая версия модуля. По умолчанию None.
    """
    try:
        __import__(module_name)
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
        raise

def get_latest_version() -> Optional[str]:
    """
    Получает последнюю версию приложения из GitHub API.

    Returns:
        Optional[str]: Тег последней версии, если успешно получен, иначе None.
    """
    url = 'https://api.github.com/repos/zhivem/DPI-Penguin/releases/latest'
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
            executable_path = get_executable_path()
            winreg.SetValueEx(key, "GoodbyeDPIApp", 0, winreg.REG_SZ, executable_path)
            logging.info("Автозапуск успешно установлен.")
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
            logging.info("Автозапуск успешно отключен.")
    except FileNotFoundError:
        logging.info("Автозапуск уже отключен.")
    except Exception as e:
        logging.error(f"Ошибка при отключении автозапуска: {e}")
        raise

def get_executable_path() -> str:
    """
    Определяет путь к исполняемому файлу приложения.

    Returns:
        str: Полный путь к исполняемому файлу.
    """
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        script_path = os.path.abspath(sys.argv[0])
        return f'python "{script_path}"'

def create_service() -> str:
    """
    Создает службу Windows для приложения GoodbyeDPI.

    Returns:
        str: Сообщение о результате создания службы.
    """
    try:
        arch = get_architecture()
        binary_path = f'"{os.path.join(BIN_FOLDER, arch, "goodbyedpi.exe")}"'
        blacklist_path = f'"{BLACKLIST_FILES[0]}"'
        youtube_blacklist_path = f'"{BLACKLIST_FILES[1]}"'

        cmd_create = [
            'sc', 'create', 'Penguin',
            f'binPath= {binary_path} -e1 -q --fake-gen=5 --fake-from-hex=160301FFFF01FFFFFF0303594F5552204144564552544953454D454E542048455245202D202431302F6D6F000000000009000000050003000000 {blacklist_path} --blacklist {youtube_blacklist_path}',
            'start=', 'auto'
        ]
        subprocess.run(cmd_create, check=True)

        cmd_description = [
            'sc', 'description', 'Penguin',
            'Passive Deep Packet Inspection blocker and Active DPI circumvention utility'
        ]
        subprocess.run(cmd_description, check=True)

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
        subprocess.run(['sc', 'delete', 'Penguin'], check=True)
        logging.info("Служба успешно удалена.")
        return "Служба успешно удалена."
    except subprocess.CalledProcessError:
        logging.error("Не удалось удалить службу.")
        return "Не удалось удалить службу."
    except Exception as e:
        logging.error(f"Неизвестная ошибка при удалении службы: {e}")
        return "Не удалось удалить службу из-за неизвестной ошибки."

def load_script_options(config_path: str) -> Tuple[Optional[Dict[str, Tuple[str, List[str]]]], Optional[str]]:
    """
    Загружает SCRIPT_OPTIONS из файла конфигурации и проверяет на дублирование разделов.

    Args:
        config_path (str): Путь к файлу конфигурации.

    Returns:
        Tuple[Optional[Dict[str, Tuple[str, List[str]]]], Optional[str]]:
            - Словарь с опциями скриптов, если ошибок нет, иначе None.
            - Сообщение об ошибке, если дублирующиеся разделы найдены, иначе None.
    """
    config = configparser.ConfigParser()
    config.optionxform = str
    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        logging.error(f"Ошибка при чтении default.ini: {e}")
        return None, f"Ошибка при чтении default.ini: Названия конфигураций не должны повторяться!"

    section_counts = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1].strip()
                    section_counts[section] = section_counts.get(section, 0) + 1
    except Exception as e:
        logging.error(f"Ошибка при обработке default.ini: {e}")
        return None, f"Ошибка при обработке default.ini: {e}"

    duplicates = [name for name, count in section_counts.items() if count > 1]
    if duplicates:
        error_message = "Ошибка: Названия разделов конфигурации не должны повторяться: " + ", ".join(duplicates)
        logging.error(error_message)
        return None, error_message

    script_options = {}
    for section in config.sections():
        if section == "SCRIPT_OPTIONS":
            continue 

        executable = config.get(section, 'executable', fallback=None)
        args = config.get(section, 'args', fallback='')

        args = ' '.join(args.splitlines())

        args_list = [arg.strip() for arg in args.split(';') if arg.strip()] if args else []

        args_list = [
            arg.replace('{ZAPRET_FOLDER}', ZAPRET_FOLDER)
               .replace('{BLACKLIST_FILES_0}', BLACKLIST_FILES[0])
               .replace('{BLACKLIST_FILES_1}', BLACKLIST_FILES[1])
               .replace('{BLACKLIST_FILES_2}', BLACKLIST_FILES[2])
               .replace('{BLACKLIST_FILES_3}', BLACKLIST_FILES[3])
               .replace('{BASE_FOLDER}', BASE_FOLDER)
               .replace('{architecture}', get_architecture())
            for arg in args_list
        ]

        if executable:
            executable = executable.replace('{ZAPRET_FOLDER}', ZAPRET_FOLDER)\
                                   .replace('{BASE_FOLDER}', BASE_FOLDER)\
                                   .replace('{architecture}', get_architecture())
            if not os.path.isabs(executable):
                executable = os.path.join(BASE_FOLDER, executable)

        script_options[section] = (executable, args_list)

    logging.info(f"SCRIPT_OPTIONS загружены: {script_options}")
    return script_options, None
