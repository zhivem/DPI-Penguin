import logging
import os
import sys

import psutil
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import QAction, QCheckBox, QMenu, QSystemTrayIcon
from qfluentwidgets import ComboBox, PushButton, TextEdit, Theme, setTheme

from process_worker import WorkerThread
from site_checker import SiteCheckerWorker
from updater import Updater
from utils import (
    BASE_FOLDER,
    DISPLAY_NAMES,
    GOODBYE_DPI_PROCESS_NAME,
    is_autostart_enabled,
    enable_autostart,
    SCRIPT_OPTIONS,
    disable_autostart,
    create_service,
    delete_service,
    current_version,
    WIN_DIVERT_COMMAND
)

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

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.join(BASE_FOLDER, "icon", 'fackrkn.ico')))
        
        tray_menu = QMenu()

        restore_action = QAction("Развернуть", self)
        restore_action.triggered.connect(self.show)
        tray_menu.addAction(restore_action)

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        self.site_status_updated.connect(self.update_site_status)
        self.sites_check_finished.connect(self.finish_check_sites)

        self.minimize_to_tray = True 

        QtCore.QTimer.singleShot(0, self.check_sites_status)

    def init_ui(self):
        self.setWindowTitle(f"GoodByeDPI GUI by Zhivem v{current_version}")
        self.setFixedSize(420, 585)
        self.setWindowIcon(QIcon(os.path.join(BASE_FOLDER, "icon", 'fackrkn.ico')))
        setTheme(Theme.LIGHT)

        layout = QtWidgets.QVBoxLayout(self)
        tab_widget = self.create_tabs()
        layout.addWidget(tab_widget)

    def closeEvent(self, event):
        if self.minimize_to_tray:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "GoodByeDPI GUI by Zhivem",
                "Приложение свернуто в трей. Для восстановления, нажмите на иконку в трее.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            event.accept() 

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.show()
            else:
                self.hide()

    def exit_app(self):
        QtWidgets.QApplication.quit()

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
        self.stop_close_button = self.create_button("Остановить и закрыть", self.stop_and_close, buttons_layout, enabled=False)
        process_layout.addLayout(buttons_layout)

        self.console_output = TextEdit(self)
        self.console_output.setReadOnly(True)
        process_layout.addWidget(self.console_output)

        return process_tab

    def create_settings_tab(self):
        settings_tab = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_tab)

        autostart_group = QtWidgets.QGroupBox("Автозапуск")
        autostart_layout = QtWidgets.QVBoxLayout()
        autostart_group.setLayout(autostart_layout)

        self.tray_checkbox = QCheckBox("Сворачивать в трей при закрытии приложения")
        self.tray_checkbox.setChecked(True)  
        self.tray_checkbox.stateChanged.connect(self.toggle_tray_behavior)
        autostart_layout.addWidget(self.tray_checkbox)

        self.autostart_checkbox = QCheckBox("Запускать программу при старте системы")
        self.autostart_checkbox.setChecked(is_autostart_enabled())
        self.autostart_checkbox.stateChanged.connect(self.toggle_autostart)
        autostart_layout.addWidget(self.autostart_checkbox)

        font = self.tray_checkbox.font()
        font.setPointSize(9)  
        self.tray_checkbox.setFont(font)
        self.autostart_checkbox.setFont(font)

        settings_layout.addWidget(autostart_group)

        services_group = QtWidgets.QGroupBox("Службы")
        services_layout = QtWidgets.QVBoxLayout()
        services_group.setLayout(services_layout)

        self.create_button("Создать службу", self.handle_create_service, services_layout)
        self.create_button("Удалить службу", self.handle_delete_service, services_layout)

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

        github_label = QtWidgets.QLabel('<a href="https://github.com/zhivem/GoodByDPI-GUI-by-Zhivem">Проект на GitHub</a>')
        github_label.setAlignment(QtCore.Qt.AlignCenter)
        github_label.setOpenExternalLinks(True)
        info_layout.addWidget(github_label)

        settings_layout.addLayout(info_layout)
        settings_layout.addStretch(1)

        return settings_tab

    def toggle_tray_behavior(self, state):
        if state == QtCore.Qt.Checked:
            self.minimize_to_tray = True
        else:
            self.minimize_to_tray = False

    def toggle_autostart(self, state):
        if state == QtCore.Qt.Checked:
            enable_autostart()
        else:
            disable_autostart()

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
    
    def handle_create_service(self):
        result = create_service()
        QtWidgets.QMessageBox.information(self, "Создание службы", result)

    def handle_delete_service(self):
        result = delete_service()
        QtWidgets.QMessageBox.information(self, "Удаление службы", result)

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
                    self.console_output.append(f"Процесс обхода завершен.")
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
