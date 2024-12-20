import logging
import os
import sys
import subprocess
from typing import Any, Optional

from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
)
from qfluentwidgets import PushButton, TextEdit
from utils.utils import (
    BASE_FOLDER,
    settings,
    tr,
)
from utils.update_utils import UpdateChecker
import utils.theme_utils

class SettingsDialog(QDialog):
    """
    Диалоговое окно для управления обновлениями приложения.
    """
    config_updated_signal = pyqtSignal()

    def __init__(self, parent: Optional[Any] = None):
        """
        Инициализирует диалоговое окно настроек обновлений.

        :param parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle(tr("Менеджер обновлений"))
        self.setFixedSize(500, 400)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Получаем текущую тему из настроек
        saved_theme = settings.value("theme", "light")
        # Применяем тему
        utils.theme_utils.apply_theme(self, saved_theme, settings, BASE_FOLDER)

        layout = QVBoxLayout()

        # Виджет для отображения информации
        self.text_edit = TextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText(tr("Информация об обновлении будет отображена здесь..."))
        layout.addWidget(self.text_edit)

        # Кнопки управления обновлениями
        button_layout = QHBoxLayout()
        self.update_button = PushButton(tr("Обновить компоненты"), self)
        self.update_button.clicked.connect(self.on_update)
        button_layout.addWidget(self.update_button)

        self.close_button = PushButton(tr("Закрыть"), self)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.initial_check_done = False
        self.update_checker = UpdateChecker()
        self.update_checker.get_local_versions()
        self.update_checker.get_remote_versions()
        self.check_for_updates()

        # Подключение сигнала обновления конфигурации
        self.update_checker.config_updated_signal.connect(self.on_config_updated)

    @pyqtSlot()
    def on_update(self) -> None:
        """
        Обработчик события нажатия кнопки обновления.
        Выполняет обновление компонентов и информирует пользователя о результате.
        """
        try:
            # Начинаем обновление компонентов
            if self.update_checker.is_update_available('zapret'):
                if not self.update_checker.download_and_update('zapret', dialog=self):
                    raise Exception("Не удалось обновить Zapret")

            if self.update_checker.is_update_available('config'):
                if not self.update_checker.download_and_update('config', dialog=self):
                    raise Exception("Не удалось обновить конфигурацию")

            # Если обновления прошли успешно
            QMessageBox.information(self, tr("Обновление"), tr("Обновление выполнено успешно!"))

            # Закрыть окно обновлений
            self.close()

            # Открыть главное окно
            if self.parent():
                self.parent().show()
            else:
                from gui.gui import GoodbyeDPIApp  # Импорт главного окна
                self.main_window = GoodbyeDPIApp()
                self.main_window.show()

        except Exception as e:
            # В случае ошибки показать уведомление
            QMessageBox.critical(self, tr("Ошибка обновления"), tr(f"Ошибка обновления: {e}"))

            # Закрыть окно обновлений
            self.close()

            # Открыть главное окно
            if self.parent():
                self.parent().show()
            else:
                from gui.gui import GoodbyeDPIApp  # Импорт главного окна
                self.main_window = GoodbyeDPIApp()
                self.main_window.show()

    def check_for_updates(self) -> None:
        """
        Проверяет наличие доступных обновлений и обновляет интерфейс соответственно.
        """
        self.text_edit.clear()
        if not self.initial_check_done:
            self.text_edit.clear()
            if self.update_checker.is_update_available('ver_programm'):
                self.text_edit.append(tr("🔄 Доступна <span style=\"color: red;\">новая версия</span> программы"))
                self.add_download_button()
            else:
                self.text_edit.append(tr("✅ Актуальная версия программы. Обновлений не требуется"))
            self.initial_check_done = True

        self.update_zapret_message(
            tr('🔄 Доступно <span style="color: red;">обновление</span> Zapret') if self.update_checker.is_update_available('zapret') 
            else tr("✅ Версия Zapret актуальна")
        )

        self.update_config_message(
            tr('🔄 Доступно <span style="color: red;">обновление</span> для конфигурационного файла') if self.update_checker.is_update_available('config') 
            else tr("✅ Версия конфигурационного файла актуальна")
        )

        if self.update_checker.is_update_available('zapret') or self.update_checker.is_update_available('config'):
            self.update_button.setEnabled(True)
        else:
            self.update_button.setEnabled(False)

    def update_zapret_message(self, message: str) -> None:
        """
        Обновляет сообщение об обновлении Zapret в текстовом редакторе.

        :param message: Новое сообщение для отображения.
        """
        self.replace_message_in_text_edit("Zapret", message)

    def update_config_message(self, message: str) -> None:
        """
        Обновляет сообщение об обновлении конфигурационного файла в текстовом редакторе.

        :param message: Новое сообщение для отображения.
        """
        self.replace_message_in_text_edit("default.ini", message)

    def replace_message_in_text_edit(self, keyword: str, new_message: str) -> None:
        """
        Заменяет сообщение в текстовом редакторе на основе ключевого слова.

        :param keyword: Ключевое слово для поиска строки.
        :param new_message: Новое сообщение для вставки.
        """
        document = self.text_edit.document()
        found = False
        for i in range(document.blockCount()):
            block = document.findBlockByNumber(i)
            text = block.text()
            if keyword.lower() in text.lower():
                cursor = self.text_edit.textCursor()
                cursor.setPosition(block.position())
                cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                cursor.insertText(new_message)
                found = True
                break
        if not found:
            self.text_edit.append(new_message)

    def add_download_button(self) -> None:
        """
        Добавляет кнопку для загрузки и обновления программы, если она ещё не добавлена.
        """
        if not hasattr(self, 'download_button'):
            self.download_button = PushButton(tr("Загрузить и обновить программу"), self)
            self.download_button.clicked.connect(self.open_download_site)
            self.layout().addWidget(self.download_button)

    def open_download_site(self) -> None:
        """
        Запускает локальный установщик обновлений.
        """
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
                updater_exe = os.path.join(base_path, 'loader.exe') 
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
                updater_exe = os.path.join(base_path, 'loader.exe')  

            if not os.path.exists(updater_exe):
                QMessageBox.critical(self, tr("Ошибка"), tr("Файл обновления не найден"))
                return

            subprocess.Popen([updater_exe], shell=True)

            if self.parent():
                self.parent().close()
            else:
                self.close()

        except Exception as e:
            QMessageBox.critical(self, tr("Ошибка"), tr(f"Не удалось запустить обновление: {e}"))

    @pyqtSlot()
    def on_config_updated(self):
        """
        Обработчик сигнала обновления конфигурации.
        """
        self.logger.info("Конфигурация обновлена.")
