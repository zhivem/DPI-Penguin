import configparser
import logging
import os
import platform
import subprocess
import sys
import winreg
from typing import Optional, List, Dict, Tuple
from packaging.version import parse as parse_version

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QIcon, QPixmap

from utils.translationmanager import TranslationManager

TRANSLATIONS_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'translations')
settings = QSettings("Zhivem", "DPI Penguin")
translation_manager = TranslationManager(TRANSLATIONS_FOLDER)
saved_language = settings.value("language", "ru")
translation_manager.set_language(saved_language)

def tr(text: str) -> str:
    return translation_manager.translate(text)

def set_language(lang_code: str):
    translation_manager.set_language(lang_code)

BASE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ZAPRET_FOLDER = os.path.join(BASE_FOLDER, "zapret")
CONFIG_PATH = os.path.join(BASE_FOLDER, "config", 'default.ini')
CURRENT_VERSION: str = "1.7"

BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "resources", "icon")

BLACKLIST_FILES: List[str] = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "youtube-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "discord-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "disk-youtube-blacklist.txt")
]

WIN_DIVERT_COMMAND: List[str] = ["net", "stop", "WinDivert"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def open_path(path: str) -> Optional[str]:
    if not os.path.exists(path):
        logging.warning(tr("Путь не существует: {path}").format(path=path))
        return tr("Путь не существует: {path}").format(path=path)

    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return None
    except Exception as e:
        return tr("Не удалось открыть путь: {error}").format(error=e)

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
        logging.warning(tr("Модуль '{module_name}' не найден или версия не соответствует, установка...").format(module_name=module_name))
        install_module(module_name, version)

def install_module(module_name: str, version: Optional[str] = None) -> None:
    try:
        cmd = [
            sys.executable, "-m", "pip", "install",
            f"{module_name}=={version}" if version else module_name
        ]
        subprocess.check_call(cmd)
        logging.info(tr("Модуль '{module_name}' успешно установлен.").format(module_name=module_name))
    except subprocess.CalledProcessError as e:
        logging.error(tr("Ошибка установки модуля '{module_name}': {error}").format(module_name=module_name, error=e))
        raise

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
        logging.error(tr("Ошибка при проверке автозапуска: {error}").format(error=e))
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
            logging.info(tr("Автозапуск успешно установлен"))
    except Exception as e:
        logging.error(tr("Ошибка при установке автозапуска: {error}").format(error=e))
        raise

def disable_autostart() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, "WinWSApp")
            logging.info(tr("Автозапуск успешно отключен"))
    except FileNotFoundError:
        logging.info(tr("Автозапуск уже отключен"))
    except Exception as e:
        logging.error(tr("Ошибка при отключении автозапуска: {error}").format(error=e))
        raise

def get_executable_path() -> str:
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        script_path = os.path.abspath(sys.argv[0])
        return f'"{sys.executable}" "{script_path}"'

def load_script_options(config_path: str) -> Tuple[Optional[Dict[str, Tuple[str, List[str]]]], Optional[str]]:
    config = configparser.ConfigParser()
    config.optionxform = str
    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        return None, tr("Ошибка при чтении config.ini: {error}").format(error=e)

    section_counts = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1].strip()
                    section_counts[section] = section_counts.get(section, 0) + 1
    except Exception as e:
        return None, tr("Ошибка при обработке config.ini: {error}").format(error=e)

    duplicates = [name for name, count in section_counts.items() if count > 1]
    if duplicates:
        error_message = tr("Ошибка: Названия разделов конфигурации не должны повторяться: {duplicates}").format(duplicates=", ".join(duplicates))
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

    logging.info(tr("SCRIPT_OPTIONS загружены: {options}").format(options=script_options))
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
            logging.error(tr("Отсутствуют необходимые файлы: {files}").format(files=", ".join(missing_files)))
            return tr("Не удалось создать службу: отсутствуют файлы {files}.").format(files=", ".join(missing_files))

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

        logging.debug(tr("Команда для создания службы: {command}").format(command=' '.join(cmd_create)))

        subprocess.run(cmd_create, check=True)

        cmd_description = [
            'sc', 'description', 'Penguin',
            'Passive Deep Packet Inspection blocker and Active DPI circumvention utility'
        ]

        logging.debug(tr("Команда для добавления описания службы: {command}").format(command=' '.join(cmd_description)))

        subprocess.run(cmd_description, check=True)

        logging.info(tr("Служба создана и настроена для автоматического запуска"))
        return tr("Служба создана и настроена для автоматического запуска")
    except subprocess.CalledProcessError as e:
        return tr("Не удалось создать службу")
    except Exception as e:
        return tr("Не удалось создать службу из-за неизвестной ошибки")

def delete_service() -> str:
    try:
        cmd_delete = ['sc', 'delete', 'Penguin']

        logging.debug(tr("Команда для удаления службы: {command}").format(command=' '.join(cmd_delete)))

        subprocess.run(cmd_delete, check=True)
        return tr("Служба успешно удалена")
    except subprocess.CalledProcessError as e:
        logging.error(tr("Не удалось удалить службу. Ошибка: {error}").format(error=e))
        return tr("Не удалось удалить службу")
    except Exception as e:
        logging.error(tr("Неизвестная ошибка при удалении службы: {error}").format(error=e))
        return tr("Не удалось удалить службу из-за неизвестной ошибки")
