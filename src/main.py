import ctypes
import logging
import os
import sys
import webbrowser

from PyQt5 import QtWidgets

from gui import GoodbyeDPIApp
from updater import Updater
from utils import BASE_FOLDER, ensure_module_installed

LOG_FILE = os.path.join(BASE_FOLDER, "app_zhivem_v1.5.1.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def is_admin():
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
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.ex = GoodbyeDPIApp()

    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception as e:
            logging.error(f"Ошибка: {e}")
            QtWidgets.QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {e}")
            return False


def check_for_updates_on_startup(updater):
    updater.update_available.connect(prompt_update)
    updater.no_update.connect(lambda: logging.info("Обновления не найдены."))
    updater.update_error.connect(lambda error_message: logging.error(f"Ошибка проверки обновлений: {error_message}"))
    updater.start()


def prompt_update(latest_version):
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
    ensure_module_installed('packaging')
    app = MyApp(sys.argv)
    if not is_admin():
        logging.error("Программа должна быть запущена с правами администратора.")
        QtWidgets.QMessageBox.critical(None, "Ошибка", "Программа должна быть запущена с правами администратора.")
        sys.exit(1)

    updater = Updater()
    check_for_updates_on_startup(updater)
    try:
        app.ex.show()
        result = app.exec_()
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}")
        QtWidgets.QMessageBox.critical(None, "Ошибка", f"Произошла ошибка: {e}")
    finally:
        updater.wait()
        sys.exit(result)


if __name__ == '__main__':
    main()
