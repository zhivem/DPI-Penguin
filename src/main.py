import sys
from PyQt5 import QtWidgets
from gui import GoodbyeDPIApp
from utils import ensure_module_installed

if __name__ == '__main__':
    ensure_module_installed('packaging')
    app = QtWidgets.QApplication(sys.argv)
    ex = GoodbyeDPIApp()
    ex.show()
    sys.exit(app.exec_())
