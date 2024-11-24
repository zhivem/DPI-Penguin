import configparser
import logging
import os
from typing import Any, List, Optional

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
    QGridLayout
)
from qfluentwidgets import ComboBox as QFComboBox, PushButton, TextEdit

from utils.update_checker import UpdateChecker
from utils.utils import (
    BASE_FOLDER,
    CURRENT_VERSION,
    ZAPRET_FOLDER,
    CONFIG_VERSION,
    ZAPRET_VERSION,
    create_service,
    delete_service,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    load_script_options,
    open_path,
    set_language,
    settings,
    tr,
    translation_manager,
)
import utils.theme_utils
from gui.updater_manager import SettingsDialog
from workers.process_worker import WorkerThread

# Пути к иконкам
TRAY_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "newicon.ico")
THEME_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "themes.png")
LOG_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "log.png")
INI_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "ini.png")
MANAGER_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "manager.png")
BLACK_ICON_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "black.png")
ADD_SRV_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "add_service.png")
DELETE_SRV_PATH = os.path.join(BASE_FOLDER, "resources", "icon", "delete_service.png")


class GoodbyeDPIApp(QtWidgets.QMainWindow):
    """
    Главное окно приложения DPI Penguin.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.ensure_logs_folder_exists()

        self.minimize_to_tray: bool = settings.value("minimize_to_tray", True, type=bool)
        self.autostart_enabled: bool = is_autostart_enabled()
        self.autorun_with_last_config: bool = settings.value(
            "autorun_with_last_config", False, type=bool
        )
        self.logger.debug(f"autorun_with_last_config: {self.autorun_with_last_config}")

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
            QTimer.singleShot(0, self.run_autorun)
        else:
            self.show()

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

    def ensure_logs_folder_exists(self) -> None:
        """
        Убедиться, что папка для логов существует, иначе создать её.
        """
        logs_folder = os.path.join(BASE_FOLDER, "logs")
        if not os.path.exists(logs_folder):
            try:
                os.makedirs(logs_folder)
                self.logger.info(f"{tr('Создана папка logs')}: {logs_folder}")
            except Exception as e:
                self.logger.error(f"{tr('Не удалось создать папку logs')}: {e}", exc_info=True)

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

        :param icon_path: Путь к иконке.
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
        Обработчик события закрытия окна. Если включено, сворачивает приложение в трей.

        :param event: Событие закрытия.
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

        :param reason: Причина активации.
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

        :return: Экземпляр QTabWidget с добавленными вкладками.
        """
        tab_widget = QTabWidget(self)
        tab_widget.addTab(self.create_process_tab(), tr("Основное"))
        tab_widget.addTab(self.create_settings_tab(), tr("Настройки"))
        tab_widget.addTab(self.create_info_tab(), tr("О программе"))
        return tab_widget

    def create_process_tab(self) -> QWidget:
        """
        Создаёт вкладку "Основное" с элементами управления процессами.

        :return: Экземпляр QWidget для вкладки "Основное".
        """
        process_tab = QWidget()
        process_layout = QVBoxLayout(process_tab)

        # Выбор скрипта
        script_layout = QHBoxLayout()

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

        # Кнопки управления процессами
        buttons_layout = QHBoxLayout()
        self.run_button = self.create_button(tr("Запустить"), self.run_exe, buttons_layout)
        self.stop_close_button = self.create_button(
            tr("Остановить и закрыть"),
            self.stop_and_close,
            buttons_layout,
            enabled=False
        )
        process_layout.addLayout(buttons_layout)

        # Консоль вывода
        self.console_output = TextEdit(self)
        self.console_output.setReadOnly(True)
        process_layout.addWidget(self.console_output)

        # Кнопки для открытия папок логов и конфигураций
        log_and_config_layout = QHBoxLayout()

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

        # Кнопка переключения темы
        self.theme_toggle_button = PushButton()
        utils.theme_utils.update_theme_button_text(self, settings)
        self.set_button_icon(self.theme_toggle_button, THEME_ICON_PATH, (16, 16))
        self.theme_toggle_button.clicked.connect(self.toggle_theme_button_clicked)
        process_layout.addWidget(self.theme_toggle_button)

        return process_tab

    def handle_open_path(self, path: str) -> None:
        """
        Открывает заданную папку или файл в проводнике.

        :param path: Путь к папке или файлу.
        """
        error = open_path(path)
        if error:
            QMessageBox.warning(self, tr("Ошибка"), error)

    def set_button_icon(self, button: PushButton, icon_path: str, icon_size: tuple) -> None:
        """
        Устанавливает иконку на кнопку.

        :param button: Экземпляр PushButton.
        :param icon_path: Путь к иконке.
        :param icon_size: Размер иконки.
        """
        if not os.path.exists(icon_path):
            self.logger.error(f"{tr('Файл иконки приложения не найден')}: {icon_path}")
        else:
            icon = QIcon(icon_path)
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

        :return: Экземпляр QWidget для вкладки "Настройки".
        """
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)

        # Группа выбора языка
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

        # Группа автозапуска
        self.autostart_group = QGroupBox(tr("Автозапуск"))
        autostart_layout = QVBoxLayout()
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

        self.update_blacklists_on_start_checkbox = QCheckBox(tr("Проверять обновления черных списков при запуске"))
        self.update_blacklists_on_start_checkbox.setChecked(settings.value("update_blacklists_on_start", False, type=bool))
        self.update_blacklists_on_start_checkbox.toggled.connect(self.toggle_update_blacklists_on_start)
        autostart_layout.addWidget(self.update_blacklists_on_start_checkbox)

        # Настройка шрифта для чекбоксов
        font = self.tray_checkbox.font()
        font.setPointSize(9)
        self.tray_checkbox.setFont(font)
        self.autostart_checkbox.setFont(font)
        self.autorun_with_last_config_checkbox.setFont(font)
        self.update_blacklists_on_start_checkbox.setFont(font)

        settings_layout.addWidget(self.autostart_group)

        # Группа управления службами
        self.services_group = QGroupBox(tr("Службы"))
        services_layout = QVBoxLayout()
        self.services_group.setLayout(services_layout)

        self.create_service_button = self.create_button(
            tr("Создать службу"),
            self.handle_create_service,
            services_layout,
            icon_path=ADD_SRV_PATH,
            icon_size=(16, 16)
        )

        self.delete_service_button = self.create_button(
            tr("Удалить службу"),
            self.handle_delete_service,
            services_layout,
            icon_path=DELETE_SRV_PATH,
            icon_size=(16, 16)
        )

        services_layout.addWidget(self.create_service_button)
        services_layout.addWidget(self.delete_service_button)

        settings_layout.addWidget(self.services_group)

        # Группа обновлений
        self.updates_group = QGroupBox(tr("Обновления"))
        updates_layout = QVBoxLayout()
        self.updates_group.setLayout(updates_layout)

        self.open_additional_settings_button = self.create_button(
            text=tr("Менеджер обновлений"),
            func=self.open_settings_dialog,
            layout=updates_layout,
            icon_path=MANAGER_ICON_PATH,
            icon_size=(16, 16)
        )

        self.update_blacklists_button = self.create_button(
            text=tr("Обновить черные списки"),
            func=lambda: self.update_blacklists(silent=False),
            layout=updates_layout,
            icon_path=BLACK_ICON_PATH,
            icon_size=(16, 16)
        )

        updates_layout.addWidget(self.open_additional_settings_button)
        updates_layout.addWidget(self.update_blacklists_button)

        settings_layout.addWidget(self.updates_group)

        settings_layout.addStretch(1)

        return settings_tab

    def change_language(self) -> None:
        """
        Обработчик изменения языка приложения.
        """
        lang_code = self.language_combo.currentData()
        set_language(lang_code)
        settings.setValue("language", lang_code)
        self.update_ui_texts()

    def update_ui_texts(self) -> None:
        """
        Обновляет тексты интерфейса в соответствии с выбранным языком.
        """
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
        self.open_additional_settings_button.setText(tr("Менеджер обновлений"))
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
        Создаёт вкладку "О программе" с информацией о приложении и зависимостях.

        :return: Экземпляр QWidget для вкладки "О программе".
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
        Обновляет тексты в вкладке "О программе" в соответствии с выбранным языком.
        """
        self.details_group.setTitle(tr("Подробности"))
        self.acknowledgements_group.setTitle(tr("Зависимости"))

    def create_details_group(self) -> QGroupBox:
        """
        Создаёт группу с подробностями о приложении.

        :return: Экземпляр QGroupBox с подробностями.
        """
        group = QGroupBox(tr("Подробности"))
        layout = QtWidgets.QGridLayout(group)

        labels = {
            tr("Версия"): f"{CURRENT_VERSION}",
            tr("Разработчик"): "Zhivem",
            tr("Репозиторий на GitHub"): f"<a href='https://github.com/zhivem/DPI-Penguin'>{tr('DPI Penguin')}</a>",
            tr("Релизы"): f"<a href='https://github.com/zhivem/DPI-Penguin/releases'>{tr('Все версии')}</a>",
            tr("Лицензия"): tr("© 2024 Zhivem. Лицензия: Apache")
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
        Создаёт группу с информацией о зависимостях приложения.

        :return: Экземпляр QGroupBox с зависимостями.
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

        return group

    def create_acknowledgement_section(self, title: str, description: str, version: str, developer: str, links: List[str]) -> QWidget:
        """
        Создаёт секцию с информацией о конкретной зависимости.

        :param title: Название зависимости.
        :param description: Описание зависимости.
        :param version: Версия зависимости.
        :param developer: Разработчик зависимости.
        :param links: Ссылки на репозиторий или документацию.
        :return: Экземпляр QWidget с информацией о зависимости.
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
        Переключает поведение приложения при закрытии (сворачивание в трей).

        :param checked: Состояние чекбокса.
        """
        self.minimize_to_tray = checked
        settings.setValue("minimize_to_tray", self.minimize_to_tray)

        if not checked and self.tray_icon.isVisible():
            self.tray_icon.hide()

    def toggle_autostart(self, checked: bool) -> None:
        """
        Включает или отключает автозапуск приложения при старте системы.

        :param checked: Состояние чекбокса.
        """
        if checked:
            enable_autostart()
            self.logger.info(tr("Автозапуск включен"))
        else:
            disable_autostart()
            self.logger.info(tr("Автозапуск отключен"))

    def toggle_autorun_with_last_config(self, checked: bool) -> None:
        """
        Включает или отключает автоматический запуск с последней конфигурацией.

        :param checked: Состояние чекбокса.
        """
        self.autorun_with_last_config = checked
        settings.setValue("autorun_with_last_config", self.autorun_with_last_config)
        self.logger.info(f"{tr('Автозапуск с последним конфигом')} {'включен' if checked else 'отключен'}")
        if checked:
            settings.setValue("last_config_path", self.current_config_path)

    def toggle_update_blacklists_on_start(self, checked: bool) -> None:
        """
        Включает или отключает автоматическое обновление черных списков при запуске приложения.

        :param checked: Состояние чекбокса.
        """
        settings.setValue("update_blacklists_on_start", checked)
        self.logger.info(f"{tr('Обновление черных списков при запуске программы')} {'включено' if checked else 'отключено'}")

    def create_button(
        self,
        text: str,
        func: Optional[Any],
        layout: QHBoxLayout,
        enabled: bool = True,
        icon_path: Optional[str] = None,
        icon_size: tuple = (24, 24),
        tooltip: Optional[str] = None
    ) -> PushButton:
        """
        Создаёт и настраивает кнопку.

        :param text: Текст на кнопке.
        :param func: Функция, вызываемая при нажатии.
        :param layout: Макет, в который добавляется кнопка.
        :param enabled: Состояние кнопки (включена/выключена).
        :param icon_path: Путь к иконке для кнопки.
        :param icon_size: Размер иконки.
        :param tooltip: Подсказка для кнопки.
        :return: Экземпляр PushButton.
        """
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

        :param auto_run: Если True, запускает скрипт в автоматическом режиме.
        """
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
            self.start_main_process(
                command,
                selected_option,
                disable_run=True,
                clear_console_text=clear_console_text,
                capture_output=capture_output
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

    def is_executable_available(self, executable: str, selected_option: str) -> bool:
        """
        Проверяет доступность исполняемого файла и необходимых зависимостей.

        :param executable: Путь к исполняемому файлу.
        :param selected_option: Выбранный скрипт.
        :return: True, если исполняемый файл доступен и все зависимости выполнены, иначе False.
        """
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

        :param command: Команда для запуска.
        :param process_name: Имя процесса.
        :param disable_run: Если True, отключает кнопку запуска.
        :param clear_console_text: Текст для очистки консоли перед запуском.
        :param capture_output: Если True, захватывает вывод процесса.
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
        Обновляет консоль вывода, фильтруя нежелательные сообщения.

        :param text: Текст для обновления консоли.
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

        :param process_name: Имя завершившегося процесса.
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

        :param error_message: Сообщение об ошибке.
        """
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

    def clear_console(self, initial_text: str = "") -> None:
        """
        Очищает консоль вывода и добавляет начальный текст, если указан.

        :param initial_text: Текст для добавления после очистки консоли.
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
        Валидирует файл конфигурации на соответствие необходимым требованиям.

        :param file_path: Путь к файлу конфигурации.
        :return: Сообщение об ошибке или None, если ошибок нет.
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

    def reload_configuration(self) -> None:
        """
        Перезагружает конфигурацию после обновления.
        """
        # Останавливаем текущие запущенные процессы
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
        """
        Перезагружает конфигурацию после обновления.
        """
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

    def check_updates(self) -> None:
        """
        Проверяет наличие доступных обновлений и уведомляет пользователя.
        """
        self.logger.info(tr("Проверка обновлений..."))
        update_checker = UpdateChecker()
        update_checker.get_local_versions()
        update_checker.get_remote_versions()

        updates_available = False

        if update_checker.is_update_available('ver_programm'):
            updates_available = True

        if update_checker.is_update_available('zapret'):
            updates_available = True

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

    def update_blacklists(self, silent: bool = False) -> None:
        """
        Обновляет черные списки.

        :param silent: Если True, не отображает сообщения пользователю.
        """
        update_checker = UpdateChecker()
        success = update_checker.update_blacklists()
        if success:
            if not silent:
                QMessageBox.information(self, tr("Обновление"), tr("Черные списки успешно обновлены"))
        else:
            if not silent:
                QMessageBox.warning(self, tr("Обновление"), tr("Произошли ошибки при обновлении черных списков. Проверьте логи для подробностей."))
            self.logger.warning(tr("Произошли ошибки при обновлении черных списков"))

    def start_winws(self, winws_path: str, args: Optional[List[str]] = None) -> None:
        """
        Запускает процесс winws.exe.

        :param winws_path: Путь к исполняемому файлу winws.exe.
        :param args: Дополнительные аргументы для запуска.
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
