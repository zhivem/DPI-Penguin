import logging
import os
import sys

import psutil
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSettings, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QGroupBox,
    QMenu,
    QSystemTrayIcon,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
)
from qfluentwidgets import ComboBox as QFComboBox, PushButton, TextEdit

from process_worker import WorkerThread
from site_checker import SiteCheckerWorker
from updater import Updater
from utils import (
    BASE_FOLDER,
    DISPLAY_NAMES,
    GOODBYE_DPI_PROCESS_NAME,
    SCRIPT_OPTIONS,
    WIN_DIVERT_COMMAND,
    current_version,
    create_service,
    delete_service,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    open_txt_file,
)
import theme_utils


class GoodbyeDPIApp(QtWidgets.QWidget):
    site_status_updated = pyqtSignal(str, str)
    sites_check_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("GoodbyeDPIApp инициализирован.")

        self.settings = QSettings("Zhivem", "GoodbyeDPIApp")
        self.init_ui()
        self.updater = Updater()

        # Настройка системного трея
        self.tray_icon = QSystemTrayIcon(self)
        tray_icon_path = os.path.join(BASE_FOLDER, "icon", 'newicon.ico')
        if not os.path.exists(tray_icon_path):
            self.logger.error(f"Файл иконки трея не найден: {tray_icon_path}")
        self.tray_icon.setIcon(QIcon(tray_icon_path))

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

        # Соединение сигналов
        self.site_status_updated.connect(self.update_site_status)
        self.sites_check_finished.connect(self.finish_check_sites)

        self.minimize_to_tray = True
        QtCore.QTimer.singleShot(0, self.check_sites_status)

    def init_ui(self):
        self.setWindowTitle(f"DPI Penguin v{current_version}")
        self.setFixedSize(420, 585)
        icon_path = os.path.join(BASE_FOLDER, "icon", 'newicon.ico')
        if not os.path.exists(icon_path):
            self.logger.error(f"Файл иконки приложения не найден: {icon_path}")
        self.setWindowIcon(QIcon(icon_path))

        # Применение темы
        saved_theme = self.settings.value("theme", "light")
        theme_utils.apply_theme(self, saved_theme, self.settings, BASE_FOLDER)

        layout = QtWidgets.QVBoxLayout(self)
        tab_widget = self.create_tabs()
        layout.addWidget(tab_widget)

    def closeEvent(self, event):
        if self.minimize_to_tray:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                f"DPI Penguin v{current_version}",
                "Приложение свернуто в трей. Для восстановления, нажмите на иконку в трее.",
                QSystemTrayIcon.Information,
                2000
            )
            self.logger.info("Приложение свернуто в трей.")
        else:
            self.logger.info("Приложение закрыто пользователем.")
            event.accept()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.show()
                self.logger.debug("Приложение развёрнуто из трея.")
            else:
                self.hide()
                self.logger.debug("Приложение свернуто в трей.")

    def exit_app(self):
        self.logger.info("Пользователь инициировал выход из приложения.")
        self.stop_and_close()
        QtWidgets.QApplication.quit()


    def create_tabs(self):
        tab_widget = QtWidgets.QTabWidget(self)
        tab_widget.addTab(self.create_process_tab(), "Основное")
        tab_widget.addTab(self.create_settings_tab(), "Настройки")
        tab_widget.addTab(self.create_info_tab(), "О программе")
        return tab_widget

    def create_process_tab(self):
        process_tab = QtWidgets.QWidget()
        process_layout = QtWidgets.QVBoxLayout(process_tab)

        # Выбор скрипта
        self.selected_script = QFComboBox()
        self.selected_script.addItems(SCRIPT_OPTIONS.keys())
        process_layout.addWidget(self.selected_script)

        # Кнопки запуска и остановки
        buttons_layout = QtWidgets.QHBoxLayout()
        self.run_button = self.create_button("Запустить", self.run_exe, buttons_layout)
        self.stop_close_button = self.create_button(
            "Остановить и закрыть",
            self.stop_and_close,
            buttons_layout,
            enabled=False
        )
        process_layout.addLayout(buttons_layout)

        # Консольный вывод
        self.console_output = TextEdit(self)
        self.console_output.setReadOnly(True)
        process_layout.addWidget(self.console_output)

        # Кнопка открытия лог-файла
        self.open_txt_button = self.create_button(
            text="Открыть Log файл",
            func=self.open_txt_file_from_gui,
            layout=process_layout,
            icon_path=os.path.join(BASE_FOLDER, "icon", "log.png"),
            icon_size=(16, 16)
        )

        # Кнопка переключения темы
        self.theme_toggle_button = PushButton()
        theme_utils.update_theme_button_text(self, self.settings)
        theme_icon_path = os.path.join(BASE_FOLDER, "icon", "themes.png")
        if not os.path.exists(theme_icon_path):
            self.logger.error(f"Файл иконки темы не найден: {theme_icon_path}")
        self.theme_toggle_button.setIcon(QIcon(theme_icon_path))
        self.theme_toggle_button.clicked.connect(self.toggle_theme_button_clicked)
        process_layout.addWidget(self.theme_toggle_button)

        return process_tab

    def toggle_theme_button_clicked(self):
        self.logger.debug("Кнопка переключения темы нажата.")
        theme_utils.toggle_theme(self, self.settings, BASE_FOLDER)

    def create_settings_tab(self):
        settings_tab = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_tab)

        # Группа автозапуска
        autostart_group = QGroupBox("Автозапуск")
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

        # Настройка шрифта
        font = self.tray_checkbox.font()
        font.setPointSize(9)
        self.tray_checkbox.setFont(font)
        self.autostart_checkbox.setFont(font)

        settings_layout.addWidget(autostart_group)

        # Группа служб
        services_group = QGroupBox("Службы")
        services_layout = QtWidgets.QVBoxLayout()
        services_group.setLayout(services_layout)

        self.create_button("Создать службу", self.handle_create_service, services_layout)
        self.create_button("Удалить службу", self.handle_delete_service, services_layout)

        settings_layout.addWidget(services_group)

        # Группа обновлений
        updates_group = QGroupBox("Обновления")
        updates_layout = QtWidgets.QVBoxLayout()
        updates_group.setLayout(updates_layout)
        self.create_button("Обновить черный список", self.update_blacklist, updates_layout)
        self.update_button = self.create_button("Проверить обновления", self.check_for_updates, updates_layout)
        settings_layout.addWidget(updates_group)

        # Группа основных сайтов YouTube
        sites_group = QGroupBox("Основные сайты YouTube")
        sites_layout = QtWidgets.QVBoxLayout()
        sites_group.setLayout(sites_layout)
        sites_widget = self.create_sites_list(DISPLAY_NAMES)
        sites_layout.addWidget(sites_widget)
        self.check_sites_button = PushButton("Проверить доступность", self)
        self.check_sites_button.clicked.connect(self.check_sites_status)
        sites_layout.addWidget(self.check_sites_button)
        settings_layout.addWidget(sites_group)

        settings_layout.addStretch(1)

        return settings_tab
    
    def create_info_tab(self):
        info_tab = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(info_tab)

        # Подробности
        details_group = self.create_details_group()
        info_layout.addWidget(details_group)

        # Благодарности
        acknowledgements_group = self.create_acknowledgements_group()
        info_layout.addWidget(acknowledgements_group)

        info_layout.addStretch(1)
        return info_tab

    def create_details_group(self):
        """Создание группы с информацией о программе"""
        group = QtWidgets.QGroupBox("Подробности")
        layout = QtWidgets.QGridLayout(group)

        # Заголовки и данные
        version_label = QtWidgets.QLabel("Версия")
        version_value = QtWidgets.QLabel(f"v{current_version}")
        developer_label = QtWidgets.QLabel("Разработчик")
        developer_value = QtWidgets.QLabel("Zhivem")
        github_label = QtWidgets.QLabel("Репозиторий на GitHub")
        github_link = QtWidgets.QLabel("<a href='https://github.com/zhivem/DPI-Penguin'>DPI Penguin</a>")
        github_link.setOpenExternalLinks(True)

        support_label = QtWidgets.QLabel("Версии:")
        support_link = QtWidgets.QLabel("<a href='https://github.com/zhivem/DPI-Penguin/releases'>Releases</a>")
        support_link.setOpenExternalLinks(True)

        # Лицензия
        license_text = QtWidgets.QLabel("© 2024 Zhivem. License: Apache License, Version 2.0.")
    
        # Расположение виджетов
        layout.addWidget(version_label, 0, 1)
        layout.addWidget(version_value, 0, 2)
        layout.addWidget(developer_label, 1, 1)
        layout.addWidget(developer_value, 1, 2)
        layout.addWidget(github_label, 2, 1)
        layout.addWidget(github_link, 2, 2)
        layout.addWidget(support_label, 3, 1)
        layout.addWidget(support_link, 3, 2)
        layout.addWidget(license_text, 4, 1, 1, 2)

        return group

    def create_acknowledgements_group(self):
    
        group = QtWidgets.QGroupBox("Благодарности")
        layout = QtWidgets.QVBoxLayout(group)

        
        goodbye_dpi_section = self.create_acknowledgement_section(
            "GoodbyeDPI",
            "Основа для работы YouTube",
            "Версия: 0.2.3rc3",
            "ValdikSS",
            ["https://github.com/ValdikSS/GoodbyeDPI/", "https://github.com/ValdikSS/"]
        )

        zapret_section = self.create_acknowledgement_section(
            "Zapret",
            "Основа для работы Discord и YouTube",
            "v.64",
            "bol-van",
            ["https://github.com/bol-van/zapret", "https://github.com/bol-van/"]
        )

        # Добавление разделов
        layout.addWidget(goodbye_dpi_section)
        layout.addWidget(zapret_section)

        return group

    def create_acknowledgement_section(self, title, description, version, developer, links):
        section = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(section)

        # Заголовки и данные
        title_label = QtWidgets.QLabel(f"<b>{title}</b>")
        description_label = QtWidgets.QLabel(f"Описание: {description}")
        version_label = QtWidgets.QLabel(f"Version: {version}")
        developer_label = QtWidgets.QLabel(f"Developer: {developer}")

        # Ссылки
        link_labels = []
        for link in links:
            link_label = QtWidgets.QLabel(f"<a href='{link}'>{link}</a>")
            link_label.setOpenExternalLinks(True)
            link_labels.append(link_label)
    
         # Расположение виджетов
        layout.addWidget(title_label, 0, 0, 1, 2)
        layout.addWidget(description_label, 1, 0, 1, 2)
        layout.addWidget(version_label, 2, 0)
        layout.addWidget(developer_label, 2, 1)
        for i, link_label in enumerate(link_labels):
            layout.addWidget(link_label, 3 + i, 0, 1, 2)

        return section

    def toggle_tray_behavior(self, state):
        self.minimize_to_tray = state == Qt.Checked
        self.logger.debug(f"Поведение сворачивания в трей изменено: {self.minimize_to_tray}")

    def toggle_autostart(self, state):
        if state == Qt.Checked:
            enable_autostart()
            self.logger.info("Автозапуск включен.")
        else:
            disable_autostart()
            self.logger.info("Автозапуск отключен.")

    def create_sites_list(self, sites):
        list_widget = QListWidget()
        list_widget.setFixedHeight(150)

        self.site_status = {}
        for site in sites:
            item = QListWidgetItem(site)
            pixmap = QPixmap(12, 12)
            pixmap.fill(QColor('gray'))
            icon = QIcon(pixmap)
            item.setIcon(icon)
            list_widget.addItem(item)
            self.site_status[site] = item

        self.logger.debug("Список сайтов создан.")
        return list_widget

    def create_button(self, text, func, layout, enabled=True, icon_path=None, icon_size=(24, 24)):
        button = PushButton(text, self)
        button.setEnabled(enabled)
        button.clicked.connect(func)

        if icon_path:
            if not os.path.exists(icon_path):
                self.logger.error(f"Файл иконки не найден: {icon_path}")
            else:
                icon = QIcon(icon_path)
                button.setIcon(icon)
                button.setIconSize(QtCore.QSize(*icon_size))

        layout.addWidget(button)
        self.logger.debug(f"Кнопка '{text}' создана и добавлена в макет.")
        return button

    def handle_create_service(self):
        self.logger.debug("Начата процедура создания службы.")
        result = create_service()
        QMessageBox.information(self, "Создание службы", result)
        self.logger.info(f"Результат создания службы: {result}")

    def handle_delete_service(self):
        self.logger.debug("Начата процедура удаления службы.")
        result = delete_service()
        QMessageBox.information(self, "Удаление службы", result)
        self.logger.info(f"Результат удаления службы: {result}")

    def run_exe(self):
        selected_option = self.selected_script.currentText()
        self.logger.debug(f"Выбранный вариант скрипта: {selected_option}")
        if selected_option not in SCRIPT_OPTIONS:
            self.logger.error(f"Неизвестный вариант скрипта: {selected_option}")
            self.console_output.append(f"Ошибка: неизвестный вариант скрипта {selected_option}.")
            return

        executable, args = SCRIPT_OPTIONS[selected_option]

        if not self.is_executable_available(executable, selected_option):
            return

        command = [executable] + args
        self.logger.debug(f"Команда для запуска: {command}")

        try:
            capture_output = selected_option not in ["Обход блокировки Discord", "Обход Discord + YouTube"]
            self.start_process(
                command,
                selected_option,
                disable_run=True,
                clear_console_text=f"Установка: {selected_option} запущена...",
                capture_output=capture_output
            )
            self.logger.info(f"Процесс '{selected_option}' запущен.")
        except Exception as e:
            self.logger.error(f"Ошибка запуска процесса: {e}", exc_info=True)
            self.console_output.append(f"Ошибка запуска процесса: {e}")

    def is_executable_available(self, executable, selected_option):
        if not os.path.exists(executable):
            self.logger.error(f"Файл {executable} не найден.")
            self.console_output.append(f"Ошибка: файл {executable} не найден.")
            return False

        if not os.access(executable, os.X_OK):
            self.logger.error(f"Недостаточно прав для запуска {executable}.")
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
                self.logger.error(f"Не найдены необходимые файлы: {', '.join(missing_files)}")
                self.console_output.append(f"Ошибка: не найдены файлы: {', '.join(missing_files)}")
                return False

        self.logger.debug(f"Исполняемый файл {executable} доступен для запуска.")
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
                self.logger.debug(f"Кнопка 'Запустить' отключена, 'Остановить и закрыть' включена.")
        except Exception as e:
            self.logger.error(f"Ошибка при запуске потока: {e}", exc_info=True)
            self.console_output.append(f"Ошибка при запуске потока: {e}")

    def update_output(self, text):
        self.console_output.append(text)
        self.logger.debug(f"Консольный вывод обновлен: {text}")
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
            self.logger.info(f"Процесс {process_name} завершён.")

    def stop_and_close(self):
        self.logger.info("Начата процедура остановки и закрытия процессов.")
        self.start_process(WIN_DIVERT_COMMAND, "WinDivert", capture_output=False)
        self.close_process(GOODBYE_DPI_PROCESS_NAME, "GoodbyeDPI")
        self.close_process("winws.exe", "winws.exe")

    def close_process(self, process_name, display_name):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    psutil.Process(proc.info['pid']).terminate()
                    self.console_output.append(f"Процесс завершен. Обход блокировки остановлен")
                    self.logger.debug(f"Процесс {display_name} (PID: {proc.info['pid']}) завершён.")
        except psutil.NoSuchProcess:
            self.logger.warning(f"Процесс {display_name} не найден.")
        except psutil.AccessDenied:
            self.logger.error(f"Недостаточно прав для завершения процесса {display_name}.")
            self.console_output.append(f"Ошибка: Недостаточно прав для завершения процесса {display_name}.")
        except Exception as e:
            self.console_output.append(f"Ошибка завершения процесса {display_name}: {str(e)}")
            self.logger.error(f"Ошибка завершения процесса {display_name}: {str(e)}")

    def update_blacklist(self):
        self.logger.debug("Начата процедура обновления черного списка.")
        self.updater.blacklist_updated.connect(self.on_blacklist_updated)
        self.updater.update_error.connect(self.on_update_error)
        self.updater.update_blacklist()

    def check_for_updates(self):
        self.update_button.setEnabled(False)
        self.logger.debug("Пользователь инициировал проверку обновлений.")
        self.updater.update_available.connect(self.notify_update)
        self.updater.no_update.connect(self.no_update)
        self.updater.update_error.connect(self.on_update_error)
        self.updater.finished.connect(self.on_update_finished)
        self.updater.start()

    def no_update(self):
        self.logger.info("Обновления не найдены.")
        QMessageBox.information(self, "Обновление", "Обновлений не найдено.")

    def on_update_finished(self):
        self.update_button.setEnabled(True)
        self.logger.debug("Процесс проверки обновлений завершен.")

    def on_blacklist_updated(self):
        self.logger.info("Черный список обновлен.")
        QMessageBox.information(self, "Обновление черного списка", "Черный список обновлен.")

    def on_update_error(self, error_message):
        self.logger.error(f"Ошибка обновления: {error_message}")
        self.console_output.append(error_message)
        QMessageBox.warning(self, "Ошибка обновления", error_message)

    def notify_update(self, latest_version):
        self.logger.info(f"Доступна новая версия: {latest_version}")
        QMessageBox.information(
            self,
            "Доступно обновление",
            f"Доступна новая версия {latest_version}. Перейдите на страницу загрузки."
        )

    def clear_console(self, initial_text=""):
        self.console_output.clear()
        if initial_text:
            self.console_output.append(initial_text)
            self.logger.debug("Консоль очищена с начальным текстом.")

    def check_sites_status(self):
        self.check_sites_button.setEnabled(False)
        self.logger.debug("Начата проверка доступности сайтов.")

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

    @pyqtSlot(str, str)
    def update_site_status(self, site, color):
        if site in self.site_status:
            pixmap = QPixmap(12, 12)
            pixmap.fill(QColor(color))
            icon = QIcon(pixmap)
            self.site_status[site].setIcon(icon)
            self.logger.debug(f"Сайт {site} доступен: {color}")

    @pyqtSlot()
    def finish_check_sites(self):
        self.check_sites_button.setEnabled(True)
        self.logger.info("Проверка доступности сайтов завершена.")

    def open_txt_file_from_gui(self):
        file_path = os.path.join(BASE_FOLDER, "logs", f"app_penguin_v{current_version}.log")
        self.logger.debug(f"Пользователь запросил открытие лог-файла: {file_path}")
        result = open_txt_file(file_path)
        if result:
            QMessageBox.critical(self, "Ошибка", result)
            self.logger.error(f"Ошибка при открытии лог-файла: {result}")
