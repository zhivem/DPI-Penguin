from PyQt5 import QtCore
from utils import get_latest_version, is_newer_version, current_version  # Импортируем текущую версию

# Класс потока для проверки обновлений.
# Наследуется от QThread для выполнения в фоновом режиме.
class UpdateCheckerThread(QtCore.QThread):
    # Сигнал, который передает информацию о доступном обновлении.
    update_available = QtCore.pyqtSignal(str)
    # Сигнал, если обновление не требуется.
    no_update = QtCore.pyqtSignal()
    # Сигнал для обработки ошибок при проверке обновлений.
    update_error = QtCore.pyqtSignal(str)

    # Метод, выполняемый при запуске потока.
    def run(self):
        # Получаем последнюю доступную версию из источника.
        latest_version = get_latest_version()
        
        if latest_version:
            # Проверяем, новее ли последняя версия, чем текущая.
            if is_newer_version(latest_version, current_version):  # Сравнение с текущей версией
                # Если обновление доступно, отправляем сигнал с новой версией.
                self.update_available.emit(latest_version)
            else:
                # Если обновление не требуется, отправляем соответствующий сигнал.
                self.no_update.emit()
        else:
            # В случае ошибки при получении версии, отправляем сигнал с ошибкой.
            self.update_error.emit("Не удалось получить последнюю версию. Проверьте подключение к интернету.")
