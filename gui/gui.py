import configparser
import logging
import os
from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot, QTimer
from PyQt6.QtGui import QAction, QIcon, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QWidget,
    QGridLayout,
)

from qfluentwidgets import ComboBox as QFComboBox, PushButton, TextEdit, FluentIcon

from utils.update_utils import UpdateChecker
from utils.utils import (
    BASE_FOLDER,
    CURRENT_VERSION,
    ZAPRET_FOLDER,
    CONFIG_VERSION,
    ZAPRET_VERSION,
    settings,
    translation_manager,
    create_service,
    delete_service,
    disable_autostart,
    start_fix_process,
    enable_autostart,
    is_autostart_enabled,
    load_script_options,
    open_path,
    set_language,
    tr,
)
import utils.theme_utils

from gui.updater_manager import SettingsDialog
from gui.proxy_window import ProxySettingsDialog
from gui.converter import ConfigConverterDialog

from utils.process_utils import WorkerThread
from utils.service_utils import stop_service

# Путь к иконке приложения
TRAY_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "newicon.ico")

logger = logging.getLogger("dpipenguin")

class UpdateBlacklistsThread(QtCore.QThread):
    def __init__(self, parent=None, silent=False):
        super().__init__(parent)
        self.silent = silent
        self.success = False

    def run(self):
        update_checker = UpdateChecker()
        self.success = update_checker.update_blacklists()

class CheckUpdatesThread(QtCore.QThread):
    updates_available_signal = QtCore.pyqtSignal(bool)

    def run(self):
        update_checker = UpdateChecker()
        update_checker.get_local_versions()
        update_checker.get_remote_versions()
        updates_available = any([
            update_checker.is_update_available('ver_programm'),
            update_checker.is_update_available('zapret'),
            update_checker.is_update_available('config')
        ])
        self.updates_available_signal.emit(updates_available)

