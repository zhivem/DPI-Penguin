import logging
import os
import sys
import win32api
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from gui.gui import DPIPenguin
from utils.utils import CURRENT_VERSION, tr
from utils.process_utils import InitializerThread

# Константы
MUTEX_NAME = "ru.github.dpipenguin.mutex"
PROCESSES_TO_TERMINATE = frozenset(["winws.exe", "goodbyedpi.exe"])
SERVICE_TO_STOP = "WinDivert"
LOG_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'DPI-Penguin' / 'logs'
LOG_FILE = LOG_DIR / f"app_penguin_v{CURRENT_VERSION}.log"

def setup_logging() -> logging.Logger:
    """Настройка логирования приложения."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("dpipenguin")
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_048_576, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Логирование успешно настроено")
    return logger

class SingleInstance:
    """Контекстный менеджер для проверки единственного экземпляра приложения (только Windows)."""
    def __init__(self, mutex_name: str):
        self.mutex_name = mutex_name
        self.mutex = None

    def __enter__(self):
        if os.name != 'nt':
            return None
        try:
            import win32event, winerror
            self.mutex = win32event.CreateMutex(None, False, self.mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                return None
            return self.mutex
        except Exception as e:
            return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mutex:
            import win32api
            win32api.CloseHandle(self.mutex)

def main() -> None:
    logger = setup_logging()
    logger.info(tr("Запуск приложения версии {version}").format(version=CURRENT_VERSION))

    with SingleInstance(MUTEX_NAME) as mutex:
        if os.name == 'nt' and mutex is None:
            app = QApplication(sys.argv)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, tr("Предупреждение"), tr("Приложение уже запущено"))
            sys.exit(0)

        app = QApplication(sys.argv)
        window = None
        try:
            window = DPIPenguin()
            app.aboutToQuit.connect(window.stop_and_close)

            initializer_thread = InitializerThread(PROCESSES_TO_TERMINATE, SERVICE_TO_STOP)
            initializer_thread.start()
            window.initializer_thread = initializer_thread

            sys.exit(app.exec())
        except Exception as e:
            logger.exception(tr("Критическая ошибка приложения: {error}").format(error=str(e)))
            sys.exit(1)
        finally:
            if window and hasattr(window, 'initializer_thread'):
                window.initializer_thread.quit()
                window.initializer_thread.wait()

if __name__ == '__main__':
    main()