import os
import logging
from datetime import datetime

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from utils import get_latest_version, is_newer_version, current_version, BASE_FOLDER

class Updater(QThread):
    update_available = pyqtSignal(str)
    no_update = pyqtSignal()
    update_error = pyqtSignal(str)
    blacklist_updated = pyqtSignal()

    def __init__(self):
        super().__init__()

    def run(self):
        self.check_for_updates()

    def check_for_updates(self):
        try:
            latest_version = get_latest_version()
            if latest_version and is_newer_version(latest_version, current_version):
                self.update_available.emit(latest_version)
            else:
                self.no_update.emit()
        except requests.RequestException as e:
            error_message = "Не удалось проверить обновления. Пожалуйста, проверьте подключение к сети."
            logging.error(f"{error_message} Ошибка: {e}")
            self.update_error.emit(error_message)

    def update_blacklist(self):
        url = "https://p.thenewone.lol/domains-export.txt"
        output_file = os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")
    
        try:
            logging.info("Начало загрузки черного списка.")
            response = requests.get(url)
            response.raise_for_status()
            with open(output_file, 'wb') as file:
                file.write(response.content)
            logging.info("Загрузка черного списка успешно завершена.")
            self.blacklist_updated.emit()
        except requests.RequestException as e:
            error_message = f"Ошибка обновления черного списка: {str(e)}"
            logging.error(error_message)
            self.update_error.emit(error_message)
