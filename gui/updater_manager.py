import logging
import os
import sys
import psutil
import win32service
import winerror
import win32serviceutil
import subprocess
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QVBoxLayout
from qfluentwidgets import PushButton, TextEdit

from utils.update_checker import UpdateChecker
from utils.utils import tr

class SettingsDialog(QDialog):
    config_updated_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Менеджер обновлений"))
        self.setFixedSize(500, 400)
        self.logger = logging.getLogger(self.__class__.__name__)

        layout = QVBoxLayout()

        # Место для отображения информации
        self.text_edit = TextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText(tr("Информация об обновлении будет отображена здесь..."))
        layout.addWidget(self.text_edit)

        # Кнопки управления
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

    @pyqtSlot()
    def on_update(self):
        try:
            # Начинаем обновление компонентов
            update_success = True

            # Обновление Zapret
            if self.update_checker.is_update_available('zapret'):
                if not self.update_checker.download_and_update('zapret', dialog=self):
                    raise Exception("Не удалось обновить Zapret")
            
            # Обновление конфигурации
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
                from gui import MainWindow  # Импорт главного окна
                self.main_window = MainWindow()
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
                from gui import MainWindow  # Импорт главного окна
                self.main_window = MainWindow()
                self.main_window.show()

    def check_for_updates(self):
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
            tr('🔄 Доступно <span style=\"color: red;\">обновление</span> Zapret') if self.update_checker.is_update_available('zapret') 
            else tr("✅ Версия Zapret актуальна")
        )

        self.update_config_message(
            tr('🔄 Доступно <span style=\"color: red;\">обновление</span> для конфигурационного файла') if self.update_checker.is_update_available('config') 
            else tr("✅ Версия конфигурационного файла актуальна")
        )

        if self.update_checker.is_update_available('zapret') or self.update_checker.is_update_available('config'):
            self.update_button.setEnabled(True)
        else:
            self.update_button.setEnabled(False)

    def update_zapret_message(self, message):
        self.replace_message_in_text_edit("Zapret", message)

    def update_config_message(self, message):
        self.replace_message_in_text_edit("default.ini", message)

    def replace_message_in_text_edit(self, keyword, new_message):
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
        if not hasattr(self, 'download_button'):
            self.download_button = PushButton(tr("Загрузить и обновить программу"), self)
            self.download_button.clicked.connect(self.open_download_site)
            self.layout().addWidget(self.download_button)

    def open_download_site(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
                updater_exe = os.path.join(base_path, 'update.exe') 
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
                updater_exe = os.path.join(base_path, 'update.exe')  

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

    def terminate_process(self, process_name=None, service_name=None):
        if process_name:
            process_found = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    process_found = True
                    try:
                        self.logger.info(f"Попытка завершить процесс {process_name} с PID {proc.info['pid']}")
                        proc.terminate()
                        proc.wait(timeout=5)
                        self.logger.info(f"Процесс {process_name} успешно завершён.")
                    except Exception as e:
                        self.logger.error(f"Ошибка при завершении процесса {process_name}: {e}")
                        raise e
            if not process_found:
                self.logger.info(f"Процесс {process_name} не найден.")
        
        elif service_name:
            try:
                self.logger.info(f"Остановка службы {service_name}...")
                service_status = win32serviceutil.QueryServiceStatus(service_name)
                if service_status[1] == win32service.SERVICE_RUNNING:
                    win32serviceutil.StopService(service_name)
                    self.logger.info(f"Служба {service_name} успешно остановлена.")
                else:
                    self.logger.info(f"Служба {service_name} не запущена.")
            except Exception as e:
                if hasattr(e, 'winerror') and e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
                    self.logger.warning(f"Служба {service_name} не установлена.")
                else:
                    self.logger.error(f"Ошибка при остановке службы {service_name}: {e}")
                    raise e

