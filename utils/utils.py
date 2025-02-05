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

# Создаем логгер
logger = logging.getLogger(__name__)

# Константы и глобальные настройки
BASE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TRANSLATIONS_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'translations')
ZAPRET_FOLDER = os.path.join(BASE_FOLDER, "zapret")
CONFIG_PATH = os.path.join(BASE_FOLDER, "config", 'default.ini')
SETTING_VER = os.path.join(BASE_FOLDER, "setting_version", "version_config.ini")

FIX_BAT_PATH = os.path.join(BASE_FOLDER, "resources", "fix-process", "fix.bat")

BLACKLIST_FOLDER = os.path.join(BASE_FOLDER, "black")
ICON_FOLDER = os.path.join(BASE_FOLDER, "resources", "icon")

BLACKLIST_FILES: List[str] = [
    os.path.join(BLACKLIST_FOLDER, "russia-blacklist.txt"), # 0
    os.path.join(BLACKLIST_FOLDER, "disk-youtube-blacklist.txt"), # 1
    os.path.join(BLACKLIST_FOLDER, "universal.txt") # 2
]

# Инициализация менеджера переводов и настроек
settings = QSettings("Zhivem", "DPI Penguin")
translation_manager = TranslationManager(TRANSLATIONS_FOLDER)
saved_language = settings.value("language", "ru")
translation_manager.set_language(saved_language)

def tr(text: str) -> str:
    """
    Функция для перевода текста.
    """
    return translation_manager.translate(text)

def set_language(lang_code: str):
    """
    Устанавливает язык приложения.
    """
    translation_manager.set_language(lang_code)

# Загрузка конфигурации
config = configparser.ConfigParser()
config.read(SETTING_VER)

CURRENT_VERSION = config.get('VERSION', 'ver_programm')
ZAPRET_VERSION = config.get('VERSION', 'zapret')
CONFIG_VERSION = config.get('VERSION', 'config')

def open_path(path: str) -> Optional[str]:
    """
    Открывает указанный путь в файловом менеджере (только для Windows).
    Возвращает сообщение об ошибке, если путь не существует или не удалось открыть.
    """
    if not os.path.exists(path):
        message = tr("Путь не существует: {path}").format(path=path)
        logger.warning(message)
        return message

    if platform.system() != "Windows":
        message = tr("Данная функция поддерживается только на Windows.")
        logger.warning(message)
        return message
    try:
        os.startfile(path) 
        return None
    except Exception as e:
        error_message = tr("Не удалось открыть путь: {error}").format(error=e)
        logger.error(error_message)
        return error_message
    
def is_autostart_enabled() -> bool:
    """
    Проверяет, включен ли автозапуск приложения.
    """
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
    """
    Включает автозапуск приложения.
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        ) as key:
            executable_path = get_executable_path()
            winreg.SetValueEx(key, "WinWSApp", 0, winreg.REG_SZ, executable_path)
            logger.info(tr("Автозапуск успешно установлен"))
    except Exception as e:
        logger.error(tr("Ошибка при установке автозапуска: {error}").format(error=e))
        raise


def disable_autostart() -> None:
    """
    Отключает автозапуск приложения.
    """
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


def get_executable_path() -> str:
    """
    Возвращает путь к исполняемому файлу приложения.
    """
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        script_path = os.path.abspath(sys.argv[0])
        return f'"{sys.executable}" "{script_path}"'


def load_script_options(config_path: str) -> Tuple[Optional[Dict[str, Tuple[str, List[str]]]], Optional[str]]:
    """
    Загружает опции скрипта из конфигурационного файла.
    Возвращает словарь опций и сообщение об ошибке, если оно произошло.
    """
    config = configparser.ConfigParser()
    config.optionxform = str
    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        return None, tr("Ошибка при чтении config.ini: {error}").format(error=e)

    # Проверка на дублирующиеся секции
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
        error_message = tr("Ошибка: Названия разделов конфигурации не должны повторяться: {duplicates}").format(
            duplicates=", ".join(duplicates)
        )
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
               .replace('{BASE_FOLDER}', BASE_FOLDER)
            for arg in args_list
        ]

        if executable:
            executable = executable.replace('{ZAPRET_FOLDER}', ZAPRET_FOLDER)\
                                   .replace('{BASE_FOLDER}', BASE_FOLDER)
            if not os.path.isabs(executable):
                executable = os.path.join(BASE_FOLDER, executable)

        script_options[section] = (executable, args_list)

    logger.info(tr("SCRIPT_OPTIONS загружены: {options}").format(options=script_options))
    return script_options, None


def create_service() -> str:
    """
    Создает и настраивает службу Windows.
    Возвращает сообщение об успехе или ошибке.
    """
    try:
        binary_path = os.path.join(ZAPRET_FOLDER, "winws.exe")
        blacklist_path = BLACKLIST_FILES[3]
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

        logger.debug(tr("Команда для создания службы: {command}").format(command=' '.join(cmd_create)))

        popen_params = {
            'args': cmd_create,
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

        cmd_description = [
            'sc', 'description', 'Penguin',
            'Passive Deep Packet Inspection blocker and Active DPI circumvention utility'
        ]

        logger.debug(tr("Команда для добавления описания службы: {command}").format(command=' '.join(cmd_description)))

        popen_params_description = {
            'args': cmd_description,
            'check': True,
            'shell': False,
            'creationflags': subprocess.CREATE_NO_WINDOW,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'text': True
        }

        if os.name == 'nt':
            popen_params_description['startupinfo'] = startupinfo

        subprocess.run(**popen_params_description)

        logger.info(tr("Служба создана и настроена для автоматического запуска"))
        return tr("Служба создана и настроена для автоматического запуска")
    except subprocess.CalledProcessError as e:
        logger.error(tr("Ошибка при создании службы: {error}").format(error=e))
        return tr("Не удалось создать службу")
    except Exception as e:
        logger.error(tr("Не удалось создать службу из-за неизвестной ошибки: {error}").format(error=e))
        return tr("Не удалось создать службу из-за неизвестной ошибки")


def delete_service() -> str:
    """
    Удаляет службу Windows.
    Возвращает сообщение об успехе или ошибке.
    """
    try:
        cmd_delete = ['sc', 'delete', 'Penguin']

        logger.debug(tr("Команда для удаления службы: {command}").format(command=' '.join(cmd_delete)))

        popen_params = {
            'args': cmd_delete,
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

        logger.info(tr("Служба успешно удалена"))
        return tr("Служба успешно удалена")
    except subprocess.CalledProcessError as e:
        logger.error(tr("Не удалось удалить службу. Ошибка: {error}").format(error=e))
        return tr("Не удалось удалить службу")
    except Exception as e:
        logger.error(tr("Неизвестная ошибка при удалении службы: {error}").format(error=e))
        return tr("Не удалось удалить службу из-за неизвестной ошибки")

def start_fix_process(parent):
    if os.path.exists(FIX_BAT_PATH):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(
                [FIX_BAT_PATH],
                startupinfo=startupinfo
            )
            QMessageBox.information(parent, "Исправление", "Процесс исправления завершен успешно")
        except subprocess.CalledProcessError:
            QMessageBox.warning(parent, "Частичное исправление", "Частичное исправление завершено")
        except Exception:
            QMessageBox.warning(parent, "Служба и процесс", "Успешно завершено, запустите обход блокировки снова")
    else:
        QMessageBox.warning(parent, "Ошибка", f"Файл {FIX_BAT_PATH} не найден")