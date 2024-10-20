import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import webbrowser
import ctypes
import atexit
import winerror

if os.name == 'nt':
    import win32event
    import win32api
    import win32con

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox

from gui.gui import GoodbyeDPIApp
from utils.updater import Updater
from utils.utils import (
    BASE_FOLDER,
    CURRENT_VERSION,
    ensure_module_installed,
)

UPDATE_URL = "https://github.com/zhivem/DPI-Penguin/releases"
MUTEX_NAME = "ru.github.dpipenguin.mutex"
LOG_FILENAME = os.path.join(BASE_FOLDER, "logs", f"app_penguin_v{CURRENT_VERSION}.log")

def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILENAME), exist_ok=True)
    
    handler = RotatingFileHandler(
        LOG_FILENAME,
        maxBytes=1 * 1024 * 1024,
        backupCount=3
    )
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logging.basicConfig(
        handlers=[handler],
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )

    logging.info("Логирование настроено.")

def is_admin() -> bool:
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            logging.error(f"Ошибка при проверке прав администратора: {e}")
            return False
    elif os.name == 'posix':
        return os.geteuid() == 0
    return False

def run_as_admin(argv=None):
    shell32 = ctypes.windll.shell32
    if argv is None:
        argv = sys.argv
    executable = sys.executable
    params = ' '.join([f'"{arg}"' for arg in argv])
    show_cmd = win32con.SW_NORMAL
    ret = shell32.ShellExecuteW(None, "runas", executable, params, None, show_cmd)
    if int(ret) <= 32:
        logging.error("Не удалось перезапустить программу с правами администратора.")
        sys.exit(1)
    sys.exit(0)

def ensure_single_instance():
    if os.name == 'nt':
        handle = win32event.CreateMutex(None, False, MUTEX_NAME)
        last_error = win32api.GetLastError()
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            logging.info("Приложение уже запущено. Завершение новой копии.")
            return False
        atexit.register(win32api.CloseHandle, handle)
    else:
        pass
    return True

def check_for_updates_on_startup(updater: Updater):
    updater.update_available.connect(prompt_update)
    updater.no_update.connect(lambda: logging.info("Обновления не найдены."))
    updater.update_error.connect(lambda msg: logging.error(f"Ошибка проверки обновлений: {msg}"))
    updater.start()

def prompt_update(latest_version: str):
    reply = QMessageBox.question(
        None,
        "Обновление",
        f"Доступна новая версия {latest_version}. Хотите перейти на страницу загрузки?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    if reply == QMessageBox.StandardButton.Yes:
        webbrowser.open(UPDATE_URL)

def main():
    logging.debug("Начало выполнения main()")
    
    app = QtWidgets.QApplication(sys.argv)
    
    if not ensure_single_instance():
        QMessageBox.warning(None, "Предупреждение", "Приложение уже запущено.")
        sys.exit(0)
    
    if not is_admin():
        logging.info("Перезапуск программы с правами администратора.")
        run_as_admin()
    
    ensure_module_installed('packaging')
    
    updater = Updater()
    check_for_updates_on_startup(updater)
    
    window = GoodbyeDPIApp()
    window.show()
    
    try:
        result = app.exec()
    except Exception as e:
        logging.critical(f"Неожиданная ошибка: {e}", exc_info=True)
        QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {e}")
        result = 1 
    finally:
        updater.wait()
        sys.exit(result)

if __name__ == '__main__':
    setup_logging()
    main()
