# gui.py

import logging
import os
import configparser

import psutil
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QMenu,
    QSystemTrayIcon,
    QMessageBox,
    QFileDialog,
)
from qfluentwidgets import ComboBox as QFComboBox, PushButton, TextEdit

from workers.process_worker import WorkerThread
from utils.utils import (
    BASE_FOLDER,
    WIN_DIVERT_COMMAND,
    CURRENT_VERSION,
    create_service,
    delete_service,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    load_script_options,
    open_path,
    tr,
    set_language,
    translation_manager,
    settings,
)
import utils.theme_utils

from gui.updater_manager import SettingsDialog
from utils.update_checker import UpdateChecker  # Импортируем UpdateChecker

TRAY_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "newicon.ico")
THEME_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "themes.png")
LOG_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "log.png")
INI_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "ini.png")
MANAGER_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "manager.png")

class GoodbyeDPIApp(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.ensure_logs_folder_exists()

        self.minimize_to_tray = settings.value("minimize_to_tray", True, type=bool)
        self.autostart_enabled = is_autostart_enabled()
        self.autorun_with_last_config = settings.value("autorun_with_last_config", False, type=bool)

        if self.autorun_with_last_config:
            last_config_path = settings.value("last_config_path", os.path.join(BASE_FOLDER, "config", "default.ini"))
            self.script_options, self.config_error = load_script_options(last_config_path)
            self.current_config_path = last_config_path
        else:
            default_config_path = os.path.join(BASE_FOLDER, "config", "default.ini")
            self.script_options, self.config_error = load_script_options(default_config_path)
            self.current_config_path = default_config_path

        self.worker_thread = None

        self.init_ui()

        self.init_tray_icon()

        if self.config_error:
            self.console_output.append(self.config_error)
            self.logger.error(self.config_error)
            self.selected_script.setEnabled(False)
            self.run_button.setEnabled(False)
            self.stop_close_button.setEnabled(False)
            self.update_config_button.setEnabled(True)

        if settings.value("update_blacklists_on_start", False, type=bool):
            self.update_blacklists(silent=True)

        self.check_updates()

        if self.autorun_with_last_config and not self.config_error:
            last_selected_script = settings.value("last_selected_script", None)
            if last_selected_script and last_selected_script in self.script_options:
                index = self.selected_script.findData(last_selected_script)
                if index >= 0:
                    self.selected_script.setCurrentIndex(index)
            else:
                if self.selected_script.count() > 0:
                    self.selected_script.setCurrentIndex(0)

            self.logger.info(tr("Автоматический запуск с последним конфигом активирован. Запуск процесса..."))
            self.run_exe(auto_run=True)
            self.hide()
            self.tray_icon.show()
            self.tray_icon.showMessage(
                tr("DPI Penguin by Zhivem"),
                tr("Приложение запущено с последней выбранной конфигурацией"),
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        else:
            self.show()

    def ensure_logs_folder_exists(self):
        logs_folder = os.path.join(BASE_FOLDER, "logs")
        if not os.path.exists(logs_folder):
            try:
                os.makedirs(logs_folder)
                self.logger.info(f"{tr('Создана папка logs')}: {logs_folder}")
            except Exception as e:
                self.logger.error(f"{tr('Не удалось создать папку logs')}: {e}", exc_info=True)

    def init_ui(self):
        self.setWindowTitle(tr("DPI Penguin v{version}").format(version=CURRENT_VERSION))
        self.setFixedSize(420, 570)
        self.set_window_icon(TRAY_ICON_PATH)

        saved_theme = settings.value("theme", "light")
        utils.theme_utils.apply_theme(self, saved_theme, settings, BASE_FOLDER)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        tab_widget = self.create_tabs()
        layout.addWidget(tab_widget)

    def set_window_icon(self, icon_path):
        if not os.path.exists(icon_path):
            self.logger.error(f"{tr('Файл иконки приложения не найден')}: {icon_path}")
        self.setWindowIcon(QIcon(icon_path))

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(TRAY_ICON_PATH))

        tray_menu = QMenu()

        restore_action = QAction(tr("Развернуть"), self)
        restore_action.triggered.connect(self.restore_from_tray)
        tray_menu.addAction(restore_action)

        quit_action = QAction(tr("Выход"), self)
        quit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def closeEvent(self, event):
        if self.minimize_to_tray:
            event.ignore()
            self.hide()
            self.tray_icon.show()
            self.tray_icon.showMessage(
                tr("DPI Penguin by Zhivem"),
                tr("Приложение свернуто в трей. Для восстановления, нажмите на иконку в трее"),
                QSystemTrayIcon.MessageIcon.Information,
                1000
            )
        else:
            self.stop_and_close()
            event.accept()

    def restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.tray_icon.hide()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isHidden():
                self.restore_from_tray()
            else:
                self.hide()

    def exit_app(self):
        self.stop_and_close()
        self.tray_icon.hide()
        QtWidgets.QApplication.quit()

    def create_tabs(self):
        tab_widget = QtWidgets.QTabWidget(self)
        tab_widget.addTab(self.create_process_tab(), tr("Основное"))
        tab_widget.addTab(self.create_settings_tab(), tr("Настройки"))
        tab_widget.addTab(self.create_info_tab(), tr("О программе"))
        return tab_widget

    def create_process_tab(self):
        process_tab = QtWidgets.QWidget()
        process_layout = QtWidgets.QVBoxLayout(process_tab)

        script_layout = QtWidgets.QHBoxLayout()

        self.selected_script = QFComboBox()
        if not self.config_error:
            for script_name in self.script_options.keys():
                translated_name = tr(script_name)
                self.selected_script.addItem(translated_name, userData=script_name)
        self.selected_script.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        script_layout.addWidget(self.selected_script)

        self.update_config_button = PushButton("📁", self)
        self.update_config_button.setToolTip(tr("Загрузить другую конфигурацию"))
        self.update_config_button.clicked.connect(self.load_config_via_dialog)
        self.update_config_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.update_config_button.setFixedWidth(40)
        script_layout.addWidget(self.update_config_button)

        script_layout.setStretch(0, 1)
        script_layout.setStretch(1, 0)

        process_layout.addLayout(script_layout)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.run_button = self.create_button(tr("Запустить"), self.run_exe, buttons_layout)
        self.stop_close_button = self.create_button(
            tr("Остановить и закрыть"),
            self.stop_and_close,
            buttons_layout,
            enabled=False
        )
        process_layout.addLayout(buttons_layout)

        self.console_output = TextEdit(self)
        self.console_output.setReadOnly(True)
        process_layout.addWidget(self.console_output)

        log_and_config_layout = QtWidgets.QHBoxLayout()

        self.open_logs_button = self.create_button(
            text=tr("Открыть папку Log"),
            func=lambda: self.handle_open_path(os.path.join(BASE_FOLDER, "logs")),
            layout=log_and_config_layout,
            icon_path=LOG_ICON_PATH,
            icon_size=(16, 16),
        )

        self.open_config_button = self.create_button(
            text=tr("Открыть configs"),
            func=lambda: self.handle_open_path(os.path.join(BASE_FOLDER, "config")),
            layout=log_and_config_layout,
            icon_path=INI_ICON_PATH,
            icon_size=(16, 16),
        )

        process_layout.addLayout(log_and_config_layout)

        self.theme_toggle_button = PushButton()
        utils.theme_utils.update_theme_button_text(self, settings)
        self.set_button_icon(self.theme_toggle_button, THEME_ICON_PATH, (16, 16))
        self.theme_toggle_button.clicked.connect(self.toggle_theme_button_clicked)
        process_layout.addWidget(self.theme_toggle_button)

        return process_tab

    def handle_open_path(self, path: str):
        error = open_path(path)
        if error:
            QMessageBox.warning(self, tr("Ошибка"), error)

    def set_button_icon(self, button, icon_path, icon_size):
        if not os.path.exists(icon_path):
            self.logger.error(f"{tr('Файл иконки приложения не найден')}: {icon_path}")
        else:
            icon = QIcon(icon_path)
            button.setIcon(icon)
            button.setIconSize(QtCore.QSize(*icon_size))

    def toggle_theme_button_clicked(self):
        utils.theme_utils.toggle_theme(self, settings, BASE_FOLDER)

    def create_settings_tab(self):
        settings_tab = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_tab)

        self.language_group = QGroupBox(tr("Язык / Language"))
        language_layout = QtWidgets.QVBoxLayout()
        self.language_group.setLayout(language_layout)

        self.language_combo = QFComboBox()
        for lang_code in translation_manager.available_languages:
            lang_name = translation_manager.language_names.get(lang_code, lang_code)
            self.language_combo.addItem(lang_name, userData=lang_code)

        current_lang_code = translation_manager.current_language
        current_index = self.language_combo.findData(current_lang_code)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)

        self.language_combo.currentIndexChanged.connect(self.change_language)
        language_layout.addWidget(self.language_combo)
        settings_layout.addWidget(self.language_group)

        self.autostart_group = QGroupBox(tr("Автозапуск"))
        autostart_layout = QtWidgets.QVBoxLayout()
        self.autostart_group.setLayout(autostart_layout)

        self.tray_checkbox = QCheckBox(tr("Сворачивать в трей при закрытии приложения"))
        self.tray_checkbox.setChecked(self.minimize_to_tray)
        self.tray_checkbox.toggled.connect(self.toggle_tray_behavior)
        autostart_layout.addWidget(self.tray_checkbox)

        self.autostart_checkbox = QCheckBox(tr("Запускать программу при старте системы"))
        self.autostart_checkbox.setChecked(self.autostart_enabled)
        self.autostart_checkbox.toggled.connect(self.toggle_autostart)
        autostart_layout.addWidget(self.autostart_checkbox)

        self.autorun_with_last_config_checkbox = QCheckBox(tr("Запускать в тихом режиме"))
        self.autorun_with_last_config_checkbox.setChecked(self.autorun_with_last_config)
        self.autorun_with_last_config_checkbox.toggled.connect(self.toggle_autorun_with_last_config)
        autostart_layout.addWidget(self.autorun_with_last_config_checkbox)

        # Добавляем чекбокс "Обновлять черные списки при запуске программы" в группу "Автозапуск"
        self.update_blacklists_on_start_checkbox = QCheckBox(tr("Проверять обновления черных списков при запуске"))
        self.update_blacklists_on_start_checkbox.setChecked(settings.value("update_blacklists_on_start", False, type=bool))
        self.update_blacklists_on_start_checkbox.toggled.connect(self.toggle_update_blacklists_on_start)
        autostart_layout.addWidget(self.update_blacklists_on_start_checkbox)

        font = self.tray_checkbox.font()
        font.setPointSize(9)
        self.tray_checkbox.setFont(font)
        self.autostart_checkbox.setFont(font)
        self.autorun_with_last_config_checkbox.setFont(font)
        self.update_blacklists_on_start_checkbox.setFont(font)

        settings_layout.addWidget(self.autostart_group)

        self.services_group = QGroupBox(tr("Службы"))
        services_layout = QtWidgets.QVBoxLayout()
        self.services_group.setLayout(services_layout)

        self.create_service_button = self.create_button(tr("Создать службу"), self.handle_create_service, services_layout)
        self.delete_service_button = self.create_button(tr("Удалить службу"), self.handle_delete_service, services_layout)

        services_layout.addWidget(self.create_service_button)
        services_layout.addWidget(self.delete_service_button)

        settings_layout.addWidget(self.services_group)

        self.updates_group = QGroupBox(tr("Обновления"))
        updates_layout = QtWidgets.QVBoxLayout()
        self.updates_group.setLayout(updates_layout)

        self.open_additional_settings_button = self.create_button(
            text=tr("Менеджер загрузок"),
            func=self.open_settings_dialog,
            layout=updates_layout,
            icon_path=MANAGER_ICON_PATH,
            icon_size=(18, 18)
        )

        # Кнопка "Обновить черные списки"
        self.update_blacklists_button = self.create_button(
            text=tr("Обновить черные списки"),
            func=lambda: self.update_blacklists(silent=False),
            layout=updates_layout
        )

        updates_layout.addWidget(self.open_additional_settings_button)
        updates_layout.addWidget(self.update_blacklists_button)

        settings_layout.addWidget(self.updates_group)

        settings_layout.addStretch(1)

        return settings_tab

    def change_language(self):
        lang_code = self.language_combo.currentData()
        set_language(lang_code)
        settings.setValue("language", lang_code)
        self.update_ui_texts()

    def update_ui_texts(self):
        self.setWindowTitle(tr("DPI Penguin v{version}").format(version=CURRENT_VERSION))
        tab_widget = self.centralWidget().layout().itemAt(0).widget()
        tab_widget.setTabText(0, tr("Основное"))
        tab_widget.setTabText(1, tr("Настройки"))
        tab_widget.setTabText(2, tr("О программе"))

        self.run_button.setText(tr("Запустить"))
        self.stop_close_button.setText(tr("Остановить и закрыть"))
        self.update_config_button.setToolTip(tr("Загрузить другую конфигурацию"))
        self.open_logs_button.setText(tr("Открыть папку Log"))
        self.open_config_button.setText(tr("Открыть configs"))
        utils.theme_utils.update_theme_button_text(self, settings)

        self.tray_checkbox.setText(tr("Сворачивать в трей при закрытии приложения"))
        self.autostart_checkbox.setText(tr("Запускать программу при старте системы"))
        self.autorun_with_last_config_checkbox.setText(tr("Запускать в тихом режиме"))
        self.update_blacklists_on_start_checkbox.setText(tr("Проверять обновления черных списков при запуске"))
        self.create_service_button.setText(tr("Создать службу"))
        self.delete_service_button.setText(tr("Удалить службу"))
        self.open_additional_settings_button.setText(tr("Менеджер загрузок"))
        self.update_blacklists_button.setText(tr("Обновить черные списки"))

        self.language_group.setTitle(tr("Язык / Language"))
        self.autostart_group.setTitle(tr("Автозапуск"))
        self.services_group.setTitle(tr("Службы"))
        self.updates_group.setTitle(tr("Обновления"))

        for index in range(self.language_combo.count()):
            lang_code = self.language_combo.itemData(index)
            lang_name = translation_manager.language_names.get(lang_code, lang_code)
            self.language_combo.setItemText(index, lang_name)

        self.details_group.setTitle(tr("Подробности"))
        self.acknowledgements_group.setTitle(tr("Зависимости"))
        self.update_info_tab_texts()

        self.update_script_options_display()

    def update_script_options_display(self):
        current_data = self.selected_script.currentData()
        self.selected_script.clear()
        for script_name in self.script_options.keys():
            translated_name = tr(script_name)
            self.selected_script.addItem(translated_name, userData=script_name)
        if current_data:
            index = self.selected_script.findData(current_data)
            if index >= 0:
                self.selected_script.setCurrentIndex(index)

    def create_info_tab(self):
        info_tab = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(info_tab)

        self.details_group = self.create_details_group()
        info_layout.addWidget(self.details_group)

        self.acknowledgements_group = self.create_acknowledgements_group()
        info_layout.addWidget(self.acknowledgements_group)

        info_layout.addStretch(1)
        return info_tab

    def update_info_tab_texts(self):
        self.details_group.setTitle(tr("Подробности"))
        self.acknowledgements_group.setTitle(tr("Зависимости"))

    def create_details_group(self):
        group = QGroupBox(tr("Подробности"))
        layout = QtWidgets.QGridLayout(group)

        labels = {
            tr("Версия"): f"{CURRENT_VERSION}",
            tr("Разработчик"): "Zhivem",
            tr("Репозиторий на GitHub"): f"<a href='https://github.com/zhivem/DPI-Penguin'>{tr('DPI Penguin')}</a>",
            tr("Релизы"): f"<a href='https://github.com/zhivem/DPI-Penguin/releases'>{tr('Релизы')}</a>",
            tr("Лицензия"): tr("© 2024 Zhivem. Лицензия: Apache")
        }

        widgets = {
            tr("Версия"): QtWidgets.QLabel(labels[tr("Версия")]),
            tr("Разработчик"): QtWidgets.QLabel(labels[tr("Разработчик")]),
            tr("Репозиторий на GitHub"): QtWidgets.QLabel(labels[tr("Репозиторий на GitHub")]),
            tr("Релизы"): QtWidgets.QLabel(labels[tr("Релизы")]),
            tr("Лицензия"): QtWidgets.QLabel(labels[tr("Лицензия")])
        }

        for row, (key, widget) in enumerate(widgets.items()):
            if key in [tr("Репозиторий на GitHub"), tr("Релизы")]:
                widget.setOpenExternalLinks(True)
            layout.addWidget(QtWidgets.QLabel(key), row, 0)
            layout.addWidget(widget, row, 1)

        return group

    def create_acknowledgements_group(self):
        group = QGroupBox(tr("Зависимости"))
        layout = QtWidgets.QVBoxLayout(group)

        dependencies = [
            {
                "title": "Discord Fix [howdyho]",
                "description": tr("Конфигурации"),
                "version": "5.8",
                "developer": "Абрахам",
                "links": [
                    "https://howdyho.net",
                    "https://vk.com/howdyho_net"
                ]
            },
            {
                "title": "Zapret",
                "description": tr("Основа для работы Discord и YouTube"),
                "version": "67",
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

        layout.addWidget(QtWidgets.QLabel(f"<b>{title}</b>"), 0, 0, 1, 2)
        layout.addWidget(QtWidgets.QLabel(f"{tr('Описание')}: {description}"), 1, 0, 1, 2)
        layout.addWidget(QtWidgets.QLabel(f"{tr('Версия')}: {version}"), 2, 0)
        layout.addWidget(QtWidgets.QLabel(f"{tr('Разработчик')}: {developer}"), 2, 1)

        for i, link in enumerate(links, start=3):
            link_label = QtWidgets.QLabel(f"<a href='{link}'>{link}</a>")
            link_label.setOpenExternalLinks(True)
            layout.addWidget(link_label, i, 0, 1, 2)

        return section

    def toggle_tray_behavior(self, checked):
        self.minimize_to_tray = checked
        settings.setValue("minimize_to_tray", self.minimize_to_tray)

        if not checked and self.tray_icon.isVisible():
            self.tray_icon.hide()

    def toggle_autostart(self, checked):
        if checked:
            enable_autostart()
            self.logger.info(tr("Автозапуск включен"))
        else:
            disable_autostart()
            self.logger.info(tr("Автозапуск отключен"))

    def toggle_autorun_with_last_config(self, checked):
        self.autorun_with_last_config = checked
        settings.setValue("autorun_with_last_config", self.autorun_with_last_config)
        self.logger.info(f"{tr('Автозапуск с последним конфигом')} {'включен' if checked else 'отключен'}")
        if checked:
            settings.setValue("last_config_path", self.current_config_path)

    def toggle_update_blacklists_on_start(self, checked):
        settings.setValue("update_blacklists_on_start", checked)
        self.logger.info(f"{tr('Обновление черных списков при запуске программы')} {'включено' if checked else 'отключено'}")

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
        QMessageBox.information(self, tr("Создание службы"), result)

    def handle_delete_service(self):
        result = delete_service()
        QMessageBox.information(self, tr("Удаление службы"), result)

    def run_exe(self, auto_run=False):
        if self.config_error:
            self.console_output.append(tr("Не удалось загрузить конфигурацию из-за ошибок"))
            self.logger.error(tr("Не удалось загрузить конфигурацию из-за ошибок"))
            return

        selected_option = self.selected_script.currentData()
        if selected_option not in self.script_options:
            error_msg = tr("Ошибка: неизвестный вариант скрипта {option}.").format(option=selected_option)
            self.console_output.append(error_msg)
            self.logger.error(error_msg)
            return

        settings.setValue("last_selected_script", selected_option)

        executable, args = self.script_options[selected_option]

        if not self.is_executable_available(executable, selected_option):
            return

        translated_option = tr(selected_option)
        clear_console_text = tr("Установка: {option} запущена...").format(option=translated_option)

        command = [executable] + args
        self.logger.debug(f"{tr('Команда для запуска')}: {command}")

        try:
            capture_output = selected_option not in [
                "Обход блокировки YouTube",
                "Обход Discord + YouTube",
                "Обход блокировки Discord",
                "Обход блокировок для ЧС РКН"
            ]
            self.start_process(
                command,
                selected_option,
                disable_run=True,
                clear_console_text=clear_console_text,
                capture_output=capture_output
            )
            self.logger.info(f"{tr('Процесс')} '{selected_option}' {tr('запущен')}")
        except Exception as e:
            error_msg = f"{tr('Ошибка запуска процесса')}: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.console_output.append(error_msg)

        if auto_run:
            settings.setValue("last_config_path", self.current_config_path)

    def is_executable_available(self, executable, selected_option):
        if not os.path.exists(executable):
            error_msg = f"{tr('Файл')} {executable} {tr('не найден')}"
            self.logger.error(error_msg)
            self.console_output.append(f"{tr('Ошибка')}: {tr('файл')} {executable} {tr('не найден')}")
            return False

        if not os.access(executable, os.X_OK):
            error_msg = f"{tr('Недостаточно прав для запуска')} {executable}."
            self.logger.error(error_msg)
            self.console_output.append(f"{tr('Ошибка')}: {tr('Недостаточно прав для запуска')} {executable}")
            return False

        if selected_option in [
            "Обход блокировки YouTube",
            "Обход Discord + YouTube",
            "Обход блокировки Discord",
            "Обход блокировок для ЧС РКН"
        ]:
            required_files = [
                os.path.join(BASE_FOLDER, "black"),
                os.path.join(BASE_FOLDER, "zapret", "quic_initial_www_google_com.bin"),
                os.path.join(BASE_FOLDER, "zapret", "tls_clienthello_www_google_com.bin"),
                os.path.join(BASE_FOLDER, "zapret", "tls_clienthello_iana_org.bin")
            ]
            missing_files = [f for f in required_files if not os.path.exists(f)]
            if missing_files:
                error_msg = f"{tr('Не найдены необходимые файлы')}: {', '.join(missing_files)}"
                self.logger.error(error_msg)
                self.console_output.append(f"{tr('Ошибка')}: {tr('не найдены файлы')}: {', '.join(missing_files)}")
                return False

        self.logger.debug(f"{tr('Исполняемый файл')} {executable} {tr('доступен для запуска')}")
        return True

    def start_process(self, command, process_name, disable_run=False, clear_console_text=None, capture_output=True):
        if clear_console_text:
            self.clear_console(clear_console_text)

        try:
            if self.worker_thread is not None:
                self.worker_thread.terminate_process()
                self.worker_thread.quit()
                self.worker_thread.wait()
                self.worker_thread = None

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
            error_msg = f"{tr('Ошибка при запуске потока')}: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.console_output.append(error_msg)

    def update_output(self, text):
        ignore_keywords = [
            "loading hostlist",
            "we have",
            "desync profile(s)",
            "loaded hosts",
            "loading plain text list",
            "loaded",
            "loading ipset"
        ]

        text_lower = text.lower()

        if "windivert initialized. capture is started." in text_lower:
            self.console_output.append(tr("Ваша конфигурация выполняется"))
        elif any(keyword in text_lower for keyword in ignore_keywords):
            return
        else:
            self.console_output.append(text)

        max_lines = 100
        document = self.console_output.document()
        while document.blockCount() > max_lines:
            cursor = self.console_output.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
            cursor.select(QtGui.QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    @pyqtSlot(str)
    def on_finished(self, process_name):
        if process_name in self.script_options:
            self.run_button.setEnabled(True)
            self.stop_close_button.setEnabled(False)
            self.logger.info(f"{tr('Процесс')} {process_name} {tr('завершён')}")
            self.console_output.append(tr("Обход блокировки завершен"))

            if self.worker_thread:
                try:
                    self.worker_thread.output_signal.disconnect(self.update_output)
                except TypeError:
                    pass
                try:
                    self.worker_thread.finished_signal.disconnect(self.on_finished)
                except TypeError:
                    pass

            self.worker_thread = None

    def stop_and_close(self):
        self.logger.info(tr("Начата процедура остановки и закрытия процессов"))

        if self.worker_thread is not None:
            self.logger.info(tr("Завершение работы WorkerThread"))
            self.worker_thread.terminate_process()
            self.worker_thread.quit()
            if not self.worker_thread.wait(5000):
                self.logger.warning(tr("WorkerThread не завершился в течение 5 секунд. Принудительно завершаем"))
                self.worker_thread.terminate()
                self.worker_thread.wait()
            self.worker_thread = None

        self.start_process(
            WIN_DIVERT_COMMAND,
            "WinDivert",
            capture_output=False
        )
        self.close_process("winws.exe", "winws.exe")

    def close_process(self, process_name, display_name):
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    psutil.Process(proc.info['pid']).terminate()
                    self.console_output.append(tr("Обход остановлен"))
                    self.logger.debug(f"{tr('Процесс')} {display_name} (PID: {proc.info['pid']}) {tr('завершён')}")
        except psutil.NoSuchProcess:
            self.logger.warning(f"{tr('Процесс')} {display_name} {tr('не найден.')}")
        except psutil.AccessDenied:
            error_msg = f"{tr('Недостаточно прав для завершения процесса')} {display_name}"
            self.logger.error(error_msg)
            self.console_output.append(f"{tr('Ошибка')}: {tr('Недостаточно прав для завершения процесса')} {display_name}")
        except Exception as e:
            error_msg = f"{tr('Ошибка завершения процесса')} {display_name}: {str(e)}"
            self.console_output.append(error_msg)
            self.logger.error(error_msg)

    def clear_console(self, initial_text=""):
        self.console_output.clear()
        if initial_text:
            self.console_output.append(initial_text)

    def load_config_via_dialog(self):
        dialog = QFileDialog(self)
        dialog.setOption(QFileDialog.Option.ReadOnly, True)

        file_path, _ = dialog.getOpenFileName(
            self,
            tr("Выберите файл конфигурации"),
            "",
            "INI Files (*.ini)"
        )

        if file_path:
            self.logger.info(f"{tr('Выбран файл конфигурации')}: {file_path}")

            if self.worker_thread is not None:
                self.logger.info(tr("Завершение работы WorkerThread перед загрузкой новой конфигурации"))
                self.worker_thread.terminate_process()
                self.worker_thread.quit()
                self.worker_thread.wait()
                self.worker_thread = None

            validation_error = self.validate_config_file(file_path)
            if validation_error:
                self.console_output.append(validation_error)
                self.logger.error(validation_error)
                QMessageBox.critical(self, tr("Ошибка загрузки конфигурации"), validation_error)
                return

            new_script_options, new_config_error = load_script_options(file_path)

            if new_config_error:
                self.console_output.append(new_config_error)
                self.logger.error(new_config_error)
                QMessageBox.critical(self, tr("Ошибка загрузки конфигурации"), new_config_error)
                return

            self.script_options = new_script_options
            self.config_error = None
            self.current_config_path = file_path
            self.console_output.append(tr("Конфигурация успешно загружена"))
            self.logger.info(tr("Конфигурация успешно загружена"))

            self.update_script_options_display()
            self.selected_script.setEnabled(True)
            self.run_button.setEnabled(True)
            self.stop_close_button.setEnabled(False)

            if self.autorun_with_last_config:
                settings.setValue("last_config_path", file_path)

    def validate_config_file(self, file_path):
        if not os.path.exists(file_path):
            error_msg = f"{tr('Файл не найден')}: {file_path}"
            self.logger.error(error_msg)
            return error_msg

        if not os.access(file_path, os.R_OK):
            error_msg = f"{tr('Недостаточно прав для чтения файла')}: {file_path}"
            self.logger.error(error_msg)
            return error_msg

        config = configparser.ConfigParser()
        try:
            config.read(file_path, encoding='utf-8')
        except Exception as e:
            error_msg = f"{tr('Ошибка при чтении файла INI')}: {e}"
            self.logger.error(error_msg)
            return error_msg

        if 'SCRIPT_OPTIONS' not in config.sections():
            error_msg = tr("Ошибка: Отсутствует секция [SCRIPT_OPTIONS] в конфигурационном файле")
            self.logger.error(error_msg)
            return error_msg

        script_sections = [section for section in config.sections() if section != 'SCRIPT_OPTIONS']
        if not script_sections:
            error_msg = tr("Ошибка: В секции [SCRIPT_OPTIONS] отсутствуют настройки скриптов")
            self.logger.error(error_msg)
            return error_msg

        required_keys = ['executable', 'args']
        for section in script_sections:
            for key in required_keys:
                if key not in config[section]:
                    error_msg = f"{tr('Ошибка')}: {tr('В секции')} [{section}] {tr('отсутствует ключ')} '{key}'"
                    self.logger.error(error_msg)
                    return error_msg

        return None

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.config_updated_signal.connect(self.reload_configuration)
        dialog.exec()

    def reload_configuration(self):
        self.logger.info(tr("Перезагрузка конфигурации после обновления default.ini"))
        # Перезагружаем опции скрипта
        self.script_options, self.config_error = load_script_options(self.current_config_path)
        if self.config_error:
            self.console_output.append(self.config_error)
            self.logger.error(self.config_error)
            self.selected_script.setEnabled(False)
            self.run_button.setEnabled(False)
        else:
            self.update_script_options_display()
            self.selected_script.setEnabled(True)
            self.run_button.setEnabled(True)
        # Отображаем сообщение пользователю
        QMessageBox.information(self, tr("Обновление"), tr("Конфигурация обновлена и перезагружена"))

    def check_updates(self):
        self.logger.info(tr("Проверка обновлений..."))
        update_checker = UpdateChecker()
        update_checker.get_local_versions()
        update_checker.get_remote_versions()

        updates_available = False

        # Проверка обновления программы
        if update_checker.is_update_available('ver_programm'):
            updates_available = True

        # Проверка обновления zapret
        if update_checker.is_update_available('zapret'):
            updates_available = True

        # Проверка обновления config (default.ini)
        if update_checker.is_update_available('config'):
            updates_available = True

        if updates_available:
            QMessageBox.information(
                self,
                tr("Обновление"),
                tr("Доступны новые обновления. Рекомендуется обновить"),
                QMessageBox.StandardButton.Ok
            )
            self.open_settings_dialog()
        else:
            self.logger.info(tr("Все компоненты обновлены до последней версии."))

    def update_blacklists(self, silent=False):
        """
        Обновляет черные списки.
        Если silent=True, то не показывает сообщения и не открывает окна.
        """
        update_checker = UpdateChecker()
        success = update_checker.update_blacklists()
        if success:
            if not silent:
                QMessageBox.information(self, tr("Обновление"), tr("Черные списки успешно обновлены"))
            self.logger.info(tr("Черные списки успешно обновлены"))
        else:
            if not silent:
                QMessageBox.warning(self, tr("Обновление"), tr("Произошли ошибки при обновлении черных списков. Проверьте логи для подробностей."))
            self.logger.warning(tr("Произошли ошибки при обновлении черных списков"))
