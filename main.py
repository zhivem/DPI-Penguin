import atexit
import ctypes
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, List
from pathlib import Path

if os.name == 'nt':
    import win32api
    import win32con
    import win32event
    import winerror

from PyQt6.QtWidgets import QApplication, QMessageBox
from gui.gui import DPIPenguin
from utils.utils import CURRENT_VERSION, tr
from utils.process_utils import InitializerThread

# Константы
MUTEX_NAME = "ru.github.dpipenguin.mutex"
PROCESSES_TO_TERMINATE = frozenset(["winws.exe", "goodbyedpi.exe"])  
SERVICE_TO_STOP = "WinDivert"
LOG_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'DPI-Penguin' / 'logs'
LOG_FILE = LOG_DIR / f"app_penguin_v{CURRENT_VERSION}.log"

# Конфигурация логгера
logger = logging.getLogger(__name__)

def setup_logging() -> None:
    """Настройка логирования приложения."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_048_576, 
            backupCount=3,
            encoding='utf-8' 
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    except Exception as e:
       
        logging.basicConfig(level=logging.ERROR)
        logger.error(f"Failed to setup logging: {e}")

def is_admin() -> bool:
    """Проверка прав администратора."""
    try:
        if os.name == 'nt':
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        elif os.name == 'posix':
            return os.geteuid() == 0
        return False
    except Exception as e:
        logger.error(tr("Ошибка при проверке прав администратора: {error}").format(error=str(e)))
        return False

def run_as_admin(argv: Optional[List[str]] = None) -> None:
    """Перезапуск приложения с правами администратора."""
    if os.name != 'nt':
        logger.error(tr("Функция run_as_admin доступна только на Windows"))
        sys.exit(1)

    try:
        executable = sys.executable
        params = ' '.join(f'"{arg}"' for arg in (argv or sys.argv))
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, None, win32con.SW_NORMAL
        )
        
        if ret <= 32:
            logger.error(tr("Не удалось получить права администратора. Код ошибки: {code}").format(code=ret))
            sys.exit(1)
        sys.exit(0)
    except Exception as e:
        logger.error(tr("Ошибка при попытке повышения прав: {error}").format(error=str(e)))
        sys.exit(1)

def ensure_single_instance() -> Optional[int]:
    """Проверка единственного экземпляра приложения."""
    if os.name != 'nt':
        return None
        
    try:
        mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            logger.info(tr("Приложение уже запущено"))
            return None
        atexit.register(win32api.CloseHandle, mutex)
        return mutex
    except Exception as e:
        logger.error(tr("Ошибка проверки единственного экземпляра: {error}").format(error=str(e)))
        return None

def main() -> None:
    """Основная функция приложения."""
    setup_logging()
    logger.info(tr("Запуск приложения версии {version}").format(version=CURRENT_VERSION))

    if not is_admin():
        logger.info(tr("Требуются права администратора"))
        run_as_admin()

    mutex = ensure_single_instance()
    if mutex is None:
        QMessageBox.warning(None, tr("Предупреждение"), tr("Приложение уже запущено"))
        sys.exit(0)

    try:
        app = QApplication(sys.argv)
        window = DPIPenguin()
        app.aboutToQuit.connect(window.stop_and_close)

        initializer_thread = InitializerThread(PROCESSES_TO_TERMINATE, SERVICE_TO_STOP)
        initializer_thread.start()
        window.initializer_thread = initializer_thread

        sys.exit(app.exec())
    except Exception as e:
        logger.critical(tr("Критическая ошибка приложения: {error}").format(error=str(e)))
        sys.exit(1)
    finally:
        if hasattr(window, 'initializer_thread'):
            initializer_thread.quit()
            initializer_thread.wait()

if __name__ == '__main__':
    main()