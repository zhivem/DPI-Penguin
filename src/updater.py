import logging
import os
from typing import Optional

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from utils import (
    BASE_FOLDER,
    current_version,
    get_latest_version,
    is_newer_version
)


class Updater(QThread):
    """
    Класс Updater для проверки и загрузки обновлений приложения и черного списка.
    Наследуется от QThread для выполнения задач в отдельном потоке.
    """
    update_available = pyqtSignal(str)
    no_update = pyqtSignal()
    update_error = pyqtSignal(str)
    blacklist_updated = pyqtSignal()
    blacklist_update_error = pyqtSignal(str)

    def __init__(self) -> None:
        """
        Инициализация Updater.
        """
        super().__init__()

    def run(self) -> None:
        """
        Метод, выполняемый при запуске потока. Запускает проверку обновлений.
        """
        self.check_for_updates()

    def check_for_updates(self) -> None:
        """
        Проверяет наличие обновлений приложения. Эмитирует соответствующие сигналы
        в зависимости от результата проверки.
        """
        try:
            latest_version = get_latest_version()
            if latest_version and is_newer_version(latest_version, current_version):
                logging.info(f"Доступна новая версия: {latest_version}")
                self.update_available.emit(latest_version)
            else:
                logging.info("Обновления не найдены.")
                self.no_update.emit()
        except requests.RequestException as e:
            error_message = "Не удалось проверить обновления. Пожалуйста, проверьте подключение к сети."
            logging.error(f"{error_message} Ошибка: {e}")
            self.update_error.emit(error_message)

    def update_blacklist(self) -> None:
        """
        Загружает и обновляет черный список из указанного URL. Эмитирует соответствующие
        сигналы в зависимости от результата загрузки.
        """
        url = "https://p.thenewone.lol/domains-export.txt"
        output_file = os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")

        try:
            logging.info(f"Начало загрузки черного списка с {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'wb') as file:
                file.write(response.content)
            logging.info("Загрузка черного списка успешно завершена.")
            self.blacklist_updated.emit()
        except requests.RequestException as e:
            error_message = f"Ошибка обновления черного списка: {str(e)}"
            logging.error(error_message)
            self.blacklist_update_error.emit(error_message)
        except Exception as e:
            error_message = f"Неизвестная ошибка при обновлении черного списка: {str(e)}"
            logging.critical(error_message, exc_info=True)
            self.blacklist_update_error.emit(error_message)
