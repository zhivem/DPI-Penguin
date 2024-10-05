import sys
import logging
import ctypes
from PyQt5 import QtWidgets
from gui import GoodbyeDPIApp
from utils import ensure_module_installed

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Инициализация QApplication перед проверкой
    app = QtWidgets.QApplication(sys.argv)

    # Проверка прав администратора
    if not is_admin():
        logging.error("Программа должна быть запущена с правами администратора.")
        QtWidgets.QMessageBox.critical(None, "Ошибка", "Программа должна быть запущена с правами администратора.")
        sys.exit(1)

    ensure_module_installed('packaging')

    try:
        ex = GoodbyeDPIApp()
        ex.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {e}")
