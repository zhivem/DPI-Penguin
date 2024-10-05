from PyQt5 import QtCore
import requests
from utils import get_latest_version, is_newer_version, current_version, BASE_FOLDER
import os
from datetime import datetime

class Updater(QtCore.QThread):
    update_available = QtCore.pyqtSignal(str)
    no_update = QtCore.pyqtSignal()
    update_error = QtCore.pyqtSignal(str)
    blacklist_updated = QtCore.pyqtSignal()

    def run(self):
        self.check_for_updates()

    def check_for_updates(self):
        latest_version = get_latest_version()
        if latest_version:
            if is_newer_version(latest_version, current_version):
                self.update_available.emit(latest_version)
            else:
                self.no_update.emit()
        else:
            self.update_error.emit("Не удалось получить последнюю версию.")

    def update_blacklist(self):
        url = "https://p.thenewone.lol/domains-export.txt"
        output_file = os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")
        log_file = os.path.join(BASE_FOLDER, "download_log.txt")

        with open(log_file, 'a', encoding='utf-8') as log:
            def log_message(message):
                log.write(f"{message}\n")

            log_message("====================================")
            log_message(f"[ИНФО] Начало загрузки в {datetime.now()}")

            try:
                response = requests.get(url)
                response.raise_for_status()
                with open(output_file, 'wb') as file:
                    file.write(response.content)
                log_message(f"[ИНФО] Загрузка успешно завершена в {datetime.now()}")
                self.blacklist_updated.emit()
            except requests.RequestException as e:
                log_message(f"[ОШИБКА] Не удалось загрузить файл с {url} в {datetime.now()}: {e}")
                self.update_error.emit(f"Ошибка обновления черного списка: {str(e)}")
