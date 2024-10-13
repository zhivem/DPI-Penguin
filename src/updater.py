import logging
import os

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from utils import BASE_FOLDER, current_version, get_latest_version, is_newer_version


class Updater(QThread):
    """
    Класс для проверки обновлений приложения и обновления черного списка.

    Сигналы:
        update_available (str): Сигнализирует о наличии доступного обновления.
        no_update (): Сигнализирует об отсутствии новых обновлений.
        update_error (str): Сигнализирует об ошибке при проверке обновлений.
        blacklist_updated (): Сигнализирует об успешном обновлении черного списка.
    """

    update_available = pyqtSignal(str)
    no_update = pyqtSignal()
    update_error = pyqtSignal(str)
    blacklist_updated = pyqtSignal()

    def __init__(self):
        super().__init__()

    def run(self):
        """Запускает проверку обновлений."""
        self.check_for_updates()

    def check_for_updates(self):
        """Проверяет наличие обновлений приложения."""
        try:
            latest_version = get_latest_version()
            logging.info(f"Текущая версия: {current_version}, последняя версия: {latest_version}")
            if latest_version and is_newer_version(latest_version, current_version):
                self.update_available.emit(latest_version)
            else:
                self.no_update.emit()
        except requests.ConnectionError:
            error_message = "Не удалось подключиться к серверу обновлений. Проверьте подключение к интернету."
            logging.error(error_message)
            self.update_error.emit(error_message)
        except requests.Timeout:
            error_message = "Превышено время ожидания ответа от сервера обновлений."
            logging.error(error_message)
            self.update_error.emit(error_message)
        except Exception as e:
            error_message = f"Неизвестная ошибка при проверке обновлений: {str(e)}"
            logging.error(error_message)
            self.update_error.emit(error_message)

    def update_blacklist(self):
        """Обновляет черный список."""
        url = "https://p.thenewone.lol/domains-export.txt"
        output_file = os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")

        try:
            logging.info("Начало загрузки черного списка.")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'wb') as file:
                file.write(response.content)
            logging.info(f"Загрузка черного списка успешно завершена. Сохранено в {output_file}")
            self.blacklist_updated.emit()
        except requests.ConnectionError:
            error_message = "Не удалось подключиться к серверу для обновления черного списка."
            logging.error(error_message)
            self.update_error.emit(error_message)
        except requests.Timeout:
            error_message = "Превышено время ожидания ответа от сервера при обновлении черного списка."
            logging.error(error_message)
            self.update_error.emit(error_message)
        except Exception as e:
            error_message = f"Ошибка обновления черного списка: {str(e)}"
            logging.error(error_message)
            self.update_error.emit(error_message)
