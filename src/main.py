import sys
import logging
from PyQt5 import QtWidgets
from gui import GoodbyeDPIApp
from utils import ensure_module_installed

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    ensure_module_installed('packaging')

    try:
        app = QtWidgets.QApplication(sys.argv)
        ex = GoodbyeDPIApp()
        ex.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {e}")
