import configparser  
import logging
import os
import subprocess
import platform
import sys
import winreg
from typing import Optional, List, Dict, Tuple

from packaging.version import parse as parse_version
import requests

from PyQt6.QtGui import QColor, QIcon, QPixmap

BASE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ZAPRET_FOLDER = os.path.join(BASE_FOLDER, "zapret")
CONFIG_PATH = os.path.join(BASE_FOLDER, "config", 'default.ini')
CURRENT_VERSION: str = "1.6.3"

BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "resources", "icon")

BLACKLIST_FILES: List[str] = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"), 
    os.path.join(BLACKLIST_FOLDER, "youtube-blacklist.txt"), 
    os.path.join(BLACKLIST_FOLDER, "discord-blacklist.txt"), 
    os.path.join(BLACKLIST_FOLDER, "disk-youtube-blacklist.txt")
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

WIN_DIVERT_COMMAND: List[str] = ["net", "stop", "WinDivert"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_site_by_name(display_name: str) -> str:
    try:
        return SITES[DISPLAY_NAMES.index(display_name)]
    except ValueError:
        logging.error(f"Сайт с именем '{display_name}' не найден.")
        return ""

def open_path(path: str) -> Optional[str]:
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
    pixmap = QPixmap(*size)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)

def ensure_module_installed(module_name: str, version: Optional[str] = None) -> None:
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
    return parse_version(latest) > parse_version(current)

def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, "WinWSApp")
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logging.error(f"Ошибка при проверке автозапуска: {e}")
        return False

def enable_autostart() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            executable_path = get_executable_path()
            winreg.SetValueEx(key, "WinWSApp", 0, winreg.REG_SZ, executable_path)
            logging.info("Автозапуск успешно установлен.")
    except Exception as e:
        logging.error(f"Ошибка при установке автозапуска: {e}")
        raise

def disable_autostart() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, "WinWSApp")
            logging.info("Автозапуск успешно отключен.")
    except FileNotFoundError:
        logging.info("Автозапуск уже отключен.")
    except Exception as e:
        logging.error(f"Ошибка при отключении автозапуска: {e}")
        raise

def get_executable_path() -> str:
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        script_path = os.path.abspath(sys.argv[0])
        return f'python "{script_path}"'

def load_script_options(config_path: str) -> Tuple[Optional[Dict[str, Tuple[str, List[str]]]], Optional[str]]:
    config = configparser.ConfigParser()
    config.optionxform = str
    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        logging.error(f"Ошибка при чтении config.ini: {e}")
        return None, f"Ошибка при чтении config.ini: {e}"

    section_counts = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1].strip()
                    section_counts[section] = section_counts.get(section, 0) + 1
    except Exception as e:
        logging.error(f"Ошибка при обработке config.ini: {e}")
        return None, f"Ошибка при обработке config.ini: {e}"

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
               .replace('{BLACKLIST_FOLDER}', BLACKLIST_FOLDER)
               .replace('{BLACKLIST_FILES_0}', BLACKLIST_FILES[0])
               .replace('{BLACKLIST_FILES_1}', BLACKLIST_FILES[1])
               .replace('{BLACKLIST_FILES_2}', BLACKLIST_FILES[2])
               .replace('{BLACKLIST_FILES_3}', BLACKLIST_FILES[3])
               .replace('{BASE_FOLDER}', BASE_FOLDER)
            for arg in args_list
        ]

        if executable:
            executable = executable.replace('{ZAPRET_FOLDER}', ZAPRET_FOLDER)\
                                   .replace('{BASE_FOLDER}', BASE_FOLDER)
            if not os.path.isabs(executable):
                executable = os.path.join(BASE_FOLDER, executable)

        script_options[section] = (executable, args_list)

    logging.info(f"SCRIPT_OPTIONS загружены: {script_options}")
    return script_options, None

def create_service() -> str:

    try:
        binary_path = os.path.join(ZAPRET_FOLDER, "winws.exe")
        blacklist_path = BLACKLIST_FILES[3]
        quic_initial = os.path.join(ZAPRET_FOLDER, "quic_initial_www_google_com.bin")
        ipset = os.path.join(BLACKLIST_FOLDER, "ipset-discord.txt")
        ts = os.path.join(ZAPRET_FOLDER, "tls_clienthello_www_google_com.bin")

        required_files = [binary_path, blacklist_path, quic_initial, ipset, ts]
        missing_files = [f for f in required_files if not os.path.exists(f)]
        if missing_files:
            logging.error(f"Отсутствуют необходимые файлы: {', '.join(missing_files)}")
            return f"Не удалось создать службу: отсутствуют файлы {', '.join(missing_files)}."

        bin_path_with_args = (
            f'"{binary_path} '
            f'--wf-tcp=80,443 '
            f'--wf-udp=443,50000-50100 '
            f'--filter-udp=443 '
            f'--hostlist={blacklist_path} '
            f'--dpi-desync=fake '
            f'--dpi-desync-repeats=6 '
            f'--dpi-desync-fake-quic={quic_initial} '
            f'--filter-udp=50000-50100 '
            f'--ipset={ipset} '
            f'--dpi-desync-any-protocol '
            f'--dpi-desync-cutoff=d3 '
            f'--filter-tcp=80 '
            f'--dpi-desync=fake,split2 '
            f'--dpi-desync-autottl=2 '
            f'--dpi-desync-fooling=md5sig '
            f'--filter-tcp=443 '
            f'--dpi-desync=fake,split '
            f'--dpi-desync-autottl=2 '
            f'--dpi-desync-repeats=6 '
            f'--dpi-desync-fooling=badseq '
            f'--dpi-desync-fake-tls={ts}"'
        )

        cmd_create = [
            'sc', 'create', 'Penguin',
            f'binPath= {bin_path_with_args}',
        ]

        logging.debug(f"Команда для создания службы: {' '.join(cmd_create)}")

        subprocess.run(cmd_create, check=True)

        cmd_description = [
            'sc', 'description', 'Penguin',
            'Passive Deep Packet Inspection blocker and Active DPI circumvention utility'
        ]

        logging.debug(f"Команда для добавления описания службы: {' '.join(cmd_description)}")

        subprocess.run(cmd_description, check=True)

        logging.info("Служба создана и настроена для автоматического запуска.")
        return "Служба создана и настроена для автоматического запуска."
    except subprocess.CalledProcessError as e:
        logging.error(f"Не удалось создать службу. Ошибка: {e}")
        return "Не удалось создать службу."
    except Exception as e:
        logging.error(f"Неизвестная ошибка при создании службы: {e}")
        return "Не удалось создать службу из-за неизвестной ошибки."

def delete_service() -> str:

    try:
        cmd_delete = ['sc', 'delete', 'Penguin']

        logging.debug(f"Команда для удаления службы: {' '.join(cmd_delete)}")

        subprocess.run(cmd_delete, check=True)
        logging.info("Служба успешно удалена.")
        return "Служба успешно удалена."
    except subprocess.CalledProcessError as e:
        logging.error(f"Не удалось удалить службу. Ошибка: {e}")
        return "Не удалось удалить службу."
    except Exception as e:
        logging.error(f"Неизвестная ошибка при удалении службы: {e}")
        return "Не удалось удалить службу из-за неизвестной ошибки."