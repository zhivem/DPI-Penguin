import os
import platform
import subprocess
import sys
import logging

# Функция для получения архитектуры системы (x86 или x86_64).
def get_architecture():
    return "x86_64" if platform.architecture()[0] == "64bit" else "x86"

# Определение базовой папки для файлов.
BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

# Пути к файлам черного списка.
BLACKLIST_FILES = [
    os.path.join(BASE_FOLDER, "russia-blacklist.txt"),
    os.path.join(BASE_FOLDER, "russia-youtube.txt")
]

# Путь к исполняемому файлу GoodbyeDPI.
GOODBYE_DPI_EXE = os.path.join(BASE_FOLDER, get_architecture(), "goodbyedpi.exe")

# Команда для остановки WinDivert (сетевая утилита).
WIN_DIVERT_COMMAND = ["net", "stop", "WinDivert"]

# Имя процесса GoodbyeDPI.
GOODBYE_DPI_PROCESS_NAME = "goodbyedpi.exe"

# Текущая версия программы.
current_version = '1.1'

# Функция для установки модуля через pip, если он не установлен.
def ensure_module_installed(module_name):
    try:
        __import__(module_name)  # Пытаемся импортировать модуль
    except ImportError:
        # Если модуль не найден, выводим предупреждение и устанавливаем его.
        logging.warning(f"Модуль {module_name} не найден, установка...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])

# Функция для получения последней версии программы с GitHub.
def get_latest_version():
    import requests
    # URL для получения информации о последнем релизе с GitHub.
    url = 'https://api.github.com/repos/{owner}/{repo}/releases/latest'.format(owner='zhivem', repo='GUI')
    try:
        # Выполняем запрос на получение информации о последнем релизе.
        response = requests.get(url)
        if response.status_code == 200:
            # Возвращаем версию последнего релиза.
            data = response.json()
            return data['tag_name']
        logging.warning(f"Не удалось получить последнюю версию. Код ответа: {response.status_code}")
        return None
    except requests.RequestException as e:
        # Логирование ошибки при запросе.
        logging.error(f"Ошибка запроса к GitHub API: {e}")
        return None

# Функция для сравнения версий (последней и текущей).
def is_newer_version(latest, current):
    from packaging.version import parse as parse_version  # Используем модуль packaging для сравнения версий
