import logging
import os
import subprocess
import platform
import configparser

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
    QFileDialog,
)
from qfluentwidgets import ComboBox as QFComboBox, PushButton, TextEdit

from workers.process_worker import WorkerThread
from workers.site_checker import SiteCheckerWorker
from utils.updater import Updater
from utils.utils import (
    BASE_FOLDER,
    BLACKLIST_FILES,
    DISPLAY_NAMES,
    GOODBYE_DPI_PROCESS_NAME,
    WIN_DIVERT_COMMAND,
    CURRENT_VERSION,
    create_service,
    delete_service,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    load_script_options,
)
import utils.theme_utils

# Константы для путей к иконкам
TRAY_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "newicon.ico")
THEME_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "themes.png")
LOG_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "log.png")
INI_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "ini.png")

class GoodbyeDPIApp(QtWidgets.QWidget):
    site_status_updated = pyqtSignal(str, str)
    sites_check_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.settings = QSettings("Zhivem", "GoodbyeDPIApp")
        self.ensure_logs_folder_exists()

        # Загрузка SCRIPT_OPTIONS с обработкой ошибок
        self.script_options, self.config_error = load_script_options(
            os.path.join(BASE_FOLDER, "config", "default.ini")
        )
        self.current_config_path = os.path.join(BASE_FOLDER, "config", "default.ini")

        # Инициализация пользовательского интерфейса
        self.init_ui()

        self.updater = Updater()

        self.init_tray_icon()
        self.connect_signals()

        self.minimize_to_tray = True

        if self.config_error:
            # Отображаем ошибку в консольном выводе
            self.console_output.append(self.config_error)
            self.logger.error(self.config_error)
            # Отключаем элементы интерфейса, связанные со скриптами
            self.selected_script.setEnabled(False)
            self.run_button.setEnabled(False)
            self.stop_close_button.setEnabled(False)
            self.update_config_button.setEnabled(False)  # Отключаем кнопку обновления при ошибках

        QtCore.QTimer.singleShot(0, self.check_sites_status)

    def ensure_logs_folder_exists(self):
        logs_folder = os.path.join(BASE_FOLDER, "logs")
        if not os.path.exists(logs_folder):
            try:
                os.makedirs(logs_folder)
                self.logger.info(f"Создана папка logs: {logs_folder}")
            except Exception as e:
                self.logger.error(f"Не удалось создать папку logs: {e}", exc_info=True)

    def init_ui(self):
        self.setWindowTitle(f"DPI Penguin v{CURRENT_VERSION}")
        self.setFixedSize(420, 585)
        self.set_window_icon(TRAY_ICON_PATH)

        # Применение темы
        saved_theme = self.settings.value("theme", "light")
        utils.theme_utils.apply_theme(self, saved_theme, self.settings, BASE_FOLDER)

        layout = QtWidgets.QVBoxLayout(self)
        tab_widget = self.create_tabs()
        layout.addWidget(tab_widget)

    def set_window_icon(self, icon_path):
        if not os.path.exists(icon_path):
            self.logger.error(f"Файл иконки приложения не найден: {icon_path}")
        self.setWindowIcon(QIcon(icon_path))

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(TRAY_ICON_PATH))

        tray_menu = QMenu()

        restore_action = QAction("Развернуть", self)
        restore_action.triggered.connect(self.restore_from_tray)
        tray_menu.addAction(restore_action)

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def connect_signals(self):
        self.site_status_updated.connect(self.update_site_status)
        self.sites_check_finished.connect(self.finish_check_sites)

    def closeEvent(self, event):
        if self.minimize_to_tray:
            event.ignore()
            self.hide()
            self.tray_icon.show()
            self.tray_icon.showMessage(
                "DPI Penguin by Zhivem",
                "Приложение свернуто в трей. Для восстановления, нажмите на иконку в трее.",
                QSystemTrayIcon.Information,
                1000
            )
        else:
            event.accept()

    def restore_from_tray(self):
        self.show()
        self.tray_icon.hide()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.restore_from_tray()
            else:
                self.hide()
                self.tray_icon.show()
                self.tray_icon.showMessage(
                    "DPI Penguin by Zhivem",
                    "Приложение свернуто в трей. Для восстановления, нажмите на иконку в трее.",
                    QSystemTrayIcon.Information,
                    1000
                )

    def exit_app(self):
        self.tray_icon.hide()
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

        # Горизонтальный макет для комбобокса и кнопки загрузки
        script_layout = QtWidgets.QHBoxLayout()

        # Выбор скрипта
        self.selected_script = QFComboBox()
        if not self.config_error:
            self.selected_script.addItems(self.script_options.keys())
        self.selected_script.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        script_layout.addWidget(self.selected_script)

        # Кнопка загрузки конфигурации с текстом
        self.update_config_button = PushButton("📁", self)
        self.update_config_button.setToolTip("Загрузить другую конфигурацию")
        self.update_config_button.clicked.connect(self.load_config_via_dialog)
        self.update_config_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.update_config_button.setFixedWidth(40)
        script_layout.addWidget(self.update_config_button)

        script_layout.setStretch(0, 1)  # QFComboBox
        script_layout.setStretch(1, 0)  # Кнопка загрузки

        process_layout.addLayout(script_layout)

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

        # Горизонтальный макет для кнопок логов и конфигурации
        log_and_config_layout = QtWidgets.QHBoxLayout()

        self.open_logs_button = self.create_button(
            text="Открыть папку Log",
            func=lambda: self.open_path(os.path.join(BASE_FOLDER, "logs")),
            layout=None,
            icon_path=LOG_ICON_PATH,
            icon_size=(16, 16),
            tooltip="Открыть папку логов"
        )
        log_and_config_layout.addWidget(self.open_logs_button)

        self.open_config_button = self.create_button(
            text="Открыть configs",
            func=lambda: self.open_path(os.path.join(BASE_FOLDER, "config")),
            layout=None,
            icon_path=INI_ICON_PATH,
            icon_size=(16, 16),
            tooltip="Открыть папку конфигураций"
        )
        log_and_config_layout.addWidget(self.open_config_button)

        process_layout.addLayout(log_and_config_layout)

        # Кнопка переключения темы
        self.theme_toggle_button = PushButton()
        utils.theme_utils.update_theme_button_text(self, self.settings)
        self.set_button_icon(self.theme_toggle_button, THEME_ICON_PATH, (16, 16))
        self.theme_toggle_button.clicked.connect(self.toggle_theme_button_clicked)
        process_layout.addWidget(self.theme_toggle_button)

        return process_tab

    def set_button_icon(self, button, icon_path, icon_size):
        if not os.path.exists(icon_path):
            self.logger.error(f"Файл иконки не найден: {icon_path}")
        else:
            icon = QIcon(icon_path)
            button.setIcon(icon)
            button.setIconSize(QtCore.QSize(*icon_size))

    def toggle_theme_button_clicked(self):
        utils.theme_utils.toggle_theme(self, self.settings, BASE_FOLDER)

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
        group = QGroupBox("Подробности")
        layout = QtWidgets.QGridLayout(group)

        # Заголовки и данные
        labels = {
            "Версия": f"v{CURRENT_VERSION}",
            "Разработчик": "Zhivem",
            "Репозиторий на GitHub": "<a href='https://github.com/zhivem/DPI-Penguin'>DPI Penguin</a>",
            "Версии": "<a href='https://github.com/zhivem/DPI-Penguin/releases'>Releases</a>",
            "Лицензия": "© 2024 Zhivem. License: Apache License, Version 2.0."
        }

        # Создание виджетов
        widgets = {
            "Версия": QtWidgets.QLabel(labels["Версия"]),
            "Разработчик": QtWidgets.QLabel(labels["Разработчик"]),
            "Репозиторий на GitHub": QtWidgets.QLabel(labels["Репозиторий на GitHub"]),
            "Версии": QtWidgets.QLabel(labels["Версии"]),
            "Лицензия": QtWidgets.QLabel(labels["Лицензия"])
        }

        for row, (key, widget) in enumerate(widgets.items()):
            if key in ["Репозиторий на GitHub", "Версии"]:
                widget.setOpenExternalLinks(True)
            layout.addWidget(QtWidgets.QLabel(key), row, 0)
            layout.addWidget(widget, row, 1)

        return group

    def create_acknowledgements_group(self):
        group = QGroupBox("Зависимости")
        layout = QtWidgets.QVBoxLayout(group)

        dependencies = [
            {
                "title": "GoodbyeDPI",
                "description": "Основа для работы YouTube",
                "version": "0.2.3rc3",
                "developer": "ValdikSS",
                "links": [
                    "https://github.com/ValdikSS/GoodbyeDPI/",
                    "https://github.com/ValdikSS/"
                ]
            },
            {
                "title": "Zapret",
                "description": "Основа для работы Discord и YouTube",
                "version": "v.64",
                "developer": "bol-van",
                "links": [
                    "https://github.com/bol-van/zapret",
                    "https://github.com/bol-van/"
                ]
            }
        ]

        for dep in dependencies:
            section = self.create_acknowledgement_section(**dep)
            layout.addWidget(section)

        return group

    def create_acknowledgement_section(self, title, description, version, developer, links):
        section = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(section)

        # Заголовки и данные
        layout.addWidget(QtWidgets.QLabel(f"<b>{title}</b>"), 0, 0, 1, 2)
        layout.addWidget(QtWidgets.QLabel(f"Описание: {description}"), 1, 0, 1, 2)
        layout.addWidget(QtWidgets.QLabel(f"Version: {version}"), 2, 0)
        layout.addWidget(QtWidgets.QLabel(f"Developer: {developer}"), 2, 1)

        # Ссылки
        for i, link in enumerate(links, start=3):
            link_label = QtWidgets.QLabel(f"<a href='{link}'>{link}</a>")
            link_label.setOpenExternalLinks(True)
            layout.addWidget(link_label, i, 0, 1, 2)

        return section

    def toggle_tray_behavior(self, state):
        self.minimize_to_tray = state == Qt.Checked

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
            icon = self.create_status_icon('gray')
            item.setIcon(icon)
            list_widget.addItem(item)
            self.site_status[site] = item

        return list_widget

    def create_status_icon(self, color):
        pixmap = QPixmap(12, 12)
        pixmap.fill(QColor(color))
        return QIcon(pixmap)

    def create_button(self, text, func, layout, enabled=True, icon_path=None, icon_size=(24, 24), tooltip=None):
        button = PushButton(text, self)
        button.setEnabled(enabled)
        if func:
            button.clicked.connect(func)

        if icon_path:
            self.set_button_icon(button, icon_path, icon_size)

        if tooltip:
            button.setToolTip(tooltip)

        if layout is not None:
            layout.addWidget(button)
        return button

    def handle_create_service(self):
        result = create_service()
        QMessageBox.information(self, "Создание службы", result)

    def handle_delete_service(self):
        result = delete_service()
        QMessageBox.information(self, "Удаление службы", result)

    def run_exe(self):
        if self.config_error:
            self.console_output.append("Не удалось загрузить конфигурацию из-за ошибок.")
            return

        selected_option = self.selected_script.currentText()
        if selected_option not in self.script_options:
            self.console_output.append(f"Ошибка: неизвестный вариант скрипта {selected_option}.")
            return

        executable, args = self.script_options[selected_option]

        if not self.is_executable_available(executable, selected_option):
            return

        command = [executable] + args
        self.logger.debug(f"Команда для запуска: {command}")

        try:
            capture_output = selected_option not in [
                "Обход блокировки Discord",
                "Обход Discord + YouTube",
                "Обход блокировки YouTube"
            ]
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

        if selected_option in [
            "Обход блокировки Discord",
            "Обход Discord + YouTube",
            "Обход блокировок YouTube (Актуальный метод)"
        ]:
            required_files = [
                os.path.join(BASE_FOLDER, "black", BLACKLIST_FILES[2]),
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
                encoding="utf-8",
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
            self.logger.error(f"Ошибка при запуске потока: {e}", exc_info=True)
            self.console_output.append(f"Ошибка при запуске потока: {e}")

    def update_output(self, text):
        # Список ключевых слов для игнорирования (в нижнем регистре)
        ignore_keywords = [
            "loading hostlist",
            "we have",
            "desync profile(s)",
            "loaded hosts",
            "loading plain text list",
            "loaded",  # Можно обобщить для всех сообщений, содержащих "loaded"
        ]
        
        text_lower = text.lower()
        
        if "windivert initialized. capture is started." in text_lower:
            # Если WinDivert запущен, выводим сообщение "Запущено"
            self.console_output.append("Ваша конфигурация выполняется.")
        elif any(keyword in text_lower for keyword in ignore_keywords):
            # Игнорируем повторяющиеся или ненужные логи
            return
        else:
            # Для всего остального выводим текст как есть
            self.console_output.append(text)
        
        # Ограничиваем количество строк в консоли
        max_lines = 100
        document = self.console_output.document()
        while document.blockCount() > max_lines:
            cursor = self.console_output.textCursor()
            cursor.movePosition(QtGui.QTextCursor.Start)
            cursor.select(QtGui.QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def on_finished(self, process_name):
        if process_name in self.script_options:
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
                    self.console_output.append(f"Обход остановлен.")
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
        self.updater.update_available.connect(self.notify_update)
        self.updater.no_update.connect(self.no_update)
        self.updater.update_error.connect(self.on_update_error)
        self.updater.finished.connect(self.on_update_finished)
        self.updater.start()

    def no_update(self):
        QMessageBox.information(self, "Обновление", "Обновлений не найдено.")

    def on_update_finished(self):
        self.update_button.setEnabled(True)

    def on_blacklist_updated(self):
        QMessageBox.information(self, "Обновление черного списка", "Черный список обновлен.")

    def on_update_error(self, error_message):
        self.console_output.append(error_message)
        QMessageBox.warning(self, "Ошибка обновления", error_message)

    def notify_update(self, latest_version):
        self.logger.info(f"Доступна новая версия: {latest_version}")
        QMessageBox.information(
            self,
            "Доступно обновление",
            f'Доступна новая версия {latest_version}. <a href="https://github.com/zhivem/DPI-Penguin/releases">Перейдите на страницу загрузки</a>.',
            QMessageBox.Ok
        )

    def clear_console(self, initial_text=""):
        self.console_output.clear()
        if initial_text:
            self.console_output.append(initial_text)

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
            icon = self.create_status_icon(color)
            self.site_status[site].setIcon(icon)
            self.logger.debug(f"Сайт {site} доступен: {color}")

    @pyqtSlot()
    def finish_check_sites(self):
        self.check_sites_button.setEnabled(True)
        self.logger.info("Проверка доступности сайтов завершена.")

    def open_path(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Ошибка", f"Путь не найден: {path}")
            return

        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", path])
            else:  # Linux и другие
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.logger.error(f"Ошибка при открытии пути {path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть путь: {e}")

    def open_logs_folder(self):
        self.open_path(os.path.join(BASE_FOLDER, "logs"))

    def open_config_file(self):
        self.open_path(os.path.join(BASE_FOLDER, "config"))

    def load_config_via_dialog(self):
        """
        Метод для загрузки конфигурации через проводник.
        Открывает диалог выбора файла и загружает выбранный default.ini.
        Выполняет валидацию выбранного файла.
        """
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл конфигурации",
            "",
            "INI Files (*.ini)",
            options=options
        )
        if file_path:
            self.logger.info(f"Выбран файл конфигурации: {file_path}")
            validation_error = self.validate_config_file(file_path)
            if validation_error:
                # Отображаем ошибку в консольном выводе и в диалоге
                self.console_output.append(validation_error)
                self.logger.error(validation_error)
                QMessageBox.critical(self, "Ошибка загрузки конфигурации", validation_error)
                return

            # Если валидация прошла успешно, загружаем конфиг
            new_script_options, new_config_error = load_script_options(file_path)

            if new_config_error:
                # Отображаем ошибку в консольном выводе и в диалоге
                self.console_output.append(new_config_error)
                self.logger.error(new_config_error)
                QMessageBox.critical(self, "Ошибка загрузки конфигурации", new_config_error)
                return

            # Обновляем текущие опции скриптов
            self.script_options = new_script_options
            self.config_error = None
            self.current_config_path = file_path  # Обновляем путь к текущему конфигу
            self.console_output.append("Конфигурация успешно загружена.")
            self.logger.info("Конфигурация успешно загружена.")

            # Обновляем комбобокс: очищаем существующие элементы и добавляем новые
            self.selected_script.clear()
            self.selected_script.addItems(self.script_options.keys())
            self.selected_script.setEnabled(True)
            self.run_button.setEnabled(True)
            self.stop_close_button.setEnabled(False)

    def validate_config_file(self, file_path):
        """
        Метод для валидации выбранного файла default.ini.
        Проверяет:
        - Существование файла
        - Читаемость файла
        - Корректность INI формата
        - Наличие обязательных секций и ключей
        """
        if not os.path.exists(file_path):
            return f"Файл не найден: {file_path}"

        if not os.access(file_path, os.R_OK):
            return f"Недостаточно прав для чтения файла: {file_path}"

        config = configparser.ConfigParser()
        try:
            config.read(file_path, encoding='utf-8')
        except Exception as e:
            return f"Ошибка при чтении файла INI: {e}"

        # Проверка наличия основной секции
        if 'SCRIPT_OPTIONS' not in config.sections():
            return "Ошибка: Отсутствует секция [SCRIPT_OPTIONS] в конфигурационном файле."

        # Проверка наличия хотя бы одной опции скрипта
        script_sections = [section for section in config.sections() if section != 'SCRIPT_OPTIONS']
        if not script_sections:
            return "Ошибка: В секции [SCRIPT_OPTIONS] отсутствуют настройки скриптов."

        # Проверка обязательных ключей в каждой опции скрипта
        required_keys = ['executable', 'args']
        for section in script_sections:
            for key in required_keys:
                if key not in config[section]:
                    return f"Ошибка: В секции [{section}] отсутствует ключ '{key}'."

        # Дополнительные проверки, допишу потом

        return None
