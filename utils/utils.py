import configparser
import logging
import os
import platform
import subprocess
import sys
import winreg
from typing import Optional, List, Dict, Tuple

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox
from utils.translation_utils import TranslationManager

# --- Глобальные константы и настройки ---
BASE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TRANSLATIONS_FOLDER = os.path.join(BASE_FOLDER, 'translations')
ZAPRET_FOLDER = os.path.join(BASE_FOLDER, "zapret")
CONFIG_PATH = os.path.join(BASE_FOLDER, "config", 'default.ini')
SETTING_VER = os.path.join(BASE_FOLDER, "setting_version", "version_config.ini")
FIX_BAT_PATH = os.path.join(BASE_FOLDER, "resources", "fix-process", "fix.bat")
BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "resources", "icon")
BLACKLIST_FILES: List[str] = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "disk-youtube-blacklist.txt"),
    os.path.join(BLACKLIST_FOLDER, "universal.txt")
]

# --- Логгер ---
logger = logging.getLogger("dpipenguin") 

# --- Переводы и настройки ---
settings = QSettings("Zhivem", "DPI Penguin")
translation_manager = TranslationManager(TRANSLATIONS_FOLDER)
saved_language = settings.value("language", "ru")
translation_manager.set_language(saved_language)

def tr(text: str) -> str:
    """Функция для перевода текста."""
    return translation_manager.translate(text)

def set_language(lang_code: str) -> None:
    """Устанавливает язык приложения."""
    translation_manager.set_language(lang_code)

# --- Загрузка версий ---
config = configparser.ConfigParser()
config.read(SETTING_VER)
CURRENT_VERSION = config.get('VERSION', 'ver_programm')
ZAPRET_VERSION = config.get('VERSION', 'zapret')
CONFIG_VERSION = config.get('VERSION', 'config')

# --- Функции работы с путями и автозапуском ---
def open_path(path: str) -> Optional[str]:
    """Открывает указанный путь в файловом менеджере (только для Windows)."""
    if not os.path.exists(path):
        msg = tr("Путь не существует: {path}").format(path=path)
        logger.warning(msg)
        return msg
    if platform.system() != "Windows":
        msg = tr("Данная функция поддерживается только на Windows.")
        logger.warning(msg)
        return msg
    try:
        os.startfile(path)
        return None
    except Exception as e:
        msg = tr("Не удалось открыть путь: {error}").format(error=e)
        logger.error(msg)
        return msg

def get_executable_path() -> str:
    """Возвращает путь к исполняемому файлу приложения."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

def is_autostart_enabled() -> bool:
    """Проверяет, включен ли автозапуск приложения."""
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
        logger.error(tr("Ошибка при проверке автозапуска: {error}").format(error=e))
        return False

def enable_autostart() -> None:
    """Включает автозапуск приложения."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "WinWSApp", 0, winreg.REG_SZ, get_executable_path())
            logger.info(tr("Автозапуск успешно установлен"))
    except Exception as e:
        logger.error(tr("Ошибка при установке автозапуска: {error}").format(error=e))
        raise

