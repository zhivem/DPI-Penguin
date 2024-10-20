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

BLACKLISTS = [
    {
        "name": "russia-blacklist",
        "url": "https://p.thenewone.lol/domains-export.txt",
        "output_file": os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")
    },
    {
        "name": "discord-blacklist",
        "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/black/discord-blacklist.txt",
        "output_file": os.path.join(BASE_FOLDER, "black", "discord-blacklist.txt")
    },
    {
        "name": "disk-yotube",
        "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/black/disk-yotube.txt",
        "output_file": os.path.join(BASE_FOLDER, "black", "disk-yotube.txt")
    },
    {
        "name": "russia-youtube",
        "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/black/russia-youtube.txt",
        "output_file": os.path.join(BASE_FOLDER, "black", "russia-youtube.txt")
    }
]

CONFIG_UPDATE_URL = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/config/default.ini"
CONFIG_OUTPUT_FILE = os.path.join(BASE_FOLDER, "config", "default.ini")

UPDATE_TIMEOUT = 10

class Updater(QThread):
    """
    Класс Updater для проверки и загрузки обновлений приложения и черных списков.
    Наследуется от QThread для выполнения задач в отдельном потоке.
    """
    update_available = pyqtSignal(str)
    no_update = pyqtSignal()
    update_error = pyqtSignal(str)
    blacklist_updated = pyqtSignal()
    blacklist_update_error = pyqtSignal(str)
    config_updated = pyqtSignal()
    config_update_error = pyqtSignal(str)

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
        Загружает и обновляет черные списки из указанных URL. Эмитирует соответствующие
        сигналы в зависимости от результата загрузки.
        """
        success = True

        for blacklist in BLACKLISTS:
            name = blacklist["name"]
            url = blacklist["url"]
            output_file = blacklist["output_file"]

            try:
                self.logger.info(f"Начало загрузки черного списка '{name}' с {url}")
                response = requests.get(url, timeout=UPDATE_TIMEOUT)
                response.raise_for_status()
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'wb') as file:
                    file.write(response.content)
                self.logger.info(f"Загрузка черного списка '{name}' успешно завершена.")
            except requests.RequestException as e:
                error_message = f"Ошибка обновления черного списка '{name}': {str(e)}"
                self.logger.error(error_message)
                self.blacklist_update_error.emit(error_message)
                success = False
            except Exception as e:
                error_message = f"Неизвестная ошибка при обновлении черного списка '{name}': {str(e)}"
                self.logger.critical(error_message, exc_info=True)
                self.blacklist_update_error.emit(error_message)
                success = False

        if success:
            self.blacklist_updated.emit()

    def update_config(self) -> None:
        """
        Загружает и обновляет конфигурационный файл default.ini из указанного URL.
        Эмитирует соответствующие сигналы в зависимости от результата загрузки.
        """
        try:
            self.logger.info(f"Начало загрузки конфигурационного файла с {CONFIG_UPDATE_URL}")
            response = requests.get(CONFIG_UPDATE_URL, timeout=UPDATE_TIMEOUT)
            response.raise_for_status()
            os.makedirs(os.path.dirname(CONFIG_OUTPUT_FILE), exist_ok=True)
            with open(CONFIG_OUTPUT_FILE, 'wb') as file:
                file.write(response.content)
            self.logger.info("Загрузка конфигурационного файла успешно завершена.")
            self.config_updated.emit()
        except requests.RequestException as e:
            error_message = f"Ошибка обновления конфигурационного файла: {str(e)}"
            self.logger.error(error_message)
            self.config_update_error.emit(error_message)
        except Exception as e:
            error_message = f"Неизвестная ошибка при обновлении конфигурационного файла: {str(e)}"
            self.logger.critical(error_message, exc_info=True)
            self.config_update_error.emit(error_message)
