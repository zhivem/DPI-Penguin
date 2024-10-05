from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QIcon, QTextCursor
from qfluentwidgets import PushButton, ComboBox, TextEdit, Theme, setTheme
import os
import psutil
from updater import Updater
import subprocess
import platform
from process_worker import WorkerThread
from utils import BASE_FOLDER, BLACKLIST_FILES, GOODBYE_DPI_EXE, WIN_DIVERT_COMMAND, GOODBYE_DPI_PROCESS_NAME


class GoodbyeDPIApp(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.updater = Updater()

    def init_ui(self):
        self.setWindowTitle("GoodByeDPI GUI by Zhivem v1.2")
        self.setFixedSize(420, 350)
        self.setWindowIcon(QIcon(os.path.join(BASE_FOLDER, "icon", 'fackrkn.ico')))
        setTheme(Theme.LIGHT)

        layout = QtWidgets.QVBoxLayout(self)
        tab_widget = self.create_tabs()
        layout.addWidget(tab_widget)

    def create_tabs(self):
        tab_widget = QtWidgets.QTabWidget(self)

        # Вкладка процессов
        process_tab = QtWidgets.QWidget()
        process_layout = QtWidgets.QVBoxLayout(process_tab)
        tab_widget.addTab(process_tab, "GoodbyeDPI")

        self.script_options = {
            "Обход блокировок YouTube (Актуальный метод)": ["-9", "--blacklist", BLACKLIST_FILES[1]],
            "Обход блокировок для всех сайтов": ["-9", "--blacklist", BLACKLIST_FILES[0], "--blacklist", BLACKLIST_FILES[1]]
        }

        self.selected_script = ComboBox()
        self.selected_script.addItems(self.script_options.keys())
        process_layout.addWidget(self.selected_script)

        self.run_button = self.create_button("Запустить", self.run_exe, process_layout)
        self.stop_close_button = self.create_button("Остановить и закрыть", self.stop_and_close, process_layout, enabled=False)

        self.console_output = TextEdit(self)
        self.console_output.setReadOnly(True)
        process_layout.addWidget(self.console_output)

        # Вкладка настроек
        settings_tab = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_tab)
        tab_widget.addTab(settings_tab, "Настройки")

        self.create_label("Службы", settings_layout)
        self.create_button("Создать службу", self.create_service, settings_layout)
        self.create_button("Удалить службу", self.delete_service, settings_layout)

        settings_layout.addStretch(1)

        self.create_label("Обновления", settings_layout)
        self.create_button("Обновить черный список", self.update_blacklist, settings_layout)
        self.update_button = self.create_button("Проверить обновления", self.check_for_updates, settings_layout)

        settings_layout.addStretch(1)
        self.create_label("GoodbyeDPI GUI by Zhivem v1.2", settings_layout, centered=True)
        self.create_label('<a href="https://github.com/zhivem/GoodByDPI-GUI-by-Zhivem">Проект на GitHub</a>', settings_layout, centered=True, link=True)

        return tab_widget

    def create_button(self, text, func, layout, enabled=True):
        button = PushButton(text, self)
        button.setEnabled(enabled)
        button.clicked.connect(func)
        layout.addWidget(button)
        return button

    def create_label(self, text, layout, centered=False, link=False):
        label = QtWidgets.QLabel(text, self)
        if centered:
            label.setAlignment(QtCore.Qt.AlignCenter)
        if link:
            label.setOpenExternalLinks(True)
        layout.addWidget(label)

    def run_exe(self):
        command = [GOODBYE_DPI_EXE] + self.script_options[self.selected_script.currentText()]
        self.start_process(command, "GoodbyeDPI", disable_run=True, clear_console_text="Процесс GoodbyeDPI запущен...")

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

    def on_finished(self, process_name):
        if process_name == "GoodbyeDPI":
            self.run_button.setEnabled(True)
            self.stop_close_button.setEnabled(False)
            self.console_output.append(f"Процесс {process_name} завершен.")

    def stop_and_close(self):
        self.start_process(WIN_DIVERT_COMMAND, "WinDivert")
        self.close_goodbyedpi()

    def close_goodbyedpi(self):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == GOODBYE_DPI_PROCESS_NAME:
                    psutil.Process(proc.info['pid']).terminate()
                    return
            self.console_output.append("Процесс GoodbyeDPI не найден.")
        except psutil.Error as e:
            self.console_output.append(f"Ошибка завершения процесса: {str(e)}")

    def update_blacklist(self):
        self.clear_console("Обновление черного списка...")
        self.updater.blacklist_updated.connect(self.on_blacklist_updated)
        self.updater.update_error.connect(self.on_update_error)
        self.updater.update_blacklist()

    def check_for_updates(self):
        self.update_button.setEnabled(False)
        self.updater.update_available.connect(self.notify_update)
        self.updater.no_update.connect(self.no_update)
        self.updater.update_error.connect(self.on_update_error)
        self.updater.finished.connect(self.on_update_finished)
        self.updater.start()

    def no_update(self):
        self.console_output.append("Обновлений не найдено.")
        QtWidgets.QMessageBox.information(self, "Обновление", "Обновлений не найдено.")

    def on_update_finished(self):
        self.update_button.setEnabled(True)

    def on_blacklist_updated(self):
        QtWidgets.QMessageBox.information(self, "Обновление черного списка", "Черный список обновлен.")
    
    def on_update_error(self, error_message):
        self.console_output.append(error_message)
        QtWidgets.QMessageBox.warning(self, "Ошибка обновления", error_message)

    def notify_update(self, latest_version):
        QtWidgets.QMessageBox.information(self, "Доступно обновление", f"Доступна новая версия {latest_version}. Перейдите на страницу загрузки.")

    def create_service(self):
        try:
            arch = 'x86_64' if platform.machine().endswith('64') else 'x86'
            binary_path = f'"{os.getcwd()}\\{arch}\\goodbyedpi.exe"'
            blacklist_path = f'"{os.getcwd()}\\russia-blacklist.txt"'
            youtube_blacklist_path = f'"{os.getcwd()}\\russia-youtube.txt"'

            subprocess.run([
                'sc', 'create', 'GoodbyeDPI',
                f'binPath= {binary_path} -9 --blacklist {blacklist_path} --blacklist {youtube_blacklist_path}',
                'start=', 'auto'
            ], check=True)

            subprocess.run([
                'sc', 'description', 'GoodbyeDPI',
                'Passive Deep Packet Inspection blocker and Active DPI circumvention utility'
            ], check=True)

            QtWidgets.QMessageBox.information(self, "Служба", "Служба GoodbyeDPI создана и настроена для автоматического запуска.")
        except subprocess.CalledProcessError:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось создать службу.")

    def delete_service(self):
        try:
            subprocess.run(['sc', 'delete', 'GoodbyeDPI'], check=True)
            QtWidgets.QMessageBox.information(self, "Служба", "Служба успешно удалена.")
        except subprocess.CalledProcessError:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось удалить службу GoodbyeDPI.")

    def clear_console(self, initial_text=""):
        self.console_output.clear()
        if initial_text:
            self.console_output.append(initial_text)
