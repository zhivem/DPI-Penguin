import os
import requests
import zipfile
import shutil
import psutil
import win32serviceutil
import win32service
import winerror  # Импортируем winerror для доступа к константам ошибок
import logging  # Импортируем logging для логирования
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QTextEdit
)
from PyQt6.QtCore import pyqtSlot
from utils.utils import tr  # Предполагается, что функция tr находится в utils/utils.py


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Дополнительные настройки"))
        self.setFixedSize(500, 400)  # Увеличиваем размер для лучшего отображения текста

        # Инициализируем логгер
        self.logger = logging.getLogger(self.__class__.__name__)

        # Основной вертикальный макет
        layout = QVBoxLayout()

        # Текстовое поле (TextEdit)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlaceholderText(tr("Информация об обновлении будет отображена здесь..."))
        layout.addWidget(self.text_edit)

        # Горизонтальный макет для кнопок
        button_layout = QHBoxLayout()

        # Кнопка "Обновить"
        self.update_button = QPushButton(tr("Обновить"), self)
        self.update_button.clicked.connect(self.on_update)
        button_layout.addWidget(self.update_button)

        # Кнопка "Закрыть"
        self.close_button = QPushButton(tr("Закрыть"), self)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    @pyqtSlot()
    def on_update(self):
        """
        Метод, вызываемый при нажатии кнопки "Обновить".
        Завершает процесс winws.exe и останавливает службу WinDivert перед обновлением.
        Затем скачивает обновления из указанного репозитория GitHub и распаковывает их в папку zapret.
        После успешного обновления обновляет локальный version_zapret.ini.
        """
        self.text_edit.append(tr("Начинается обновление..."))
        self.logger.info(tr("Начинается обновление zapret..."))

        # Завершение процесса winws.exe и остановка службы WinDivert перед обновлением
        self.terminate_process("winws.exe")
        self.stop_service("WinDivert")

        try:
            # URL для скачивания zip-архива репозитория
            zip_url = "https://github.com/zhivem/DPI-Penguin/raw/refs/heads/main/zapret/zapret.zip"
            self.text_edit.append(tr("Скачивание обновлений с GitHub..."))
            self.logger.info(tr("Скачивание обновлений с GitHub..."))
            response = requests.get(zip_url, stream=True)

            if response.status_code == 200:
                zip_path = os.path.join(os.getcwd(), "update_temp.zip")
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                self.text_edit.append(tr("Скачивание завершено. Распаковка обновлений..."))
                self.logger.info(tr("Скачивание завершено. Распаковка обновлений..."))

                # Распаковываем только папку zapret
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zapret_folder_in_zip = [item for item in zip_ref.namelist() if item.startswith("zapret/")]
                    if zapret_folder_in_zip:
                        for file in zapret_folder_in_zip:
                            if file.endswith('/'):
                                # Это директория, создаём её
                                target_dir = os.path.join(os.getcwd(), "zapret", os.path.relpath(file, "zapret"))
                                os.makedirs(target_dir, exist_ok=True)
                            else:
                                # Это файл, извлекаем его
                                relative_path = os.path.relpath(file, "zapret")
                                if relative_path in [".", "./"]:  # Пропускаем текущую директорию
                                    continue
                                target_path = os.path.join(os.getcwd(), "zapret", relative_path)
                                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                                with zip_ref.open(file) as source, open(target_path, "wb") as target:
                                    shutil.copyfileobj(source, target)
                        self.text_edit.append(tr("Распаковка завершена. Обновление выполнено успешно."))
                        self.logger.info(tr("Распаковка завершена. Обновление выполнено успешно."))
                    else:
                        self.text_edit.append(tr("Папка zapret не найдена в архиве."))
                        self.logger.warning(tr("Папка zapret не найдена в архиве."))
                        QMessageBox.warning(self, tr("Обновление"), tr("Папка zapret не найдена в архиве."))
                        return
                # Удаляем временный zip-файл
                os.remove(zip_path)
                self.text_edit.append(tr("Файлы zapret успешно обновлены."))
                self.logger.info(tr("Файлы zapret успешно обновлены."))

                # Обновляем локальный version_zapret.ini
                self.update_local_version()

                QMessageBox.information(self, tr("Обновление"), tr("Обновление выполнено успешно."))
                self.logger.info(tr("Обновление выполнено успешно."))
            else:
                self.text_edit.append(tr(f"Не удалось скачать обновления. Статус код: {response.status_code}"))
                self.logger.warning(tr(f"Не удалось скачать обновления. Статус код: {response.status_code}"))
                QMessageBox.warning(self, tr("Обновление"), tr("Не удалось скачать обновления. Попробуйте позже."))
        except Exception as e:
            error_message = f"Произошла ошибка при обновлении: {e}"
            self.text_edit.append(tr(error_message))
            self.logger.error(tr(f"Произошла ошибка при обновлении: {e}"))
            QMessageBox.critical(self, tr("Обновление"), tr(f"Произошла ошибка при обновлении: {e}"))

    def terminate_process(self, process_name):
        """Завершает указанный процесс, если он запущен."""
        self.text_edit.append(tr(f"Попытка завершить процесс {process_name}..."))
        self.logger.info(tr(f"Попытка завершить процесс {process_name}..."))
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == process_name.lower():
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    self.text_edit.append(tr(f"Процесс {process_name} успешно завершен."))
                    self.logger.info(tr(f"Процесс {process_name} успешно завершен."))
                except psutil.NoSuchProcess:
                    self.text_edit.append(tr(f"Процесс {process_name} уже завершен."))
                    self.logger.warning(tr(f"Процесс {process_name} уже завершен."))
                except psutil.TimeoutExpired:
                    self.text_edit.append(tr(f"Не удалось завершить процесс {process_name} в течение времени ожидания."))
                    self.logger.error(tr(f"Не удалось завершить процесс {process_name} в течение времени ожидания."))
                except Exception as e:
                    self.text_edit.append(tr(f"Ошибка при завершении процесса {process_name}: {e}"))
                    self.logger.error(tr(f"Ошибка при завершении процесса {process_name}: {e}"))

    def stop_service(self, service_name):
        """Останавливает указанную службу, если она запущена."""
        self.text_edit.append(tr(f"Попытка остановить службу {service_name}..."))
        self.logger.info(tr(f"Попытка остановить службу {service_name}..."))
        try:
            status = win32serviceutil.QueryServiceStatus(service_name)[1]
            if status == win32service.SERVICE_RUNNING:
                win32serviceutil.StopService(service_name)
                win32serviceutil.WaitForServiceStatus(service_name, win32service.SERVICE_STOPPED, 30)
                self.text_edit.append(tr(f"Служба {service_name} успешно остановлена."))
                self.logger.info(tr(f"Служба {service_name} успешно остановлена."))
            else:
                self.text_edit.append(tr(f"Служба {service_name} уже остановлена."))
                self.logger.info(tr(f"Служба {service_name} уже остановлена."))
        except win32service.error as e:
            if e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
                self.text_edit.append(tr(f"Служба {service_name} не существует."))
                self.logger.warning(tr(f"Служба {service_name} не существует."))
            else:
                self.text_edit.append(tr(f"Ошибка при остановке службы {service_name}: {e}"))
                self.logger.error(tr(f"Ошибка при остановке службы {service_name}: {e}"))
        except Exception as e:
            self.text_edit.append(tr(f"Неожиданная ошибка при остановке службы {service_name}: {e}"))
            self.logger.error(tr(f"Неожиданная ошибка при остановке службы {service_name}: {e}"))

    def update_local_version(self):
        """
        Загружает последнюю версию version_zapret.ini с GitHub и обновляет локальный файл.
        """
        self.text_edit.append(tr("Обновление локального version_zapret.ini..."))
        self.logger.info(tr("Обновление локального version_zapret.ini..."))
        try:
            # URL для получения версии zapret с GitHub
            version_url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/version/version_zapret.ini"
            response = requests.get(version_url)
            if response.status_code == 200:
                # Убедимся, что директория version существует
                version_dir = os.path.join(os.getcwd(), "zapret", "version")
                os.makedirs(version_dir, exist_ok=True)

                local_version_file = os.path.join(version_dir, "version_zapret.ini")
                with open(local_version_file, "w", encoding='utf-8') as f:
                    f.write(response.text)
                self.text_edit.append(tr("Локальный version_zapret.ini успешно обновлён."))
                self.logger.info(tr("Локальный version_zapret.ini успешно обновлён."))
            else:
                self.text_edit.append(tr(f"Не удалось скачать version_zapret.ini. Статус код: {response.status_code}"))
                self.logger.warning(tr(f"Не удалось скачать version_zapret.ini. Статус код: {response.status_code}"))
        except Exception as e:
            error_message = f"Произошла ошибка при обновлении version_zapret.ini: {e}"
            self.text_edit.append(tr(error_message))
            self.logger.error(tr(f"Произошла ошибка при обновлении version_zapret.ini: {e}"))
