from PyQt5 import QtCore
from utils import get_latest_version, is_newer_version, current_version

class UpdateCheckerThread(QtCore.QThread):
    update_available = QtCore.pyqtSignal(str)
    no_update = QtCore.pyqtSignal()
    update_error = QtCore.pyqtSignal(str)

    def run(self):
        latest_version = get_latest_version()
        
        if latest_version:
            if is_newer_version(latest_version, current_version):
                self.update_available.emit(latest_version)
            else:
                self.no_update.emit()
        else:
            self.update_error.emit("Не удалось получить последнюю версию.")