def disable_autostart() -> None:
    """Отключает автозапуск приложения."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, "WinWSApp")
            logger.info(tr("Автозапуск успешно отключен"))
    except FileNotFoundError:
        logger.info(tr("Автозапуск уже отключен"))
    except Exception as e:
        logger.error(tr("Ошибка при отключении автозапуска: {error}").format(error=e))
        raise

# --- Работа с конфигом скриптов ---
def load_script_options(config_path: str) -> Tuple[Optional[Dict[str, Tuple[str, List[str]]]], Optional[str]]:
    """Загружает опции скрипта из конфигурационного файла."""
    config = configparser.ConfigParser()
    config.optionxform = str
    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        msg = tr("Ошибка при чтении config.ini: {error}").format(error=e)
        logger.error(msg)
        return None, msg

    # Проверка на дубли секций
    section_counts = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('[') and line.strip().endswith(']'):
                    section = line.strip()[1:-1]
                    section_counts[section] = section_counts.get(section, 0) + 1
    except Exception as e:
        msg = tr("Ошибка при обработке config.ini: {error}").format(error=e)
        logger.error(msg)
        return None, msg

    duplicates = [name for name, count in section_counts.items() if count > 1]
    if duplicates:
        msg = tr("Ошибка: Названия разделов конфигурации не должны повторяться: {duplicates}").format(
            duplicates=", ".join(duplicates)
        )
        logger.error(msg)
        return None, msg

    script_options = {}
    for section in config.sections():
        if section == "SCRIPT_OPTIONS":
            continue
        executable = config.get(section, 'executable', fallback=None)
        args = config.get(section, 'args', fallback='')
        args_list = [arg.strip() for arg in ' '.join(args.splitlines()).split(';') if arg.strip()] if args else []

        # Подстановка путей
        args_list = [
            arg.replace('{ZAPRET_FOLDER}', ZAPRET_FOLDER)
               .replace('{BLACKLIST_FOLDER}', BLACKLIST_FOLDER)
               .replace('{BLACKLIST_FILES_0}', BLACKLIST_FILES[0])
               .replace('{BLACKLIST_FILES_1}', BLACKLIST_FILES[1])
               .replace('{BLACKLIST_FILES_2}', BLACKLIST_FILES[2])
               .replace('{BASE_FOLDER}', BASE_FOLDER)
            for arg in args_list
        ]
        if executable:
            executable = executable.replace('{ZAPRET_FOLDER}', ZAPRET_FOLDER).replace('{BASE_FOLDER}', BASE_FOLDER)
            if not os.path.isabs(executable):
                executable = os.path.join(BASE_FOLDER, executable)
        script_options[section] = (executable, args_list)

    logger.info(tr("SCRIPT_OPTIONS успешно загружены"))
    return script_options, None

# --- Работа со службой Windows ---
def _run_sc_command(args: List[str], error_msg: str) -> str:
    """Вспомогательная функция для запуска команд sc."""
    try:
        popen_params = {
            'args': args,
            'check': True,
            'shell': False,
            'creationflags': subprocess.CREATE_NO_WINDOW,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'text': True
        }
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            popen_params['startupinfo'] = startupinfo
        subprocess.run(**popen_params)
        return ""
    except subprocess.CalledProcessError as e:
        logger.error(error_msg.format(error=e))
        return error_msg.format(error=e)
    except Exception as e:
        logger.error(error_msg.format(error=e))
        return error_msg.format(error=e)

def create_service() -> str:
    """Создает и настраивает службу Windows."""
    try:
        binary_path = os.path.join(ZAPRET_FOLDER, "winws.exe")
        blacklist_path = BLACKLIST_FILES[2]
        quic_initial = os.path.join(ZAPRET_FOLDER, "quic_initial_www_google_com.bin")
        ipset = os.path.join(BLACKLIST_FOLDER, "ipset-discord.txt")
        ts = os.path.join(ZAPRET_FOLDER, "tls_clienthello_www_google_com.bin")
        required_files = [binary_path, blacklist_path, quic_initial, ipset, ts]
        missing_files = [f for f in required_files if not os.path.exists(f)]
        if missing_files:
            logger.error(tr("Отсутствуют необходимые файлы: {files}").format(files=", ".join(missing_files)))
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
            f'--dpi-desync=fake,split '
            f'--dpi-desync-autottl=2 '
            f'--dpi-desync-repeats=6 '
            f'--dpi-desync-fooling=badseq '
            f'--dpi-desync-fake-tls={ts}"'
        )
        # Создание службы
        err = _run_sc_command(
            ['sc', 'create', 'Penguin', f'binPath= {bin_path_with_args}'],
            tr("Ошибка при создании службы: {error}")
        )
        if err:
            return tr("Не удалось создать службу")

        # Описание службы
        err = _run_sc_command(
            ['sc', 'description', 'Penguin', 'Passive Deep Packet Inspection blocker and Active DPI circumvention utility'],
            tr("Ошибка при добавлении описания службы: {error}")
        )
        if err:
            return tr("Не удалось добавить описание службы")

        logger.info(tr("Служба создана и настроена для автоматического запуска"))
        return tr("Служба создана и настроена для автоматического запуска")
    except Exception as e:
        logger.error(tr("Не удалось создать службу из-за неизвестной ошибки: {error}").format(error=e))
        return tr("Не удалось создать службу из-за неизвестной ошибки")

def delete_service() -> str:
    """Удаляет службу Windows."""
    err = _run_sc_command(
        ['sc', 'delete', 'Penguin'],
        tr("Не удалось удалить службу. Ошибка: {error}")
    )
    if err:
        return tr("Не удалось удалить службу")
    logger.info(tr("Служба успешно удалена"))
    return tr("Служба успешно удалена")

# --- Исправление через fix.bat ---
def start_fix_process(parent) -> None:
    """Запускает процесс исправления через fix.bat."""
    if not os.path.exists(FIX_BAT_PATH):
        logger.error(tr("Файл исправления не найден: {path}").format(path=FIX_BAT_PATH))
        QMessageBox.warning(parent, tr("Ошибка"), tr("Файл {path} не найден").format(path=FIX_BAT_PATH))
        return
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run([FIX_BAT_PATH], startupinfo=startupinfo)
        logger.info(tr("Процесс исправления завершён успешно"))
        QMessageBox.information(parent, tr("Исправление"), tr("Процесс исправления завершен успешно"))
    except subprocess.CalledProcessError:
        logger.warning(tr("Частичное исправление завершено с ошибкой"))
        QMessageBox.warning(parent, tr("Частичное исправление"), tr("Частичное исправление завершено"))
    except Exception as e:
        logger.error(tr("Ошибка при выполнении процесса исправления: {error}").format(error=e))
        QMessageBox.warning(parent, tr("Служба и процесс"), tr("Успешно завершено, запустите обход блокировки снова"))