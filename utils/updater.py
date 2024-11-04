import logging
import os

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from utils.utils import (
    BASE_FOLDER,
    CURRENT_VERSION,
    get_latest_version,
    is_newer_version,
    tr
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
        "name": "disk-youtube-blacklist", 
        "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/black/disk-youtube-blacklist.txt",
        "output_file": os.path.join(BASE_FOLDER, "black", "disk-youtube-blacklist.txt")
    },
    {
        "name": "ipset-discord", 
        "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/black/ipset-discord.txt",
        "output_file": os.path.join(BASE_FOLDER, "black", "ipset-discord.txt")
    },
    {
        "name": "youtube-blacklist",
        "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/black/youtube-blacklist.txt",
        "output_file": os.path.join(BASE_FOLDER, "black", "youtube-blacklist.txt")
    }
]

CONFIG_UPDATE_URL = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/config/default.ini"
CONFIG_OUTPUT_FILE = os.path.join(BASE_FOLDER, "config", "default.ini")

UPDATE_TIMEOUT = 10

class Updater(QThread):
    update_available = pyqtSignal(str)
    no_update = pyqtSignal()
    update_error = pyqtSignal(str)
    blacklist_updated = pyqtSignal()
    blacklist_update_error = pyqtSignal(str)
    config_updated = pyqtSignal()
    config_update_error = pyqtSignal(str)

    def __init__(self, operation: str = 'check_updates') -> None:
        super().__init__()
        self.operation = operation
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        if self.operation == 'check_updates':
            self.check_for_updates()
        elif self.operation == 'update_blacklist':
            self.update_blacklist()
        elif self.operation == 'update_config':
            self.update_config()
        else:
            error_message = tr(f"Неизвестная операция: {self.operation}")
            self.logger.error(error_message)
            self.update_error.emit(error_message)

    def check_for_updates(self) -> None:
        try:
            self.logger.debug(tr("Начата проверка наличия обновлений."))
            latest_version = get_latest_version()
            if latest_version:
                if is_newer_version(latest_version, CURRENT_VERSION):
                    self.logger.info(tr(f"Доступна новая версия: {latest_version}"))
                    self.update_available.emit(latest_version)
                else:
                    self.logger.info(tr("Обновления не найдены."))
                    self.no_update.emit()
            else:
                self.logger.warning(tr("Не удалось получить последнюю версию."))
                self.no_update.emit()
        except requests.RequestException as e:
            error_message = tr("Не удалось проверить обновления. Пожалуйста, проверьте подключение к сети.")
            self.logger.error(f"{error_message} Ошибка: {e}")
            self.update_error.emit(error_message)
        except Exception as e:
            error_message = tr(f"Неизвестная ошибка при проверке обновлений: {e}")
            self.logger.critical(error_message, exc_info=True)
            self.update_error.emit(error_message)

    def update_blacklist(self) -> None:
        success = True

        for blacklist in BLACKLISTS:
            name = blacklist["name"]
            url = blacklist["url"]
            output_file = blacklist["output_file"]

            try:
                self.logger.info(tr(f"Начало загрузки черного списка '{name}' с {url}"))
                response = requests.get(url, timeout=UPDATE_TIMEOUT)
                response.raise_for_status()
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'wb') as file:
                    file.write(response.content)
                self.logger.info(tr(f"Загрузка черного списка '{name}' успешно завершена."))
            except requests.RequestException as e:
                error_message = tr(f"Ошибка обновления черного списка '{name}': {str(e)}")
                self.logger.error(error_message)
                self.blacklist_update_error.emit(error_message)
                success = False
            except Exception as e:
                error_message = tr(f"Неизвестная ошибка при обновлении черного списка '{name}': {str(e)}")
                self.logger.critical(error_message, exc_info=True)
                self.blacklist_update_error.emit(error_message)
                success = False

        if success:
            self.blacklist_updated.emit()

    def update_config(self) -> None:
        try:
            self.logger.info(tr(f"Начало загрузки конфигурационного файла с {CONFIG_UPDATE_URL}"))
            response = requests.get(CONFIG_UPDATE_URL, timeout=UPDATE_TIMEOUT)
            response.raise_for_status()
            os.makedirs(os.path.dirname(CONFIG_OUTPUT_FILE), exist_ok=True)
            with open(CONFIG_OUTPUT_FILE, 'wb') as file:
                file.write(response.content)
            self.logger.info(tr("Загрузка конфигурационного файла успешно завершена."))
            self.config_updated.emit()
        except requests.RequestException as e:
            error_message = tr(f"Ошибка обновления конфигурационного файла: {str(e)}")
            self.logger.error(error_message)
            self.config_update_error.emit(error_message)
        except Exception as e:
            error_message = tr(f"Неизвестная ошибка при обновлении конфигурационного файла: {str(e)}")
            self.logger.critical(error_message, exc_info=True)
            self.config_update_error.emit(error_message)
