# settings_dialog.py

import os
import requests
import zipfile
import shutil
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
        self.setFixedSize(400, 300)
        
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
        Скачивает обновления из указанного репозитория GitHub.
        """
        self.text_edit.append(tr("Начинается обновление..."))
        try:
            # URL для скачивания zip-архива репозитория
            zip_url = "https://github.com/zhivem/DPI-Penguin/archive/refs/heads/main.zip"
            self.text_edit.append(tr("Скачивание обновлений с GitHub..."))
            response = requests.get(zip_url, stream=True)
            if response.status_code == 200:
                zip_path = os.path.join(os.getcwd(), "update_temp.zip")
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                self.text_edit.append(tr("Скачивание завершено. Распаковка обновлений..."))

                # Распаковываем только папку zapret
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zapret_folder_in_zip = [item for item in zip_ref.namelist() if item.startswith("DPI-Penguin-main/zapret/")]
                    if zapret_folder_in_zip:
                        for file in zapret_folder_in_zip:
                            zip_ref.extract(file, os.getcwd())
                        self.text_edit.append(tr("Распаковка завершена. Обновление выполнено успешно."))
                    else:
                        self.text_edit.append(tr("Папка zapret не найдена в архиве."))
                # Удаляем временный zip-файл и извлеченные файлы
                os.remove(zip_path)
                extracted_folder = os.path.join(os.getcwd(), "DPI-Penguin-main", "zapret")
                if os.path.exists(extracted_folder):
                    target_zapret_folder = os.path.join(os.getcwd(), "zapret")
                    if os.path.exists(target_zapret_folder):
                        shutil.rmtree(target_zapret_folder)
                    shutil.move(extracted_folder, target_zapret_folder)
                    shutil.rmtree(os.path.join(os.getcwd(), "DPI-Penguin-main"))
                    self.text_edit.append(tr("Файлы zapret успешно обновлены."))
                QMessageBox.information(self, tr("Обновление"), tr("Обновление выполнено успешно."))
            else:
                self.text_edit.append(tr(f"Не удалось скачать обновления. Статус код: {response.status_code}"))
                QMessageBox.warning(self, tr("Обновление"), tr("Не удалось скачать обновления. Попробуйте позже."))
        except Exception as e:
            self.text_edit.append(tr(f"Произошла ошибка при обновлении: {e}"))
            QMessageBox.critical(self, tr("Обновление"), tr(f"Произошла ошибка при обновлении: {e}"))
