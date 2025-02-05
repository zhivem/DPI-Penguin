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
from utils.utils import tr
from utils.update_utils import UpdateChecker

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
            self.update_component('zapret')
            self.update_component('config')

            # Если обновления прошли успешно
            QMessageBox.information(self, tr("Обновление"), tr("Обновление выполнено успешно!"))
            self.close_and_open_main_window()

        except Exception as e:
            # В случае ошибки показать уведомление
            QMessageBox.critical(self, tr("Ошибка обновления"), tr(f"Ошибка обновления: {e}"))
            self.close_and_open_main_window()

    def update_component(self, component: str) -> None:
        """
        Обновляет указанный компонент (например, 'zapret' или 'config').
        :param component: Имя компонента для обновления.
        """
        if self.update_checker.is_update_available(component):
            if not self.update_checker.download_and_update(component, dialog=self):
                raise Exception(f"Не удалось обновить {component}")

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

        self.update_message('zapret', '🔄 Доступно <span style="color: red;">обновление</span> Zapret', "✅ Версия Zapret актуальна")
        self.update_message('config', '🔄 Доступно <span style="color: red;">обновление</span> для конфигурационного файла', "✅ Версия конфигурационного файла актуальна")

        self.update_button.setEnabled(self.update_checker.is_update_available('zapret') or self.update_checker.is_update_available('config'))

    def update_message(self, component: str, update_message: str, current_message: str) -> None:
        """
        Обновляет сообщение для указанного компонента.
        :param component: Имя компонента.
        :param update_message: Сообщение, если обновление доступно.
        :param current_message: Сообщение, если версия актуальна.
        """
        message = update_message if self.update_checker.is_update_available(component) else current_message
        keyword = 'Zapret' if component == 'zapret' else 'default.ini'
        self.replace_message_in_text_edit(keyword, message)

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
            self.close_and_open_main_window()

        except Exception as e:
            QMessageBox.critical(self, tr("Ошибка"), tr(f"Не удалось запустить обновление: {e}"))

    def close_and_open_main_window(self) -> None:
        """
        Закрывает диалог и открывает главное окно.
        """
        self.close()
        if self.parent():
            self.parent().show()
        else:
            from gui.gui import DPIPenguin  
            self.main_window = DPIPenguin()
            self.main_window.show()

    @pyqtSlot()
    def on_config_updated(self):
        """
        Обработчик сигнала обновления конфигурации.
        """
        self.logger.info("Конфигурация обновлена.")