class DPIPenguin(QtWidgets.QMainWindow):
    """
    Главное окно приложения DPI Penguin.
    """

    def __init__(self):
        super().__init__()
        self.logger = logger

        # Инициализация базовых настроек
        self.minimize_to_tray = settings.value("minimize_to_tray", True, type=bool)
        self.autostart_enabled = is_autostart_enabled()
        self.autorun_with_last_config = settings.value("autorun_with_last_config", False, type=bool)

        # Инициализация параметров конфигурации
        if self.autorun_with_last_config:
            last_config_path = settings.value(
                "last_config_path",
                os.path.join(BASE_FOLDER, "config", "default.ini"),
            )
            self.script_options, self.config_error = load_script_options(last_config_path)
            self.current_config_path = last_config_path
        else:
            default_config_path = os.path.join(BASE_FOLDER, "config", "default.ini")
            self.script_options, self.config_error = load_script_options(default_config_path)
            self.current_config_path = default_config_path

        self.main_worker_thread: Optional[WorkerThread] = None
        self.winws_worker_thread: Optional[WorkerThread] = None

        # Инициализация интерфейса и трей-иконки
        self.init_ui()
        self.init_tray_icon()

        # Обработка ошибок конфигурации
        if self.config_error:
            self.console_output.append(self.config_error)
            self.logger.error(self.config_error)
            self.selected_script.setEnabled(False)
            self.run_button.setEnabled(False)
            self.stop_close_button.setEnabled(False)
            self.update_config_button.setEnabled(True)

        # Запуск дополнительных задач
        if settings.value("update_blacklists_on_start", False, type=bool):
            self.start_update_blacklists_thread(silent=True)

        self.start_check_updates_thread()

        # Автозапуск или показ окна
        if self.autorun_with_last_config and not self.config_error:
            QTimer.singleShot(0, self.run_autorun)
        else:
            self.show()

    def start_update_blacklists_thread(self, silent=False):
        self.update_blacklists_thread = UpdateBlacklistsThread(silent=silent)
        self.update_blacklists_thread.finished.connect(self.on_update_blacklists_finished)
        self.update_blacklists_thread.start()

    def on_update_blacklists_finished(self):
        success = self.update_blacklists_thread.success
        if not self.update_blacklists_thread.silent:
            if success:
                QMessageBox.information(self, tr("Обновление"), tr("Черные списки успешно обновлены"))
            else:
                QMessageBox.warning(self, tr("Обновление"), tr("Произошли ошибки при обновлении черных списков. Проверьте логи для подробностей."))
        if not success:
            self.logger.warning(tr("Произошли ошибки при обновлении черных списков"))

    def start_check_updates_thread(self):
        self.check_updates_thread = CheckUpdatesThread()
        self.check_updates_thread.updates_available_signal.connect(self.on_updates_checked)
        self.check_updates_thread.start()

    def on_updates_checked(self, updates_available):
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

    def run_autorun(self) -> None:
        """
        Выполняет автоматический запуск с последней выбранной конфигурацией.
        """
        last_selected_script = settings.value("last_selected_script", None)
        if last_selected_script and last_selected_script in self.script_options:
            index = self.selected_script.findData(last_selected_script)
            if index >= 0:
                self.selected_script.setCurrentIndex(index)
        else:
            if self.selected_script.count() > 0:
                self.selected_script.setCurrentIndex(0)

        self.run_exe(auto_run=True)
        self.hide()
        self.tray_icon.show()
        self.tray_icon.showMessage(
            tr("DPI Penguin by Zhivem"),
            tr("Приложение запущено с последней выбранной конфигурацией"),
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def init_ui(self) -> None:
        """
        Инициализирует пользовательский интерфейс главного окна.
        """
        self.setWindowTitle("DPI Penguin v{version}".format(version=CURRENT_VERSION))
        self.setFixedSize(420, 570)
        self.set_window_icon(TRAY_ICON_PATH)

        saved_theme = settings.value("theme", "light")
        utils.theme_utils.apply_theme(self, saved_theme, settings, BASE_FOLDER)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        tab_widget = self.create_tabs()
        layout.addWidget(tab_widget)

    def set_window_icon(self, icon_path: str) -> None:
        """
        Устанавливает иконку окна приложения.
        """
        if not os.path.exists(icon_path):
            self.logger.error(f"{tr('Файл иконки приложения не найден')}: {icon_path}")
        else:
            self.setWindowIcon(QIcon(icon_path))

    def init_tray_icon(self) -> None:
        """
        Инициализирует иконку в системном трее с контекстным меню.
        """
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

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        Обработчик события закрытия окна.
        """
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

    def restore_from_tray(self) -> None:
        """
        Восстанавливает окно приложения из трея.
        """
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.tray_icon.hide()

    def on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        Обработчик активации иконки в трее.
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isHidden():
                self.restore_from_tray()
            else:
                self.hide()

    def exit_app(self) -> None:
        """
        Завершает работу приложения.
        """
        self.stop_and_close()
        self.tray_icon.hide()
        QtWidgets.QApplication.quit()

    def create_tabs(self) -> QTabWidget:
        """
        Создаёт вкладки в главном окне.
        """
        tab_widget = QTabWidget(self)
        tab_widget.addTab(self.create_process_tab(), tr("Основное"))
        tab_widget.addTab(self.create_settings_tab(), tr("Настройки"))
        tab_widget.addTab(self.create_info_tab(), tr("О программе"))
        return tab_widget

    def create_process_tab(self) -> QWidget:
        """
        Создаёт вкладку "Основное" с элементами управления процессами.
        """
        process_tab = QWidget()
        process_layout = QVBoxLayout(process_tab)
        script_layout = QHBoxLayout()

        self.selected_script = QFComboBox()
        if not self.config_error:
            for script_name in self.script_options.keys():
                translated_name = tr(script_name)
                self.selected_script.addItem(translated_name, userData=script_name)
        self.selected_script.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        script_layout.addWidget(self.selected_script)

        self.update_config_button = self.create_button(
            text="...",
            func=self.load_config_via_dialog,
            layout=script_layout,
            icon=FluentIcon.FOLDER,
            icon_size=(16, 16),
            tooltip=tr("Загрузить другую конфигурацию")
        )

        self.converter_button = self.create_button(
            text="...",
            func=self.open_converter,
            layout=script_layout,
            icon=FluentIcon.EDIT,
            icon_size=(16, 16),
            tooltip=tr("Открыть окно конвертера")
        )

        script_layout.setStretch(0, 1)
        script_layout.setStretch(1, 0)
        script_layout.setStretch(2, 0)

        process_layout.addLayout(script_layout)

        buttons_layout = QHBoxLayout()
        self.run_button = self.create_button(tr("Запустить"), self.run_exe, buttons_layout)
        self.stop_close_button = self.create_button(
            tr("Остановить"),
            self.stop_and_close,
            buttons_layout,
            enabled=False
        )
        process_layout.addLayout(buttons_layout)

        self.console_output = TextEdit(self)
        self.console_output.setReadOnly(True)
        process_layout.addWidget(self.console_output)

        log_and_config_layout = QHBoxLayout()

        self.open_proxy_settings_button = self.create_button(
            text=tr("Прокси и DNS"),
            func=self.open_proxy_settings_dialog,
            layout=log_and_config_layout,
            icon=FluentIcon.GLOBE,
            icon_size=(16, 16),
        )

        self.open_config_button = self.create_button(
            text=tr("Открыть Configs"),
            func=lambda: self.handle_open_path(os.path.join(BASE_FOLDER, "config")),
            layout=log_and_config_layout,
            icon=FluentIcon.SETTING,
            icon_size=(16, 16),
        )

        process_layout.addLayout(log_and_config_layout)

        self.theme_toggle_button = PushButton()
        utils.theme_utils.update_theme_button_text(self, settings)
        self.set_button_icon(self.theme_toggle_button, FluentIcon.PALETTE, (16, 16))
        self.theme_toggle_button.clicked.connect(self.toggle_theme_button_clicked)
        process_layout.addWidget(self.theme_toggle_button)

        return process_tab

    def open_converter(self):
        self.converter_window = ConfigConverterDialog(self)
        self.converter_window.show()

    def handle_open_path(self, path: str) -> None:
        """
        Открывает заданную папку или файл в проводнике.
        """
        error = open_path(path)
        if error:
            QMessageBox.warning(self, tr("Ошибка"), error)

    def set_button_icon(self, button: PushButton, icon: FluentIcon, icon_size: tuple) -> None:
        """
        Устанавливает иконку FluentIcon на кнопку.
        """
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(*icon_size))

    def toggle_theme_button_clicked(self) -> None:
        """
        Обработчик нажатия кнопки переключения темы.
        """
        utils.theme_utils.toggle_theme(self, settings, BASE_FOLDER)

    def create_settings_tab(self) -> QWidget:
        """
        Создаёт вкладку "Настройки" с различными настройками приложения.
        """
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)

        self.language_group = QGroupBox("Язык / Language")
        language_layout = QVBoxLayout()
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
        autostart_layout = QVBoxLayout()
        self.autostart_group.setLayout(autostart_layout)

        self.tray_checkbox = QCheckBox(tr("Сворачивать в трей при закрытии приложения"))
        self.tray_checkbox.setChecked(self.minimize_to_tray)
        self.tray_checkbox.toggled.connect(self.toggle_tray_behavior)
        autostart_layout.addWidget(self.tray_checkbox)

        self.autostart_checkbox = QCheckBox(tr("Запускать при старте Windows"))
        self.autostart_checkbox.setChecked(self.autostart_enabled)
        self.autostart_checkbox.toggled.connect(self.toggle_autostart)
        autostart_layout.addWidget(self.autostart_checkbox)

        self.autorun_with_last_config_checkbox = QCheckBox(tr("Запускать в тихом режиме"))
        self.autorun_with_last_config_checkbox.setChecked(self.autorun_with_last_config)
        self.autorun_with_last_config_checkbox.toggled.connect(self.toggle_autorun_with_last_config)
        autostart_layout.addWidget(self.autorun_with_last_config_checkbox)

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
        services_layout = QVBoxLayout()
        self.services_group.setLayout(services_layout)

        self.create_service_button = self.create_button(
            tr("Создать службу"),
            self.handle_create_service,
            services_layout,
            icon=FluentIcon.ADD,
            icon_size=(16, 16)
        )

        self.delete_service_button = self.create_button(
            tr("Удалить службу"),
            self.handle_delete_service,
            services_layout,
            icon=FluentIcon.DELETE,
            icon_size=(16, 16)
        )

        settings_layout.addWidget(self.services_group)

        self.updates_group = QGroupBox(tr("Обновления"))
        updates_layout = QVBoxLayout()
        self.updates_group.setLayout(updates_layout)

        self.open_additional_settings_button = self.create_button(
            text=tr("Менеджер обновлений"),
            func=self.open_settings_dialog,
            layout=updates_layout,
            icon=FluentIcon.UPDATE,
            icon_size=(16, 16)
        )

        self.update_blacklists_button = self.create_button(
            text=tr("Обновить черные списки"),
            func=lambda: self.start_update_blacklists_thread(silent=False),
            layout=updates_layout,
            icon=FluentIcon.SYNC,
            icon_size=(16, 16)
        )

        settings_layout.addWidget(self.updates_group)

        self.fix_group = QGroupBox(tr("Исправление"))
        fix_layout = QVBoxLayout()
        self.fix_group.setLayout(fix_layout)

        self.fix_button = self.create_button(
            text=tr("Исправить работу с процессом"),
            func=lambda: start_fix_process(self),
            layout=fix_layout,
            icon=FluentIcon.VPN,
            icon_size=(16, 16)
        )

        fix_layout.addWidget(self.fix_button)

        self.fix_info_label = QLabel(tr("Исправляет работу с запуском процесса обхода и службы WinDivert. Нажимать если кнопка «Запустить» не работает!"))
        self.fix_info_label.setWordWrap(True)
        fix_layout.addWidget(self.fix_info_label)

        settings_layout.addWidget(self.fix_group)
        settings_layout.addStretch(1)

        return settings_tab

    def change_language(self) -> None:
        """
        Обработчик изменения языка приложения.
        """
        lang_code = self.language_combo.currentData()
        set_language(lang_code)
        settings.setValue("language", lang_code)
        self.notify_restart_required()

    def notify_restart_required(self):
        """
        Отображает сообщение о необходимости перезапуска.
        """
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(tr("Перезапуск приложения"))
        msg_box.setText(tr("Изменения языка вступят в силу после перезапуска приложения"))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def update_script_options_display(self) -> None:
        """
        Обновляет список доступных скриптов в комбобоксе.
        """
        current_data = self.selected_script.currentData()
        self.selected_script.clear()
        for script_name in self.script_options.keys():
            translated_name = tr(script_name)
            self.selected_script.addItem(translated_name, userData=script_name)
        if current_data:
            index = self.selected_script.findData(current_data)
            if index >= 0:
                self.selected_script.setCurrentIndex(index)

    def create_info_tab(self) -> QWidget:
        """
        Создаёт вкладку "О программе".
        """
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)

        self.details_group = self.create_details_group()
        info_layout.addWidget(self.details_group)

        self.acknowledgements_group = self.create_acknowledgements_group()
        info_layout.addWidget(self.acknowledgements_group)

        info_layout.addStretch(1)
        return info_tab

    def update_info_tab_texts(self) -> None:
        """
        Обновляет тексты в вкладке "О программе".
        """
        self.details_group.setTitle(tr("Подробности"))
        self.acknowledgements_group.setTitle(tr("Зависимости"))

    def create_details_group(self) -> QGroupBox:
        """
        Создаёт группу с подробностями о приложении.
        """
        group = QGroupBox(tr("Подробности"))
        layout = QtWidgets.QGridLayout(group)

        labels = {
            tr("Версия"): f"{CURRENT_VERSION}",
            tr("Разработчик"): "Zhivem",
            tr("Репозиторий на GitHub"): f"<a href='https://github.com/zhivem/DPI-Penguin'>{tr('DPI Penguin')}</a>",
            tr("Релизы"): f"<a href='https://github.com/zhivem/DPI-Penguin/releases'>{tr('Все версии')}</a>",
            tr("Лицензия"): tr("© 2025 Zhivem. Лицензия: MIT license")
        }

        widgets = {
            tr("Версия"): QLabel(labels[tr("Версия")]),
            tr("Разработчик"): QLabel(labels[tr("Разработчик")]),
            tr("Репозиторий на GitHub"): QLabel(labels[tr("Репозиторий на GitHub")]),
            tr("Релизы"): QLabel(labels[tr("Релизы")]),
            tr("Лицензия"): QLabel(labels[tr("Лицензия")])
        }

        for row, (key, widget) in enumerate(widgets.items()):
            if key in [tr("Репозиторий на GitHub"), tr("Релизы")]:
                widget.setOpenExternalLinks(True)
            layout.addWidget(QLabel(key), row, 0)
            layout.addWidget(widget, row, 1)

        return group

    def create_acknowledgements_group(self) -> QGroupBox:
        """
        Создаёт группу с информацией о зависимостях.
        """
        group = QGroupBox(tr("Зависимости"))
        layout = QVBoxLayout(group)

        dependencies = [
            {
                "title": "Конфигурации",
                "description": tr("Версия основных конфигурационных файлов"),
                "version": f"{CONFIG_VERSION}",
                "developer": "Zhivem",
                "links": [
                    "https://github.com/zhivem",
                    "https://github.com/zhivem/DPI-Penguin"
                ]
            },
            {
                "title": "Zapret",
                "description": tr("Основа для работы Discord и YouTube"),
                "version": f"{ZAPRET_VERSION}",
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

        appdata_folder = os.environ.get('LOCALAPPDATA', os.path.expanduser("~\\AppData\\Local"))
        log_folder = os.path.join(appdata_folder, 'DPI-Penguin', 'logs')

        self.open_logs_button = self.create_button(
            text=tr("Открыть папку Log"),
            func=lambda: self.handle_open_path(log_folder),
            layout=layout,
            icon=FluentIcon.DOCUMENT,
            icon_size=(16, 16),
        )

        return group

    def create_acknowledgement_section(self, title: str, description: str, version: str, developer: str, links: List[str]) -> QWidget:
        """
        Создаёт секцию с информацией о зависимости.
        """
        section = QWidget()
        layout = QGridLayout(section)

        layout.addWidget(QLabel(f"<b>{title}</b>"), 0, 0, 1, 2)
        layout.addWidget(QLabel(f"{tr('Описание')}: {description}"), 1, 0, 1, 2)
        layout.addWidget(QLabel(f"{tr('Версия')}: {version}"), 2, 0)
        layout.addWidget(QLabel(f"{tr('Разработчик')}: {developer}"), 2, 1)

        for i, link in enumerate(links, start=3):
            link_label = QLabel(f"<a href='{link}'>{link}</a>")
            link_label.setOpenExternalLinks(True)
            layout.addWidget(link_label, i, 0, 1, 2)

        return section

    def toggle_tray_behavior(self, checked: bool) -> None:
        """
        Переключает поведение приложения при закрытии.
        """
        self.minimize_to_tray = checked
        settings.setValue("minimize_to_tray", self.minimize_to_tray)

        if not checked and self.tray_icon.isVisible():
            self.tray_icon.hide()

    def toggle_autostart(self, checked: bool) -> None:
        """
        Включает или отключает автозапуск при старте системы.
        """
        if checked:
            enable_autostart()
            self.logger.info(tr("Автозапуск включен"))
        else:
            disable_autostart()
            self.logger.info(tr("Автозапуск отключен"))

    def toggle_autorun_with_last_config(self, checked: bool) -> None:
        """
        Включает или отключает автозапуск с последней конфигурацией.
        """
        self.autorun_with_last_config = checked
        settings.setValue("autorun_with_last_config", self.autorun_with_last_config)
        self.logger.info(f"{tr('Автозапуск с последним конфигом')} {'включен' if checked else 'отключен'}")
        if checked:
            settings.setValue("last_config_path", self.current_config_path)

    def toggle_update_blacklists_on_start(self, checked: bool) -> None:
        """
        Включает или отключает обновление черных списков при запуске.
        """
        settings.setValue("update_blacklists_on_start", checked)
        self.logger.info(f"{tr('Обновление черных списков при запуске программы')} {'включено' if checked else 'отключено'}")

    def create_button(self, text, func, layout, enabled=True, icon=None, icon_size=(24, 24), tooltip=None):
        """
        Создает кнопку с заданными параметрами.
        """
        button = PushButton(text, self, icon)
        button.setEnabled(enabled)
        if func:
            button.clicked.connect(func)
        if icon:
            self.set_button_icon(button, icon, icon_size)
        if tooltip:
            button.setToolTip(tooltip)
        if layout is not None:
            layout.addWidget(button)
        return button

    def handle_create_service(self) -> None:
        """
        Обработчик создания службы.
        """
        result = create_service()
        QMessageBox.information(self, tr("Создание службы"), result)

    def handle_delete_service(self) -> None:
        """
        Обработчик удаления службы.
        """
        result = delete_service()
        QMessageBox.information(self, tr("Удаление службы"), result)

    def run_exe(self, auto_run: bool = False) -> None:
        """
        Запускает выбранный скрипт.
        """
        self.logger.debug(f"Запуск скрипта, auto_run={auto_run}")
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
            self.start_main_process(
                command,
                selected_option,
                disable_run=True,
                clear_console_text=clear_console_text,
                capture_output=True
            )
            self.logger.info(f"{tr('Процесс')} '{selected_option}' {tr('запущен')}")

            winws_path = os.path.join(ZAPRET_FOLDER, "winws.exe")
            self.start_winws(winws_path)

        except Exception as e:
            error_msg = f"{tr('Ошибка запуска процесса')}: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.console_output.append(error_msg)

        if auto_run:
            settings.setValue("last_config_path", self.current_config_path)

    def is_executable_available(self, executable, selected_option):
        if not os.path.exists(executable):
            self.logger.error(f"{tr('Файл не найден')}: {executable}")
            return False
        if not os.access(executable, os.X_OK):
            self.logger.error(f"{tr('Недостаточно прав для запуска')}: {executable}")
            return False
        return True

    def start_main_process(
        self,
        command: List[str],
        process_name: str,
        disable_run: bool = False,
        clear_console_text: Optional[str] = None,
        capture_output: bool = True
    ) -> None:
        """
        Запускает основной процесс через WorkerThread.
        """
        if clear_console_text:
            self.clear_console(clear_console_text)

        try:
            if self.main_worker_thread is not None:
                self.main_worker_thread.terminate_process()
                self.main_worker_thread.quit()
                self.main_worker_thread.wait()
                self.main_worker_thread = None

            self.main_worker_thread = WorkerThread(
                command=command,
                process_name=process_name,
                capture_output=capture_output
            )
            if capture_output:
                self.main_worker_thread.output_signal.connect(self.update_output)
            self.main_worker_thread.finished_signal.connect(self.on_finished)
            self.main_worker_thread.error_signal.connect(self.handle_error)

            self.main_worker_thread.start()

            if disable_run:
                self.run_button.setEnabled(False)
                self.stop_close_button.setEnabled(True)
        except Exception as e:
            error_msg = f"{tr('Ошибка при запуске потока')}: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.console_output.append(error_msg)

    def update_output(self, text: str) -> None:
        """
        Обновляет консоль вывода.
        """
        ignore_keywords = [
            "loading hostlist",
            "we have",
            "desync profile(s)",
            "loaded hosts",
            "loading plain text list",
            "loaded",
            "loading ipset",
            "github version"
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
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    @pyqtSlot(str)
    def on_finished(self, process_name: str) -> None:
        """
        Обработчик завершения процесса.
        """
        if process_name in self.script_options or process_name == "winws.exe":
            if process_name == "winws.exe":
                self.logger.info(f"{tr('Процесс')} {process_name} {tr('завершён')}")
            else:
                self.run_button.setEnabled(True)
                self.stop_close_button.setEnabled(False)
                self.logger.info(f"{tr('Процесс')} {process_name} {tr('завершён')}")
                self.console_output.append(tr("Обход блокировки завершен"))

            if process_name == "winws.exe":
                if self.winws_worker_thread:
                    try:
                        self.winws_worker_thread.finished_signal.disconnect(self.on_finished)
                        self.winws_worker_thread.error_signal.disconnect(self.handle_error)
                    except TypeError:
                        pass
                    self.winws_worker_thread = None
            else:
                if self.main_worker_thread:
                    try:
                        self.main_worker_thread.output_signal.disconnect(self.update_output)
                        self.main_worker_thread.finished_signal.disconnect(self.on_finished)
                        self.main_worker_thread.error_signal.disconnect(self.handle_error)
                    except TypeError:
                        pass
                    self.main_worker_thread = None

    @pyqtSlot(str)
    def handle_error(self, error_message: str) -> None:
        """
        Обработчик ошибок процессов.
        """
        self.logger.error(f"Ошибка процесса: {error_message}")
        QMessageBox.critical(self, tr("Ошибка"), error_message)

    def stop_and_close(self) -> None:
        """
        Завершает все запущенные процессы и закрывает приложение.
        """
        self.logger.info(tr("Начата процедура остановки и закрытия процессов"))

        if self.main_worker_thread is not None:
            self.logger.info(tr("Завершение работы основного WorkerThread"))
            self.main_worker_thread.terminate_process()
            self.main_worker_thread.quit()
            if not self.main_worker_thread.wait(5000):
                self.logger.warning(tr("Основной WorkerThread не завершился в течение 5 секунд. Принудительно заверяем"))
                self.main_worker_thread.terminate()
                self.main_worker_thread.wait()
            self.main_worker_thread = None

        if self.winws_worker_thread is not None:
            self.logger.info(tr("Завершение работы WorkerThread для winws.exe"))
            self.winws_worker_thread.terminate_process()
            self.winws_worker_thread.quit()
            if not self.winws_worker_thread.wait(5000):
                self.logger.warning(tr("WorkerThread для winws.exe не завершился в течение 5 секунд. Принудительно заверяем"))
                self.winws_worker_thread.terminate()
                self.winws_worker_thread.wait()
            self.winws_worker_thread = None

        service_name = "WinDivert"
        try:
            self.logger.info(tr(f"Попытка остановить службу '{service_name}'"))
            stop_service(service_name)
            self.logger.info(tr(f"Служба '{service_name}' успешно остановлена"))
        except Exception as e:
            self.logger.error(tr(f"Ошибка при остановке службы '{service_name}': {e}"))
            QMessageBox.warning(
                self,
                tr("Ошибка"),
                tr(f"Не удалось остановить службу '{service_name}'. Подробнее в логах."),
            )

    def clear_console(self, initial_text: str = "") -> None:
        """
        Очищает консоль вывода.
        """
        self.console_output.clear()
        if initial_text:
            self.console_output.append(initial_text)

    def load_config_via_dialog(self) -> None:
        """
        Открывает диалог выбора файла конфигурации и загружает выбранную конфигурацию.
        """
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

            if self.main_worker_thread is not None:
                self.logger.info(tr("Завершение работы WorkerThread перед загрузкой новой конфигурации"))
                self.main_worker_thread.terminate_process()
                self.main_worker_thread.quit()
                self.main_worker_thread.wait()
                self.main_worker_thread = None

            if self.winws_worker_thread is not None:
                self.logger.info(tr("Завершение работы WorkerThread для winws.exe перед загрузкой новой конфигурации"))
                self.winws_worker_thread.terminate_process()
                self.winws_worker_thread.quit()
                self.winws_worker_thread.wait()
                self.winws_worker_thread = None

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

            self.update_script_options_display()
            self.selected_script.setEnabled(True)
            self.run_button.setEnabled(True)
            self.stop_close_button.setEnabled(False)

            if self.autorun_with_last_config:
                settings.setValue("last_config_path", file_path)

    def validate_config_file(self, file_path: str) -> Optional[str]:
        """
        Валидирует файл конфигурации.
        """
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

    def open_settings_dialog(self) -> None:
        """
        Открывает диалоговое окно настроек обновлений.
        """
        dialog = SettingsDialog(self)
        dialog.config_updated_signal.connect(self.reload_configuration)
        dialog.exec()

    def open_proxy_settings_dialog(self) -> None:
        """
        Открывает диалоговое окно с настройками прокси.
        """
        dialog = ProxySettingsDialog(self)
        dialog.show()

    def reload_configuration(self) -> None:
        """
        Перезагружает конфигурацию после обновления.
        """
        self.logger.debug("Перезагрузка конфигурации")
        if self.main_worker_thread is not None:
            self.main_worker_thread.terminate_process()
            self.main_worker_thread.quit()
            self.main_worker_thread.wait()
            self.main_worker_thread = None

        if self.winws_worker_thread is not None:
            self.winws_worker_thread.terminate_process()
            self.winws_worker_thread.quit()
            self.winws_worker_thread.wait()
            self.winws_worker_thread = None

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
        QMessageBox.information(self, tr("Обновление"), tr("Конфигурация обновлена и перезагружена"))

    def start_winws(self, winws_path: str, args: Optional[List[str]] = None) -> None:
        """
        Запускает процесс winws.exe.
        """
        if self.winws_worker_thread is not None and self.winws_worker_thread.process_name == "winws.exe":
            return

        self.winws_worker_thread = WorkerThread(
            command=[winws_path] + (args if args else []),
            process_name="winws.exe",
            capture_output=False
        )
        self.winws_worker_thread.finished_signal.connect(self.on_finished)
        self.winws_worker_thread.error_signal.connect(self.handle_error)
        self.winws_worker_thread.start()