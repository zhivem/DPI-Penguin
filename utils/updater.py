import logging
import os

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from utils.utils import (
    BASE_FOLDER,
    CURRENT_VERSION,
    get_latest_version,
    is_newer_version
)

# Константы
UPDATE_BLACKLIST_URL = "https://p.thenewone.lol/domains-export.txt"
BLACKLIST_OUTPUT_FILE = os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")
UPDATE_TIMEOUT = 10  # секунд

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
        self.logger = logging.getLogger(self.__class__.__name__)

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
            self.logger.debug("Начата проверка наличия обновлений.")
            latest_version = get_latest_version()
            if latest_version:
                if is_newer_version(latest_version, CURRENT_VERSION):
                    self.logger.info(f"Доступна новая версия: {latest_version}")
                    self.update_available.emit(latest_version)
                else:
                    self.logger.info("Обновления не найдены.")
                    self.no_update.emit()
            else:
                self.logger.warning("Не удалось получить последнюю версию.")
                self.no_update.emit()
        except requests.RequestException as e:
            error_message = "Не удалось проверить обновления. Пожалуйста, проверьте подключение к сети."
            self.logger.error(f"{error_message} Ошибка: {e}")
            self.update_error.emit(error_message)
        except Exception as e:
            error_message = f"Неизвестная ошибка при проверке обновлений: {e}"
            self.logger.critical(error_message, exc_info=True)
            self.update_error.emit(error_message)

    def update_blacklist(self) -> None:
        """
        Загружает и обновляет черный список из указанного URL. Эмитирует соответствующие
        сигналы в зависимости от результата загрузки.
        """
        try:
            self.logger.info(f"Начало загрузки черного списка с {UPDATE_BLACKLIST_URL}")
            response = requests.get(UPDATE_BLACKLIST_URL, timeout=UPDATE_TIMEOUT)
            response.raise_for_status()
            os.makedirs(os.path.dirname(BLACKLIST_OUTPUT_FILE), exist_ok=True)
            with open(BLACKLIST_OUTPUT_FILE, 'wb') as file:
                file.write(response.content)
            self.logger.info("Загрузка черного списка успешно завершена.")
            self.blacklist_updated.emit()
        except requests.RequestException as e:
            error_message = f"Ошибка обновления черного списка: {str(e)}"
            self.logger.error(error_message)
            self.blacklist_update_error.emit(error_message)
        except Exception as e:
            error_message = f"Неизвестная ошибка при обновлении черного списка: {str(e)}"
            self.logger.critical(error_message, exc_info=True)
            self.blacklist_update_error.emit(error_message)
