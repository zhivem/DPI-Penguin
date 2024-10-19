import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import webbrowser
import ctypes
import atexit
import winerror

# Импорт стандартных библиотек для Windows
if os.name == 'nt':
    import win32event
    import win32api
    import win32con

# Импорт сторонних библиотек
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

# Импорт локальных модулей
from gui.gui import GoodbyeDPIApp
from utils.updater import Updater
from utils.utils import (
    BASE_FOLDER,
    CURRENT_VERSION,
    ensure_module_installed,
)

# Константы
UPDATE_URL = "https://github.com/zhivem/DPI-Penguin/releases"
MUTEX_NAME = "ru.github.dpipenguin.mutex"
LOG_FILENAME = os.path.join(BASE_FOLDER, "logs", f"app_penguin_v{CURRENT_VERSION}.log")

def setup_logging():
    """
    Настройка логирования с использованием RotatingFileHandler.
    """
    os.makedirs(os.path.dirname(LOG_FILENAME), exist_ok=True)
    
    handler = RotatingFileHandler(
        LOG_FILENAME,
        maxBytes=1 * 1024 * 1024,  # 1 MB
        backupCount=3  # Количество резервных копий логов
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
    """
    Проверяет, запущено ли приложение с правами администратора.
    
    Returns:
        bool: True, если приложение запущено как администратор, иначе False.
    """
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
    """
    Перезапускает программу с правами администратора.
    
    Args:
        argv (list, optional): Аргументы командной строки. По умолчанию None.
    """
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
    """
    Обеспечивает однократный запуск приложения.
    """
    if os.name == 'nt':
        handle = win32event.CreateMutex(None, False, MUTEX_NAME)
        last_error = win32api.GetLastError()
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            logging.info("Приложение уже запущено. Завершение новой копии.")
            QMessageBox.warning(None, "Предупреждение", "Приложение уже запущено.")
            sys.exit(0)
        # Релиз мьютекса при выходе
        atexit.register(win32api.CloseHandle, handle)
    else:
        # Для POSIX систем можно использовать файлы блокировки или другие механизмы
        pass

class MyApp(QtWidgets.QApplication):
    """
    Класс приложения, наследующий от QtWidgets.QApplication.
    Обрабатывает глобальные исключения и инициализирует главное окно.
    """
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Главное окно инициализировано.")
        self.ex = GoodbyeDPIApp()

    def notify(self, receiver, event):
        """
        Переопределяет метод notify для глобальной обработки исключений.
        """
        try:
            return super().notify(receiver, event)
        except Exception as e:
            logging.error(f"Глобальная ошибка: {e}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {e}")
            return False

def check_for_updates_on_startup(updater: Updater):
    """
    Проверяет наличие обновлений при запуске приложения.
    
    Args:
        updater (Updater): Экземпляр класса Updater.
    """
    updater.update_available.connect(prompt_update)
    updater.no_update.connect(lambda: logging.info("Обновления не найдены."))
    updater.update_error.connect(lambda msg: logging.error(f"Ошибка проверки обновлений: {msg}"))
    updater.start()

def prompt_update(latest_version: str):
    """
    Запрашивает у пользователя обновление приложения.
    
    Args:
        latest_version (str): Доступная последняя версия.
    """
    reply = QMessageBox.question(
        None,
        "Обновление",
        f"Доступна новая версия {latest_version}. Хотите перейти на страницу загрузки?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    if reply == QMessageBox.Yes:
        webbrowser.open(UPDATE_URL)

def main():
    """
    Основная функция запуска приложения.
    """
    logging.debug("Начало выполнения main()")
    
    # Обеспечить однократный запуск
    ensure_single_instance()
    
    # Проверка прав администратора
    if not is_admin():
        logging.info("Перезапуск программы с правами администратора.")
        run_as_admin()
    
    # Убедимся, что необходимый модуль установлен
    ensure_module_installed('packaging')
    
    # Инициализация приложения
    app = MyApp(sys.argv)
    
    # Инициализация и проверка обновлений
    updater = Updater()
    check_for_updates_on_startup(updater)
    
    try:
        app.ex.show()
        result = app.exec_()
    except Exception as e:
        logging.critical(f"Неожиданная ошибка: {e}", exc_info=True)
        QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {e}")
    finally:
        updater.wait()
        sys.exit(result)

if __name__ == '__main__':
    setup_logging()
    main()
