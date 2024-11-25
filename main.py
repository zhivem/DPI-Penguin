import atexit
import ctypes
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

if os.name == 'nt':
    import win32api
    import win32con
    import win32event
    import winerror

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QMessageBox

from gui.gui import GoodbyeDPIApp
from utils.utils import BASE_FOLDER, CURRENT_VERSION, tr
from utils.process_utils import InitializerThread

MUTEX_NAME = "ru.github.dpipenguin.mutex"
LOG_FILENAME = os.path.join(BASE_FOLDER, "logs", f"app_penguin_v{CURRENT_VERSION}.log")

PROCESSES_TO_TERMINATE = ["winws.exe", "goodbyedpi.exe"]
SERVICE_TO_STOP = "WinDivert"

logger = logging.getLogger(__name__)


def setup_logging():
    """Настройка логирования приложения."""
    os.makedirs(os.path.dirname(LOG_FILENAME), exist_ok=True)
    handler = RotatingFileHandler(LOG_FILENAME, maxBytes=1 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # Устанавливаем корневой уровень логирования и добавляем обработчик
    logging.basicConfig(handlers=[handler], level=logging.DEBUG, force=True)
    logger.info(tr("Логирование настроено"))


def is_admin() -> bool:
    """Проверка прав администратора."""
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            logger.error(tr("Ошибка при проверке прав администратора: {error}").format(error=e))
            return False
    elif os.name == 'posix':
        return os.geteuid() == 0
    return False


def run_as_admin(argv=None):
    """Перезапуск приложения с правами администратора."""
    if os.name != 'nt':
        logger.error(tr("Функция run_as_admin доступна только на Windows."))
        sys.exit(1)

    shell32 = ctypes.windll.shell32
    if argv is None:
        argv = sys.argv
    executable = sys.executable
    params = ' '.join([f'"{arg}"' for arg in argv])
    show_cmd = win32con.SW_NORMAL
    ret = shell32.ShellExecuteW(None, "runas", executable, params, None, show_cmd)

    if int(ret) <= 32:
        logger.error(tr("Не удалось перезапустить программу с правами администратора"))
        sys.exit(1)
    sys.exit(0)


def ensure_single_instance() -> bool:
    """Обеспечить, чтобы приложение работало только в одном экземпляре."""
    if os.name == 'nt':
        handle = win32event.CreateMutex(None, False, MUTEX_NAME)
        last_error = win32api.GetLastError()
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            logger.info(tr("Обнаружен уже запущенный экземпляр приложения"))
            return False
        atexit.register(win32api.CloseHandle, handle)
    return True


def show_single_instance_warning():
    """Показать предупреждение о запущенном экземпляре приложения."""
    app = QtWidgets.QApplication(sys.argv)
    QMessageBox.warning(None, tr("Предупреждение"), tr("Приложение уже запущено"))
    sys.exit(0)


def main():
    setup_logging()

    if not is_admin():
        logger.info(tr("Перезапуск программы с правами администратора"))
        run_as_admin()

    if not ensure_single_instance():
        logger.info(tr("Попытка запустить вторую копию приложения"))
        show_single_instance_warning()

    app = QtWidgets.QApplication(sys.argv)

    window = GoodbyeDPIApp()
    app.aboutToQuit.connect(window.stop_and_close)

    def start_initializer():
        """Функция для запуска InitializerThread после запуска цикла событий."""
        initializer_thread = InitializerThread(PROCESSES_TO_TERMINATE, SERVICE_TO_STOP)
        initializer_thread.start()

        window.initializer_thread = initializer_thread 

    QtCore.QTimer.singleShot(0, start_initializer)

    result = app.exec()

    if hasattr(window, 'initializer_thread'):
        window.initializer_thread.quit()
        window.initializer_thread.wait()


if __name__ == '__main__':
    main()
