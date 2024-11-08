# updater_manager.py

import os
import requests
import zipfile
import psutil
import win32serviceutil
import win32service
import winerror
import logging
import configparser
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSlot, pyqtSignal
from utils.utils import tr, BASE_FOLDER, CURRENT_VERSION
from utils.update_checker import UpdateChecker
from qfluentwidgets import PushButton, TextEdit

class SettingsDialog(QDialog):
    config_updated_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Менеджер загрузок"))
        self.setFixedSize(500, 400)

        # Инициализируем логгер
        self.logger = logging.getLogger(self.__class__.__name__)

        # Основной вертикальный макет
        layout = QVBoxLayout()

        # Текстовое поле (TextEdit)
        self.text_edit = TextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText(tr("Информация об обновлении будет отображена здесь..."))
        layout.addWidget(self.text_edit)

        # Горизонтальный макет для кнопок
        button_layout = QHBoxLayout()

        # Кнопка "Обновить"
        self.update_button = PushButton(tr("Обновить"), self)
        self.update_button.clicked.connect(self.on_update)
        button_layout.addWidget(self.update_button)

        # Кнопка "Закрыть"
        self.close_button = PushButton(tr("Закрыть"), self)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Флаг для контроля первоначального заполнения TextEdit
        self.initial_check_done = False

        # Проверяем обновления при инициализации окна
        self.check_for_updates()

    @pyqtSlot()
    def on_update(self):
        """
        Метод, вызываемый при нажатии кнопки "Обновить".
        """
        try:
            # Выполняем обновление Zapret, если требуется
            if self.zapret_update_available:
                self.update_zapret()

            # Выполняем обновление default.ini, если требуется
            if self.config_update_available:
                self.update_default_ini()

            self.logger.info(tr("Обновление успешно"))
            # После обновления проверяем снова, чтобы обновить состояние кнопки
            self.check_for_updates()
            # Показываем диалоговое окно
            QMessageBox.information(self, tr("Обновление"), tr("Обновление успешно завершено"))
        except Exception as e:
            error_message = f"{tr('Произошла ошибка при обновлении')}: {e}"
            self.logger.error(error_message)
            QMessageBox.critical(self, tr("Обновление"), error_message)

    def check_for_updates(self):
        
        self.text_edit.clear()  # Очищаем текстовое поле перед обновлением
        update_checker = UpdateChecker()
        update_checker.get_local_versions()
        update_checker.get_remote_versions()

        # Если это первый запуск, заполняем текстовое поле
        if not self.initial_check_done:
            self.text_edit.clear()
            # Проверяем обновления для программы
            if update_checker.is_update_available('ver_programm'):
                self.text_edit.append(tr("🔄 Доступна <span style=\"color: red;\">новая версия</span> программы"))
                self.add_download_button()
            else:
                self.text_edit.append(tr("✅ Актуальная версия программы. Обновлений не требуется"))
            self.initial_check_done = True

        # Проверяем обновления для Zapret
        self.zapret_update_available = update_checker.is_update_available('zapret')
        if self.zapret_update_available:
            self.update_zapret_message(tr('🔄 Доступно <span style=\"color: red;\">обновление</span> Zapret'))
        else:
            self.update_zapret_message(tr("✅ Версия Zapret актуальна"))

        # Проверяем обновления для config (default.ini)
        self.config_update_available = update_checker.is_update_available('config')
        if self.config_update_available:
            self.update_config_message(tr('🔄 Доступно <span style=\"color: red;\">обновление</span> для конфигурационного файла'))
        else:
            self.update_config_message(tr("✅ Версия конфигурационного файла актуальна"))

        # Устанавливаем состояние кнопки "Обновить"
        if self.zapret_update_available or self.config_update_available:
            self.update_button.setEnabled(True)
        else:
            self.update_button.setEnabled(False)

    def update_zapret_message(self, message):
        """
        Обновляет сообщение о состоянии Zapret в TextEdit.
        """
        self.replace_message_in_text_edit("Zapret", message)

    def update_config_message(self, message):
        """
        Обновляет сообщение о состоянии default.ini в TextEdit.
        """
        self.replace_message_in_text_edit("default.ini", message)

    def replace_message_in_text_edit(self, keyword, new_message):
        """
        Заменяет сообщение, содержащее ключевое слово, на новое сообщение.
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

    def add_download_button(self):
        # Проверяем, не была ли кнопка уже добавлена
        if not hasattr(self, 'download_button'):
            self.download_button = PushButton(tr("Перейти на сайт загрузки"), self)
            self.download_button.clicked.connect(self.open_download_site)
            self.layout().addWidget(self.download_button)

    def open_download_site(self):
        import webbrowser
        download_url = "https://github.com/zhivem/DPI-Penguin/releases"
        webbrowser.open(download_url)

    def update_zapret(self):
        """
        Обновляет файлы zapret.
        """
        self.logger.info(tr("Начинается обновление zapret..."))
        # Завершение процесса winws.exe и остановка службы WinDivert перед обновлением
        self.terminate_process("winws.exe")
        self.stop_service("WinDivert")
        try:
            # URL для скачивания zip-архива zapret
            zip_url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/zapret/zapret.zip"
            self.logger.info(tr("Скачивание обновлений с GitHub..."))
            response = requests.get(zip_url, stream=True)
            if response.status_code == 200:
                zip_path = os.path.join(BASE_FOLDER, "update_temp.zip")
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                self.logger.info(tr("Скачивание завершено. Распаковка обновлений..."))
                # Распаковываем zip-файл
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(BASE_FOLDER)
                os.remove(zip_path)
                self.logger.info(tr("Файлы zapret успешно обновлены."))
                # Обновляем локальный файл версии
                self.update_local_version_file()
            else:
                self.logger.warning(tr(f"Не удалось скачать обновления. Статус код: {response.status_code}"))
                raise Exception(tr("Не удалось скачать обновления. Попробуйте позже."))
        except Exception as e:
            self.logger.error(tr(f"Произошла ошибка при обновлении zapret: {e}"))
            raise e

    def update_default_ini(self):
        """
        Обновляет файл default.ini.
        """
        self.logger.info(tr("Обновление default.ini..."))
        try:
            default_ini_url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/config/default.ini"
            response = requests.get(default_ini_url)
            if response.status_code == 200:
                config_dir = os.path.join(BASE_FOLDER, "config")
                os.makedirs(config_dir, exist_ok=True)
                local_default_ini = os.path.join(config_dir, "default.ini")
                with open(local_default_ini, "w", encoding='utf-8') as f:
                    f.write(response.text)
                self.logger.info(tr("default.ini обновлён успешно."))
                # Обновляем локальный файл версии
                self.update_local_version_file()
                # Уведомляем главное приложение о перезагрузке конфигурации
                self.config_updated_signal.emit()
            else:
                self.logger.warning(tr(f"Не удалось скачать default.ini. Статус код: {response.status_code}"))
                raise Exception(tr("Не удалось скачать default.ini. Попробуйте позже."))
        except Exception as e:
            self.logger.error(tr(f"Произошла ошибка при обновлении default.ini: {e}"))
            raise e

    def update_local_version_file(self):
        """
        Загружает последнюю версию version_zapret.ini с GitHub и обновляет локальный файл.
        """
        self.logger.info(tr("Обновление локального version_zapret.ini..."))
        try:
            version_url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/setting_version/version_zapret.ini"
            response = requests.get(version_url)
            if response.status_code == 200:
                version_dir = os.path.join(BASE_FOLDER, "zapret", "version")
                os.makedirs(version_dir, exist_ok=True)
                local_version_file = os.path.join(version_dir, "version_zapret.ini")
                with open(local_version_file, "w", encoding='utf-8') as f:
                    f.write(response.text)
                self.logger.info(tr("Локальный version_zapret.ini успешно обновлён."))
            else:
                self.logger.warning(tr(f"Не удалось скачать version_zapret.ini. Статус код: {response.status_code}"))
        except Exception as e:
            self.logger.error(tr(f"Произошла ошибка при обновлении version_zapret.ini: {e}"))
            raise e

    def terminate_process(self, process_name):
        """
        Завершает процесс по имени.
        """
        process_found = False
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == process_name.lower():
                process_found = True
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    self.logger.info(tr(f"Процесс {process_name} успешно завершён."))
                except Exception as e:
                    self.logger.error(tr(f"Ошибка при завершении процесса {process_name}: {e}"))
                    raise e
        if not process_found:
            self.logger.info(tr(f"Процесс {process_name} не найден."))

    def stop_service(self, service_name):
        """
        Останавливает службу Windows по имени.
        """
        try:
            # Проверяем, существует ли служба
            service_status = win32serviceutil.QueryServiceStatus(service_name)
            # Если служба запущена, останавливаем ее
            if service_status[1] == win32service.SERVICE_RUNNING:
                win32serviceutil.StopService(service_name)
                self.logger.info(tr(f"Служба {service_name} успешно остановлена."))
            else:
                self.logger.info(tr(f"Служба {service_name} не запущена."))
        except Exception as e:
            if hasattr(e, 'winerror') and e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
                self.logger.warning(tr(f"Служба {service_name} не установлена."))
            else:
                self.logger.error(tr(f"Ошибка при остановке службы {service_name}: {e}"))
                raise e
