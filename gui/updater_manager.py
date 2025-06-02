import logging
import os
import subprocess
import sys
from typing import Optional, Any

from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QMessageBox, QVBoxLayout
)

from qfluentwidgets import PushButton, TextEdit

from utils.utils import tr, settings, BASE_FOLDER
from utils.update_utils import UpdateChecker
from utils import theme_utils

class SettingsDialog(QDialog):
    config_updated_signal = pyqtSignal()

    def __init__(self, parent: Optional[Any] = None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.info("Инициализация диалога менеджера обновлений")

        self.setWindowTitle(tr("Менеджер обновлений"))
        self.setFixedSize(500, 400)

        saved_theme = settings.value("theme", "light")  
        theme_utils.apply_theme(self, saved_theme, settings, BASE_FOLDER) 

        self.text_edit = TextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText(tr("Информация об обновлении будет отображена здесь..."))

        self.update_button = PushButton(tr("Обновить компоненты"), self)
        self.update_button.clicked.connect(self.on_update)

        self.close_button = PushButton(tr("Закрыть"), self)
        self.close_button.clicked.connect(self.close)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.close_button)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.text_edit)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.initial_check_done = False
        self.update_checker = UpdateChecker()
        self.update_checker.get_local_versions()
        self.update_checker.get_remote_versions()
        self.update_checker.config_updated_signal.connect(self.on_config_updated)

        self.check_for_updates()

    @pyqtSlot()
    def on_update(self) -> None:
        """Обработчик кнопки обновления компонентов."""
        self.logger.info("Нажата кнопка 'Обновить компоненты'")
        try:
            for component in ('zapret', 'config'):
                self.update_component(component)

            self.logger.info("Обновление компонентов выполнено успешно")
            QMessageBox.information(self, tr("Обновление"), tr("Обновление выполнено успешно!"))
            self.close_and_open_main_window()

        except Exception as e:
            self.logger.exception(f"Ошибка при обновлении компонентов: {e}")
            QMessageBox.critical(self, tr("Ошибка обновления"), tr(f"Ошибка обновления: {e}"))
            self.close_and_open_main_window()

    def update_component(self, component: str) -> None:
        """Проверяет и обновляет указанный компонент, если доступно обновление."""
        self.logger.info(f"Проверка обновления для компонента '{component}'")
        if self.update_checker.is_update_available(component):
            self.logger.info(f"Доступно обновление для '{component}', начинаю загрузку")
            if not self.update_checker.download_and_update(component, dialog=self):
                error_msg = f"Не удалось скачать и обновить '{component}'"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            self.logger.info(f"Компонент '{component}' успешно обновлён")

    def check_for_updates(self) -> None:
        """Проверяет наличие обновлений и обновляет интерфейс."""
        self.logger.info("Проверка наличия обновлений")
        self.text_edit.clear()

        if not self.initial_check_done:
            if self.update_checker.is_update_available('ver_programm'):
                self.logger.info("Доступна новая версия программы")
                self.text_edit.append(tr('🔄 Доступна <span style="color: red;">новая версия</span> программы'))
                self.add_download_button()
            else:
                self.logger.info("Программа актуальна, обновлений не требуется")
                self.text_edit.append(tr("✅ Актуальная версия программы. Обновлений не требуется"))
            self.initial_check_done = True

        self.update_message('zapret', 'Zapret', '🔄 Доступно <span style="color: red;">обновление</span> Zapret', "✅ Версия Zapret актуальна")
        self.update_message('config', 'default.ini', '🔄 Доступно <span style="color: red;">обновление</span> для конфигурационного файла', "✅ Версия конфигурационного файла актуальна")

        self.update_button.setEnabled(
            self.update_checker.is_update_available('zapret') or
            self.update_checker.is_update_available('config')
        )

    def update_message(self, component: str, keyword: str, update_message: str, current_message: str) -> None:
        """Обновляет сообщение в text_edit для компонента."""
        message = update_message if self.update_checker.is_update_available(component) else current_message
        self.replace_message_in_text_edit(keyword, message)

    def replace_message_in_text_edit(self, keyword: str, new_message: str) -> None:
        """Заменяет или добавляет сообщение в text_edit по ключевому слову."""
        document = self.text_edit.document()
        found = False
        for i in range(document.blockCount()):
            block = document.findBlockByNumber(i)
            if keyword.lower() in block.text().lower():
                cursor = self.text_edit.textCursor()
                cursor.setPosition(block.position())
                cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                cursor.insertHtml(new_message)
                found = True
                break
        if not found:
            self.text_edit.append(new_message)

    def add_download_button(self) -> None:
        """Добавляет кнопку загрузки новой версии программы, если её ещё нет."""
        if not hasattr(self, 'download_button'):
            self.logger.info("Добавление кнопки 'Загрузить и обновить программу'")
            self.download_button = PushButton(tr("Загрузить и обновить программу"), self)
            self.download_button.clicked.connect(self.open_download_site)
            self.layout().addWidget(self.download_button)

    def open_download_site(self) -> None:
        """Запускает локальный установщик обновлений."""
        self.logger.info("Запуск локального установщика обновлений")
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            updater_exe = os.path.join(base_path, 'loader.exe')
            if not os.path.exists(updater_exe):
                self.logger.error(f"Файл обновления не найден: {updater_exe}")
                QMessageBox.critical(self, tr("Ошибка"), tr("Файл обновления не найден"))
                return

            self.logger.info(f"Запуск обновления через {updater_exe}")
            subprocess.Popen([updater_exe], shell=True)
            self.close_and_open_main_window()

        except Exception as e:
            self.logger.exception(f"Не удалось запустить обновление: {e}")
            QMessageBox.critical(self, tr("Ошибка"), tr(f"Не удалось запустить обновление: {e}"))

    def close_and_open_main_window(self) -> None:
        """Закрывает диалог и открывает главное окно приложения."""
        self.logger.info("Закрытие диалога и открытие главного окна")
        self.close()
        if self.parent():
            self.parent().show()
        else:
            from gui.gui import DPIPenguin
            self.main_window = DPIPenguin()
            self.main_window.show()

    @pyqtSlot()
    def on_config_updated(self) -> None:
        """Обработчик сигнала обновления конфигурации."""
        self.logger.info("Получен сигнал обновления конфигурации")