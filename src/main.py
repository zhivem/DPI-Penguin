import ctypes
import logging
import os
import sys
import webbrowser

from PyQt5 import QtWidgets

from gui import GoodbyeDPIApp  
from updater import Updater  
from utils import ensure_module_installed 


LOG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "app_zhivem_v1.5.2.log")
logging.basicConfig(
    filename=LOG_FILE,
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelность)s - %(message)s'
)

def is_admin():
    """Проверяет, запущено ли приложение с правами администратора."""
    if os.name == 'nt':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            logging.error(f"Ошибка при проверке прав администратора: {e}")
            return False
        
class MyApp(QtWidgets.QApplication):
    """Класс приложения с обработкой исключений."""
    
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.ex = GoodbyeDPIApp()  # Инициализация основного окна приложения

    def notify(self, receiver, event):
        """Переопределение метода для глобальной обработки исключений."""
        try:
            return super().notify(receiver, event)
        except Exception as e:
            logging.error(f"Ошибка: {e}")
            QtWidgets.QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {e}")
            return False

def check_for_updates_on_startup(updater):
    """Проверяет наличие обновлений при запуске приложения."""
    updater.update_available.connect(prompt_update)
    updater.no_update.connect(lambda: logging.info("Обновления не найдены."))
    updater.update_error.connect(lambda error_message: logging.error(f"Ошибка проверки обновлений: {error_message}"))
    updater.start()

def prompt_update(latest_version):
    """Предлагает пользователю перейти на страницу загрузки новой версии."""
    reply = QtWidgets.QMessageBox.question(
        None,
        "Обновление",
        f"Доступна новая версия {latest_version}. Хотите перейти на страницу загрузки?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.No
    )
    if reply == QtWidgets.QMessageBox.Yes:
        webbrowser.open("https://github.com/zhivem/GoodByDPI-GUI-by-Zhivem")

def main():
    """Главная функция запуска приложения."""
    ensure_module_installed('packaging')  # Убедиться, что модуль 'packaging' установлен
    app = MyApp(sys.argv)  # Инициализация приложения

    if not is_admin():
        logging.error("Программа должна быть запущена с правами администратора.")
        QtWidgets.QMessageBox.critical(None, "Ошибка", "Программа должна быть запущена с правами администратора.")
        sys.exit(1)

    updater = Updater()  # Инициализация объекта для проверки обновлений
    check_for_updates_on_startup(updater)  # Проверка обновлений при запуске

    result = 0
    try:
        app.ex.show()  # Показ основного окна приложения
        result = app.exec_()  # Запуск цикла обработки событий
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}")
        QtWidgets.QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {e}")
    finally:
        updater.wait()  # Дождаться завершения потоков, связанных с обновлениями
        sys.exit(result)

if __name__ == '__main__':
    main()
