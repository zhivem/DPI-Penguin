import atexit
import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

if os.name == 'nt':
    import win32api
    import win32con
    import win32event
    import win32process
    import win32service
    import win32serviceutil
    import winerror

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox

from gui.gui import GoodbyeDPIApp
from utils.utils import BASE_FOLDER, CURRENT_VERSION, ensure_module_installed, tr

MUTEX_NAME = "ru.github.dpipenguin.mutex"
LOG_FILENAME = os.path.join(BASE_FOLDER, "logs", f"app_penguin_v{CURRENT_VERSION}.log")

PROCESSES_TO_TERMINATE = ["winws.exe", "goodbyedpi.exe"]
SERVICE_TO_STOP = "WinDivert"

def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILENAME), exist_ok=True)
    handler = RotatingFileHandler(LOG_FILENAME, maxBytes=1 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logging.basicConfig(handlers=[handler], level=logging.DEBUG, force=True)
    logging.info(tr("Логирование настроено"))

def is_admin() -> bool:
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            logging.error(tr("Ошибка при проверке прав администратора: {e}").format(e=e))
            return False
    elif os.name == 'posix':
        return os.geteuid() == 0
    return False

def run_as_admin(argv=None):
    if os.name != 'nt':
        logging.error(tr("Функция run_as_admin доступна только на Windows."))
        sys.exit(1)

    shell32 = ctypes.windll.shell32
    if argv is None:
        argv = sys.argv
    executable = sys.executable
    params = ' '.join([f'"{arg}"' for arg in argv])
    show_cmd = win32con.SW_NORMAL
    ret = shell32.ShellExecuteW(None, "runas", executable, params, None, show_cmd)
    if int(ret) <= 32:
        logging.error(tr("Не удалось перезапустить программу с правами администратора"))
        sys.exit(1)
    sys.exit(0)

def ensure_single_instance():
    if os.name == 'nt':
        handle = win32event.CreateMutex(None, False, MUTEX_NAME)
        last_error = win32api.GetLastError()
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            logging.info(tr("Обнаружен уже запущенный экземпляр приложения"))
            return False
        atexit.register(win32api.CloseHandle, handle)
    return True

def terminate_processes(process_names):
    logging.info(tr("Попытка завершить указанные процессы"))
    current_process_id = win32api.GetCurrentProcessId()
    try:
        process_ids = win32process.EnumProcesses()
        for pid in process_ids:
            if pid == current_process_id:
                continue
            try:
                h_process = win32api.OpenProcess(
                    win32con.PROCESS_TERMINATE | win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                    False, pid
                )
                exe_name = win32process.GetModuleFileNameEx(h_process, 0)
                exe_base_name = os.path.basename(exe_name).lower()
                for name in process_names:
                    if exe_base_name == name.lower():
                        win32api.TerminateProcess(h_process, 0)
                        logging.info(tr("Процесс {exe_base_name} (PID: {pid}) успешно завершён").format(
                            exe_base_name=exe_base_name, pid=pid
                        ))
                win32api.CloseHandle(h_process)
            except Exception as e:
                logging.debug(tr("Не удалось завершить PID {pid}: {e}").format(pid=pid, e=e))
    except Exception as e:
        logging.error(tr("Ошибка при перечислении процессов: {e}").format(e=e))

def stop_service(service_name):
    logging.info(tr("Попытка остановить службу {service_name}.").format(service_name=service_name))
    try:
        status = win32serviceutil.QueryServiceStatus(service_name)[1]
        if status == win32service.SERVICE_RUNNING:
            win32serviceutil.StopService(service_name)
            win32serviceutil.WaitForServiceStatus(service_name, win32service.SERVICE_STOPPED, 30)
            logging.info(tr("Служба {service_name} успешно остановлена.").format(service_name=service_name))
        else:
            logging.info(tr("Служба {service_name} не запущена").format(service_name=service_name))
    except win32service.error as e:
        if e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
            logging.warning(tr("Служба {service_name} не найдена").format(service_name=service_name))
        else:
            logging.error(tr("Не удалось остановить службу {service_name}: {e}").format(service_name=service_name, e=e))
    except Exception as e:
        logging.error(tr("Неожиданная ошибка при остановке службы {service_name}: {e}").format(service_name=service_name, e=e))

def terminate_and_stop_services():
    if os.name == 'nt':
        terminate_processes(PROCESSES_TO_TERMINATE)
        stop_service(SERVICE_TO_STOP)

def main():
    setup_logging()
    app = QtWidgets.QApplication(sys.argv)

    if not is_admin():
        logging.info(tr("Перезапуск программы с правами администратора"))
        run_as_admin()

    terminate_and_stop_services()

    if not ensure_single_instance():
        logging.info(tr("Попытка запустить вторую копию приложения"))
        QMessageBox.warning(None, tr("Предупреждение"), tr("Приложение уже запущено"))
        sys.exit(0)

    ensure_module_installed('packaging')

    window = GoodbyeDPIApp()
    app.aboutToQuit.connect(window.stop_and_close)
    result = app.exec()

if __name__ == '__main__':
    main()
