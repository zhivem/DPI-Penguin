import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import webbrowser
import ctypes

# Константы
UPDATE_URL = "https://github.com/zhivem/DPI-Penguin"

# Импорт утилит, необходимых для логирования
from utils import BASE_FOLDER, ensure_module_installed, current_version

# Конфигурация логирования с ротацией файлов и перезаписью при запуске
import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Указание директории для логов
    log_dir = os.path.join(BASE_FOLDER, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Создание файла логов с текущей версией
    log_file = os.path.join(log_dir, f"app_penguin_v{current_version}.log")

    # Настройка ротации файлов
    handler = RotatingFileHandler(
        log_file,
        mode='w',  
        maxBytes=5 * 1024 * 1024,  
        backupCount=3  
    )

    # Формат логирования
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Настройка логирования с заданными параметрами
    logging.basicConfig(
        handlers=[handler],
        level=logging.DEBUG,  # Уровень логирования DEBUG для подробного вывода
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True  # Принудительное изменение существующих настроек логирования
    )

    logging.info("Логирование настроено.")

# Настройка логирования перед импортом других модулей
setup_logging()

# Импорт после настройки логирования
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

from gui import GoodbyeDPIApp
from updater import Updater

def is_admin() -> bool:
    """
    Проверяет, запущено ли приложение с правами администратора.

    Returns:
        bool: True, если запущено с правами администратора, иначе False.
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

class MyApp(QtWidgets.QApplication):
    """
    Класс приложения, наследующий от QtWidgets.QApplication.
    Обрабатывает глобальные исключения и инициализирует главное окно.
    """
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("MyApp инициализирован.")
        self.ex = GoodbyeDPIApp()

    def notify(self, receiver, event):
        """
        Переопределяет метод notify для глобальной обработки исключений.

        Args:
            receiver: Объект-получатель события.
            event: Событие.

        Returns:
            bool: Результат обработки события.
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
    updater.update_error.connect(lambda error_message: logging.error(f"Ошибка проверки обновлений: {error_message}"))
    updater.start()

def prompt_update(latest_version: str):
    """
    Запрашивает у пользователя обновление приложения.

    Args:
        latest_version (str): Последняя доступная версия.
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

    # Убедиться, что необходимый модуль установлен
    ensure_module_installed('packaging')

    # Инициализация приложения
    app = MyApp(sys.argv)

    # Проверка прав администратора
    if not is_admin():
        logging.error("Программа должна быть запущена с правами администратора.")
        QMessageBox.critical(None, "Ошибка", "Программа должна быть запущена с правами администратора.")
        sys.exit(1)

    # Инициализация и проверка обновлений
    updater = Updater()
    check_for_updates_on_startup(updater)

    try:
        app.ex.show()
        logging.info("Приложение запущено.")
        result = app.exec_()
    except Exception as e:
        logging.critical(f"Неожиданная ошибка: {e}", exc_info=True)
        QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {e}")
    finally:
        updater.wait()
        logging.info("Приложение завершило работу.")
        sys.exit(result)

if __name__ == '__main__':
    main()
