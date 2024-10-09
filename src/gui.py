import os
import sys 
import platform
import logging
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QIcon, QPixmap, QColor
from qfluentwidgets import PushButton, ComboBox, TextEdit, Theme, setTheme
from process_worker import WorkerThread
from utils import (
    SITES, DISPLAY_NAMES, BASE_FOLDER, BLACKLIST_FILES, 
    GOODBYE_DPI_EXE, WIN_DIVERT_COMMAND, GOODBYE_DPI_PROCESS_NAME, 
    current_version, SCRIPT_OPTIONS
)
from site_checker import SiteCheckerWorker
from updater import Updater
import psutil
import subprocess
import webbrowser

LOG_FILE = os.path.join(BASE_FOLDER, "app_zhivem_v1.5.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class GoodbyeDPIApp(QtWidgets.QWidget):
    site_status_updated = QtCore.pyqtSignal(str, str)
    sites_check_finished = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.updater = Updater()

        self.site_status_updated.connect(self.update_site_status)
        self.sites_check_finished.connect(self.finish_check_sites)

        QtCore.QTimer.singleShot(0, self.check_sites_status)

    def init_ui(self):
        self.setWindowTitle(f"GoodByeDPI GUI by Zhivem v{current_version}")
        self.setFixedSize(420, 510)
        self.setWindowIcon(QIcon(os.path.join(BASE_FOLDER, "icon", 'fackrkn.ico')))
        setTheme(Theme.LIGHT)

        layout = QtWidgets.QVBoxLayout(self)
        tab_widget = self.create_tabs()
        layout.addWidget(tab_widget)

    def create_tabs(self):
        tab_widget = QtWidgets.QTabWidget(self)

        process_tab = self.create_process_tab()
        tab_widget.addTab(process_tab, "GoodbyeDPI")

        settings_tab = self.create_settings_tab()
        tab_widget.addTab(settings_tab, "Настройки")

        return tab_widget

    def create_process_tab(self):
        process_tab = QtWidgets.QWidget()
        process_layout = QtWidgets.QVBoxLayout(process_tab)

        self.selected_script = ComboBox()
        self.selected_script.addItems(SCRIPT_OPTIONS.keys())
        process_layout.addWidget(self.selected_script)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.run_button = self.create_button("Запустить", self.run_exe, buttons_layout)
        self.stop_close_button = self.create_button(
            "Остановить и закрыть", self.stop_and_close, buttons_layout, enabled=False
        )
        process_layout.addLayout(buttons_layout)

        self.console_output = TextEdit(self)
        self.console_output.setReadOnly(True)
        process_layout.addWidget(self.console_output)

        return process_tab

    def create_settings_tab(self):
        settings_tab = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_tab)

        services_group = QtWidgets.QGroupBox("Службы")
        services_layout = QtWidgets.QVBoxLayout()
        services_group.setLayout(services_layout)
        self.create_button("Создать службу", self.create_service, services_layout)
        self.create_button("Удалить службу", self.delete_service, services_layout)
        settings_layout.addWidget(services_group)

        updates_group = QtWidgets.QGroupBox("Обновления")
        updates_layout = QtWidgets.QVBoxLayout()
        updates_group.setLayout(updates_layout)
        self.create_button("Обновить черный список", self.update_blacklist, updates_layout)
        self.update_button = self.create_button("Проверить обновления", self.check_for_updates, updates_layout)
        settings_layout.addWidget(updates_group)

        sites_group = QtWidgets.QGroupBox("Основные сайты YouTube")
        sites_layout = QtWidgets.QVBoxLayout()
        sites_group.setLayout(sites_layout)
        sites_widget = self.create_sites_list(DISPLAY_NAMES)
        sites_layout.addWidget(sites_widget)
        self.check_sites_button = PushButton("Проверить доступность", self)
        self.check_sites_button.clicked.connect(self.check_sites_status)
        sites_layout.addWidget(self.check_sites_button)
        settings_layout.addWidget(sites_group)

        info_layout = QtWidgets.QVBoxLayout()
        info_label = QtWidgets.QLabel(f"GoodbyeDPI GUI by Zhivem v{current_version}")
        info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_layout.addWidget(info_label)

        github_label = QtWidgets.QLabel(
            '<a href="https://github.com/zhivem/GoodByDPI-GUI-by-Zhivem">Проект на GitHub</a>'
        )
        github_label.setAlignment(QtCore.Qt.AlignCenter)
        github_label.setOpenExternalLinks(True)
        info_layout.addWidget(github_label)

        settings_layout.addLayout(info_layout)
        settings_layout.addStretch(1)

        return settings_tab

    def create_sites_list(self, sites):
        list_widget = QtWidgets.QListWidget()
        list_widget.setFixedHeight(113)

        self.site_status = {}
        for site in sites:
            item = QtWidgets.QListWidgetItem(site)
            pixmap = QPixmap(12, 12)
            pixmap.fill(QColor('gray'))
            icon = QtGui.QIcon(pixmap)
            item.setIcon(icon)
            list_widget.addItem(item)
            self.site_status[site] = item

        return list_widget

    def create_button(self, text, func, layout, enabled=True):
        button = PushButton(text, self)
        button.setEnabled(enabled)
        button.clicked.connect(func)
        layout.addWidget(button)
        return button

    def run_exe(self):
        selected_option = self.selected_script.currentText()
        if selected_option not in SCRIPT_OPTIONS:
            logging.error(f"Неизвестный вариант скрипта: {selected_option}")
            self.console_output.append(f"Ошибка: неизвестный вариант скрипта {selected_option}.")
            return

        executable, args = SCRIPT_OPTIONS[selected_option]

        if not self.is_executable_available(executable, selected_option):
            return

        command = [executable] + args
        logging.debug(f"Команда для запуска: {command}")

        try:
            capture_output = not selected_option in ["Обход блокировки Discord", "Обход Discord + YouTube"]
            self.start_process(
                command,
                selected_option,
                disable_run=True,
                clear_console_text=f"Установка: {selected_option} запущена...",
                capture_output=capture_output
            )
        except Exception as e:
            logging.error(f"Ошибка запуска процесса: {e}")
            self.console_output.append(f"Ошибка запуска процесса: {e}")

    def is_executable_available(self, executable, selected_option):
        if not os.path.exists(executable):
            logging.error(f"Файл {executable} не найден.")
            self.console_output.append(f"Ошибка: файл {executable} не найден.")
            return False

        if not os.access(executable, os.X_OK):
            logging.error(f"Недостаточно прав для запуска {executable}.")
            self.console_output.append(f"Ошибка: Недостаточно прав для запуска {executable}.")
            return False

        if selected_option in ["Обход блокировки Discord", "Обход Discord + YouTube"]:
            required_files = [
                os.path.join(BASE_FOLDER, "black", "discord-blacklist.txt"),
                os.path.join(BASE_FOLDER, "zapret", "quic_initial_www_google_com.bin"),
                os.path.join(BASE_FOLDER, "zapret", "tls_clienthello_www_google_com.bin")
            ]
            missing_files = [f for f in required_files if not os.path.exists(f)]
            if missing_files:
                logging.error(f"Не найдены необходимые файлы: {', '.join(missing_files)}")
                self.console_output.append(f"Ошибка: не найдены файлы: {', '.join(missing_files)}")
                return False

        return True

    def start_process(self, command, process_name, disable_run=False, clear_console_text=None, capture_output=True):
        if clear_console_text:
            self.clear_console(clear_console_text)

        try:
            self.worker_thread = WorkerThread(
                command, 
                process_name, 
                encoding="cp866", 
                capture_output=capture_output
            )
            if capture_output:
                self.worker_thread.output_signal.connect(self.update_output)
            self.worker_thread.finished_signal.connect(self.on_finished)

            self.worker_thread.start()

            if disable_run:
                self.run_button.setEnabled(False)
                self.stop_close_button.setEnabled(True)
        except Exception as e:
            logging.error(f"Ошибка при запуске потока: {e}")
            self.console_output.append(f"Ошибка при запуске потока: {e}")

    def update_output(self, text):
        self.console_output.append(text)
        max_lines = 100
        document = self.console_output.document()
        while document.blockCount() > max_lines:
            cursor = self.console_output.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.select(QtGui.QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def on_finished(self, process_name):
        if process_name in SCRIPT_OPTIONS:
            self.run_button.setEnabled(True)
            self.stop_close_button.setEnabled(False)
            logging.debug(f"Процесс {process_name} завершён.")

    def stop_and_close(self):
        self.start_process(WIN_DIVERT_COMMAND, "WinDivert", capture_output=False)
        self.close_process(GOODBYE_DPI_PROCESS_NAME, "GoodbyeDPI")
        self.close_process("winws.exe", "winws.exe")

    def close_process(self, process_name, display_name):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    psutil.Process(proc.info['pid']).terminate()
                    self.console_output.append(f"Процесс {display_name} завершен.")
                    logging.debug(f"Процесс {display_name} (PID: {proc.info['pid']}) завершён.")
        except psutil.Error as e:
            self.console_output.append(f"Ошибка завершения процесса {display_name}: {str(e)}")
            logging.error(f"Ошибка завершения процесса {display_name}: {str(e)}")

    def update_blacklist(self):
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
            binary_path = f'"{os.path.join(os.getcwd(), arch, "goodbyedpi.exe")}"'
            blacklist_path = f'"{os.path.join(os.getcwd(), "russia-blacklist.txt")}"'
            youtube_blacklist_path = f'"{os.path.join(os.getcwd(), "russia-youtube.txt")}"'

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

    def check_sites_status(self):
        self.check_sites_button.setEnabled(False)

        self.site_checker_thread = QtCore.QThread()
        self.site_checker_worker = SiteCheckerWorker(self.site_status.keys())
        self.site_checker_worker.moveToThread(self.site_checker_thread)

        self.site_checker_thread.started.connect(self.site_checker_worker.run)
        self.site_checker_worker.site_checked.connect(self.update_site_status)
        self.site_checker_worker.finished.connect(self.sites_check_finished)
        self.site_checker_worker.finished.connect(self.site_checker_thread.quit)
        self.site_checker_worker.finished.connect(self.site_checker_worker.deleteLater)
        self.site_checker_thread.finished.connect(self.site_checker_thread.deleteLater)

        self.site_checker_thread.start()

    @QtCore.pyqtSlot(str, str)
    def update_site_status(self, site, color):
        if site in self.site_status:
            pixmap = QPixmap(12, 12)
            pixmap.fill(QColor(color))
            icon = QtGui.QIcon(pixmap)
            self.site_status[site].setIcon(icon)
            logging.debug(f"Сайт {site} доступен: {color}")

    @QtCore.pyqtSlot()
    def finish_check_sites(self):
        self.check_sites_button.setEnabled(True)

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = GoodbyeDPIApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
