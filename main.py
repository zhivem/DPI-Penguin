import atexit
import ctypes
import logging
import os
import sys
import time
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

# Инициализация логгера
logger = logging.getLogger()

def setup_logging() -> None:
    """Настройка логирования приложения."""
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.DEBUG)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_048_576,
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.info("Логирование успешно настроено")
    except Exception as e:
        logger.error(f"Не удалось настроить логирование: {e}")
        raise

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

def run_as_admin(argv: Optional[List[str]] = None, mutex: Optional[int] = None) -> None:
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
        else:
            logger.info(tr("Приложение перезапускается с правами администратора"))
            if mutex:
                win32api.CloseHandle(mutex) 
            time.sleep(1)
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
            return None
        return mutex
    except Exception as e:
        logger.error(tr("Ошибка проверки единственного экземпляра: {error}").format(error=str(e)))
        return None

def main() -> None:
    """Основная функция приложения."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(tr("Запуск приложения версии {version}").format(version=CURRENT_VERSION))
    
    # Проверка единственного экземпляра
    mutex = ensure_single_instance()
    if mutex is None:
        app = QApplication(sys.argv) 
        QMessageBox.warning(None, tr("Предупреждение"), tr("Приложение уже запущено"))
        sys.exit(0)

    # Проверка прав администратора
    if not is_admin():
        logger.info(tr("Требуются права администратора"))
        run_as_admin(mutex=mutex)  

    app = QApplication(sys.argv)
    
    window = None 
    initializer_thread = None
    try:
        window = DPIPenguin()
        app.aboutToQuit.connect(window.stop_and_close)

        initializer_thread = InitializerThread(PROCESSES_TO_TERMINATE, SERVICE_TO_STOP)
        initializer_thread.start()
        window.initializer_thread = initializer_thread

        logger.info(tr("Главное окно приложения инициализировано"))
        sys.exit(app.exec())
    except Exception as e:
        logger.exception(tr("Критическая ошибка приложения: {error}").format(error=str(e)))
        sys.exit(1)
    finally:
        if window and hasattr(window, 'initializer_thread'):
            window.initializer_thread.quit()
            window.initializer_thread.wait()
        if mutex:
            win32api.CloseHandle(mutex)

if __name__ == '__main__':
    main()