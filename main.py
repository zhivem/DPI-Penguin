import atexit
import ctypes
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, List

if os.name == 'nt':
    import win32api
    import win32con
    import win32event
    import winerror

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox

from gui.gui import DPIPenguin
from utils.utils import CURRENT_VERSION, tr
from utils.process_utils import InitializerThread

# Константы
MUTEX_NAME = "ru.github.dpipenguin.mutex"
PROCESSES_TO_TERMINATE = ["winws.exe", "goodbyedpi.exe"]
SERVICE_TO_STOP = "WinDivert"
LOG_FOLDER = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser("~\\AppData\\Local")), 'DPI-Penguin', 'logs')
LOG_FILENAME = os.path.join(LOG_FOLDER, f"app_penguin_v{CURRENT_VERSION}.log")

# Логгер
logger = logging.getLogger(__name__)

def setup_logging() -> None:
    """Настройка логирования приложения."""
    os.makedirs(LOG_FOLDER, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILENAME, maxBytes=1 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logging.basicConfig(handlers=[handler], level=logging.DEBUG, force=True)

def is_admin() -> bool:
    """Проверка прав администратора."""
    try:
        if os.name == 'nt':
            return ctypes.windll.shell32.IsUserAnAdmin()
        elif os.name == 'posix':
            return os.geteuid() == 0
        return False
    except Exception as e:
        logger.error(tr("Ошибка при проверке прав администратора: {error}").format(error=e))
        return False

def run_as_admin(argv: Optional[List[str]] = None) -> None:
    """Перезапуск приложения с правами администратора."""
    if os.name != 'nt':
        logger.error(tr("Функция run_as_admin доступна только на Windows."))
        sys.exit(1)

    shell32 = ctypes.windll.shell32
    executable = sys.executable
    params = ' '.join([f'"{arg}"' for arg in (argv or sys.argv)])
    ret = shell32.ShellExecuteW(None, "runas", executable, params, None, win32con.SW_NORMAL)

    if int(ret) <= 32:
        logger.error(tr("Не удалось перезапустить программу с правами администратора"))
        sys.exit(1)
    sys.exit(0)

def ensure_single_instance() -> bool:
    """Обеспечить, чтобы приложение работало только в одном экземпляре."""
    if os.name == 'nt':
        handle = win32event.CreateMutex(None, False, MUTEX_NAME)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            logger.info(tr("Обнаружен уже запущенный экземпляр приложения"))
            return False
        atexit.register(win32api.CloseHandle, handle)
    return True

def show_single_instance_warning() -> None:
    """Показать предупреждение о запущенном экземпляре приложения."""
    app = QtWidgets.QApplication(sys.argv)
    QMessageBox.warning(None, tr("Предупреждение"), tr("Приложение уже запущено"))
    sys.exit(0)

def main() -> None:
    """Основная функция приложения."""
    setup_logging()

    if not is_admin():
        logger.info(tr("Перезапуск программы с правами администратора"))
        run_as_admin()

    if not ensure_single_instance():
        logger.info(tr("Попытка запустить вторую копию приложения"))
        show_single_instance_warning()

    app = QtWidgets.QApplication(sys.argv)
    window = DPIPenguin()
    app.aboutToQuit.connect(window.stop_and_close)

    # Запуск InitializerThread после старта цикла событий
    initializer_thread = InitializerThread(PROCESSES_TO_TERMINATE, SERVICE_TO_STOP)
    initializer_thread.start()
    window.initializer_thread = initializer_thread

    app.exec()

    if hasattr(window, 'initializer_thread'):
        window.initializer_thread.quit()
        window.initializer_thread.wait()

if __name__ == '__main__':
    main()