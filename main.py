import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import webbrowser
import ctypes
import atexit

if os.name == 'nt':
    import win32event
    import win32api
    import win32con
    import winerror
    import win32process
    import win32service
    import win32serviceutil

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

PROCESSES_TO_TERMINATE = ["winws.exe", "goodbyedpi.exe"]

SERVICE_TO_STOP = "WinDivert"

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
    if os.name != 'nt':
        logging.error("Функция run_as_admin доступна только на Windows.")
        sys.exit(1)
        
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
            logging.info("Обнаружен уже запущенный экземпляр приложения.")
            return False
        atexit.register(win32api.CloseHandle, handle)
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

def terminate_processes(process_names):
    logging.info("Попытка завершить указанные процессы.")
    current_process_id = win32api.GetCurrentProcessId()
    try:
        process_ids = win32process.EnumProcesses()
        for pid in process_ids:
            if pid == current_process_id:
                continue
            try:
                h_process = win32api.OpenProcess(win32con.PROCESS_TERMINATE | win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
                exe_name = win32process.GetModuleFileNameEx(h_process, 0)
                exe_base_name = os.path.basename(exe_name).lower()
                for name in process_names:
                    if exe_base_name == name.lower():
                        win32api.TerminateProcess(h_process, 0)
                        logging.info(f"Процесс {exe_base_name} (PID: {pid}) успешно завершён.")
                win32api.CloseHandle(h_process)
            except Exception as e:
                logging.debug(f"Не удалось завершить PID {pid}: {e}")
    except Exception as e:
        logging.error(f"Ошибка при перечислении процессов: {e}")

def stop_service(service_name):
    logging.info(f"Попытка остановить службу {service_name}.")
    try:
        status = win32serviceutil.QueryServiceStatus(service_name)[1]
        if status == win32service.SERVICE_RUNNING:
            win32serviceutil.StopService(service_name)
            win32serviceutil.WaitForServiceStatus(service_name, win32service.SERVICE_STOPPED, 30)
            logging.info(f"Служба {service_name} успешно остановлена.")
        else:
            logging.info(f"Служба {service_name} не запущена.")
    except win32service.error as e:
        if e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
            logging.warning(f"Служба {service_name} не найдена.")
        else:
            logging.error(f"Не удалось остановить службу {service_name}: {e}")
    except Exception as e:
        logging.error(f"Неожиданная ошибка при остановке службы {service_name}: {e}")

def terminate_and_stop_services():
    if os.name == 'nt':
        terminate_processes(PROCESSES_TO_TERMINATE)
        stop_service(SERVICE_TO_STOP)

def main():
    setup_logging()

    app = QtWidgets.QApplication(sys.argv)

    if not is_admin():
        logging.info("Перезапуск программы с правами администратора.")
        run_as_admin()

    terminate_and_stop_services()

    if not ensure_single_instance():
        logging.info("Попытка запустить вторую копию приложения.")
        QMessageBox.warning(None, "Предупреждение", "Приложение уже запущено.")
        sys.exit(0)

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
    main()
