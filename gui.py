import os
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QIcon, QTextCursor, QDesktopServices
from qfluentwidgets import PushButton, ComboBox, TextEdit, Theme, setTheme
from process_worker import WorkerThread
from update_checker import UpdateCheckerThread
from blacklist_updater import update_blacklist
from utils import BASE_FOLDER, BLACKLIST_FILES, GOODBYE_DPI_EXE, WIN_DIVERT_COMMAND, GOODBYE_DPI_PROCESS_NAME
import psutil

class GoodbyeDPIApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.check_for_updates()

    def init_ui(self):
        self.setWindowTitle("GoodByeDPI GUI by [Ярослав Zhivem]")
        self.setFixedSize(420, 450)
        self.setWindowIcon(QIcon(os.path.join(BASE_FOLDER, 'fackrkn.ico')))
        setTheme(Theme.LIGHT)

        layout = QtWidgets.QVBoxLayout(self)

        self.script_options = {
            "YouTube (Актуальный метод)": [
                "-9", "--blacklist", BLACKLIST_FILES[0], "--blacklist", BLACKLIST_FILES[1]
            ],
            "Ростелеком (Тестовая версия)": [
                "-5", "-e1", "--blacklist", BLACKLIST_FILES[0], "--blacklist", BLACKLIST_FILES[1]
            ]
        }

        self.selected_script = ComboBox()
        self.selected_script.addItems(self.script_options.keys())
        layout.addWidget(self.selected_script)

        self.run_button = PushButton("Запустить")
        self.run_button.clicked.connect(self.run_exe)  # Подключаем к кнопке метод run_exe
        layout.addWidget(self.run_button)

        self.stop_close_button = PushButton("Остановить WinDivert и закрыть GoodbyeDPI")
        self.stop_close_button.setEnabled(False)
        self.stop_close_button.clicked.connect(self.stop_and_close)
        layout.addWidget(self.stop_close_button)

        self.update_blacklist_button = PushButton("Обновить черный список")
        self.update_blacklist_button.clicked.connect(self.update_blacklist)
        layout.addWidget(self.update_blacklist_button)

        self.update_button = PushButton("Проверить обновления")
        self.update_button.clicked.connect(self.check_for_updates)
        layout.addWidget(self.update_button)

        self.console_output = TextEdit()
        self.console_output.setReadOnly(True)
        layout.addWidget(self.console_output)

    # Метод, запускающий процесс GoodbyeDPI
    def run_exe(self):
        command = [GOODBYE_DPI_EXE] + self.script_options[self.selected_script.currentText()]
        self.start_process(command, "GoodbyeDPI", disable_run=True, clear_console_text="Процесс GoodbyeDPI запущен...")

    # Метод для запуска потока с процессом
    def start_process(self, command, process_name, disable_run=False, clear_console_text=None):
        if clear_console_text:
            self.clear_console(clear_console_text)

        self.worker_thread = WorkerThread(command, process_name, encoding="cp866")
        self.worker_thread.output_signal.connect(self.update_output)
        self.worker_thread.finished_signal.connect(self.on_finished)
        self.worker_thread.start()

        if disable_run:
            self.run_button.setEnabled(False)
            self.stop_close_button.setEnabled(True)

    # Метод для обновления вывода консоли
    def update_output(self, text):
        self.console_output.append(text)
        max_lines = 100
        document = self.console_output.document()
        while document.blockCount() > max_lines:
            cursor = self.console_output.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    # Метод для завершения работы с процессом
    def on_finished(self, process_name):
        if process_name == "GoodbyeDPI":
            self.run_button.setEnabled(True)
            self.stop_close_button.setEnabled(False)
            self.console_output.append(f"Процесс {process_name} завершен.")
    
    # Метод для остановки WinDivert и завершения GoodbyeDPI
    def stop_and_close(self):
        self.start_process(WIN_DIVERT_COMMAND, "WinDivert")
        self.close_goodbyedpi()

    # Метод для завершения процесса GoodbyeDPI
    def close_goodbyedpi(self):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == GOODBYE_DPI_PROCESS_NAME:
                    psutil.Process(proc.info['pid']).terminate()
                    return
            self.console_output.append("Процесс GoodbyeDPI не найден.")
        except psutil.Error as e:
            self.console_output.append(f"Ошибка завершения процесса: {str(e)}")

    # Метод для обновления черного списка
    def update_blacklist(self):
        self.clear_console("Обновление черного списка...")
        success = update_blacklist()
        if success:
            self.console_output.append("Обновление черного списка успешно завершено.")
        else:
            self.console_output.append("Не удалось обновить черный список. Проверьте соединение с интернетом.")

    # Метод для очистки консоли
    def clear_console(self, initial_text=""):
        self.console_output.clear()
        if initial_text:
            self.console_output.append(initial_text)

    # Метод для проверки обновлений
    def check_for_updates(self):
        self.update_thread = UpdateCheckerThread()
        self.update_thread.update_available.connect(self.notify_update)
        self.update_thread.no_update.connect(self.no_update)
        self.update_thread.update_error.connect(self.update_error)
        self.update_thread.start()

    # Уведомление об отсутствии обновлений
    def no_update(self):
        self.console_output.append("Обновлений нет. Вы используете последнюю версию.")

    # Обработка ошибок при проверке обновлений
    def update_error(self, error_message):
        self.console_output.append(error_message)

    # Уведомление о доступности обновлений
    def notify_update(self, latest_version):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Доступно обновление",
            f"Доступна новая версия {latest_version}. Хотите перейти на страницу загрузки?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            QDesktopServices.openUrl(QtCore.QUrl('https://github.com/zhivem/GUI/releases'))

