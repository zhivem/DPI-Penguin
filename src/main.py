import sys
from PyQt5 import QtWidgets
from gui import GoodbyeDPIApp
from utils import ensure_module_installed

# Точка входа в программу.
# Здесь начинается выполнение программы при запуске файла.

if __name__ == '__main__':
    # Проверка и установка модуля 'packaging' при необходимости.
    ensure_module_installed('packaging')
    
    # Инициализация приложения Qt.
    app = QtWidgets.QApplication(sys.argv)
    
    # Создание экземпляра основного GUI приложения.
    ex = GoodbyeDPIApp()
    
    # Отображение главного окна.
    ex.show()
    
    # Корректное завершение работы приложения при закрытии.
    sys.exit(app.exec_())
