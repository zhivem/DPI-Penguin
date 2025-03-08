import configparser
import io
import logging
import os
import zipfile
import time
from typing import Dict, List, Optional
import requests
from packaging.version import parse as parse_version
from PyQt6.QtCore import QObject, pyqtSignal

from utils.process_utils import ProcessUtils
from utils.utils import BASE_FOLDER, CURRENT_VERSION, tr


class UpdateChecker(QObject):
    config_updated_signal = pyqtSignal()

    BLACKLISTS: List[Dict[str, str]] = [
        {
            "name": "russia-blacklist",
            "url": "https://p.thenewone.lol/domains-export.txt",
            "output_file": os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")
        },
        {
            "name": "discord-blacklist",
            "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/black/universal.txt",
            "output_file": os.path.join(BASE_FOLDER, "black", "universal.txt")
        },
        {
            "name": "disk-youtube-blacklist",
            "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/black/disk-youtube-blacklist.txt",
            "output_file": os.path.join(BASE_FOLDER, "black", "disk-youtube-blacklist.txt")
        },
        {
            "name": "ipset-discord",
            "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/black/ipset-discord.txt",
            "output_file": os.path.join(BASE_FOLDER, "black", "ipset-discord.txt")
        }
    ]

    COMPONENTS: Dict[str, Dict[str, Optional[str]]] = {
        "zapret": {
            "url": "https://github.com/zhivem/DPI-Penguin/raw/refs/heads/main/zapret/zapret.zip",
            "destination": os.path.join(BASE_FOLDER, "zapret", "zapret.zip"),
            "extract": True,
            "pre_update": ["terminate_process", "stop_service"],
            "pre_update_args": {
                "terminate_process": {"process_name": "winws.exe"},
                "stop_service": {"service_name": "WinDivert"}
            }
        },
        "config": {
            "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/config/default.ini",
            "destination": os.path.join(BASE_FOLDER, "config", "default.ini"),
            "extract": False,
            "post_update": "emit_config_updated"
        }
    }

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)  # Используем __name__ для соответствия main.py
        self.logger.info("Инициализация UpdateChecker")
        self.local_versions: Dict[str, str] = {}
        self.remote_versions: Dict[str, str] = {}

    def get_local_versions(self) -> None:
        """Получение локальных версий компонентов из файла version_config.ini."""
        version_file_path = os.path.join(BASE_FOLDER, "setting_version", "version_config.ini")
        versions: Dict[str, str] = {}
        if os.path.exists(version_file_path):
            try:
                config = configparser.ConfigParser()
                config.read(version_file_path, encoding='utf-8')
                if 'VERSION' in config:
                    versions = {k: v.strip() for k, v in config['VERSION'].items()}
                    versions.setdefault('ver_programm', CURRENT_VERSION)
                else:
                    self.logger.warning(f"Файл {version_file_path} не содержит секцию [VERSION]")
            except Exception as e:
                self.logger.exception(f"Ошибка при чтении локального файла версий {version_file_path}: {e}")
        else:
            self.logger.warning(f"Локальный файл версий не найден: {version_file_path}")
            versions['ver_programm'] = CURRENT_VERSION
        self.local_versions = versions

    def get_remote_versions(self) -> None:
        """Получение удалённых версий компонентов с GitHub."""
        versions: Dict[str, str] = {}
        version_url = f"https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/setting_version/version_config.ini?t={int(time.time())}"
        try:
            response = requests.get(version_url, timeout=10)
            response.raise_for_status()
            config = configparser.ConfigParser()
            config.read_string(response.text)
            if 'VERSION' in config:
                versions = {k: v.strip() for k, v in config['VERSION'].items()}
            else:
                self.logger.warning("Удалённый файл версий не содержит секцию [VERSION]")
        except requests.RequestException as e:
            self.logger.exception(f"Ошибка при запросе удалённых версий: {e}")
        self.remote_versions = versions

    def is_update_available(self, component: str) -> bool:
        """Проверка наличия обновления для компонента."""
        local_version = self.local_versions.get(component)
        remote_version = self.remote_versions.get(component)
        if local_version and remote_version:
            result = self.is_newer_version(remote_version, local_version)
            return result
        self.logger.warning(f"Версии для '{component}' неполные: локальная={local_version}, удалённая={remote_version}")
        return False

    def is_newer_version(self, latest: str, current: str) -> bool:
        """Сравнение версий."""
        try:
            result = parse_version(latest) > parse_version(current)
            return result
        except Exception as e:
            self.logger.exception(f"Ошибка при сравнении версий {latest} и {current}: {e}")
            return False

    def download_and_update(self, component: str, dialog=None) -> bool:
        """Скачивание и обновление компонента."""
        component_info = self.COMPONENTS.get(component)
        if not component_info:
            self.logger.error(f"Неизвестный компонент для обновления: '{component}'")
            return False
        try:
            if 'pre_update' in component_info:
                for method_name in component_info['pre_update']:
                    method = getattr(self, method_name, None)
                    if method:
                        args = component_info.get('pre_update_args', {}).get(method_name, {})
                        method(**args)
                    else:
                        self.logger.warning(f"Метод '{method_name}' не найден в UpdateChecker")

            self.logger.info(f"Скачивание {component} с {component_info['url']}")
            response = requests.get(component_info['url'], stream=True, timeout=30)
            response.raise_for_status()
            os.makedirs(os.path.dirname(component_info['destination']), exist_ok=True)
            if component_info.get('extract'):
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    zip_ref.extractall(os.path.dirname(component_info['destination']))
            else:
                with open(component_info['destination'], "w", encoding='utf-8') as f:
                    f.write(response.text)
            self.logger.info(f"{component} успешно обновлён")

            if 'post_update' in component_info and component_info['post_update'] == "emit_config_updated":
                if dialog and hasattr(dialog, 'config_updated_signal'):
                    dialog.config_updated_signal.emit()
                self.emit_config_updated()

            self.update_local_version_file()
            return True
        except requests.RequestException as e:
            self.logger.exception(f"Ошибка при скачивании {component}: {e}")
            return False
        except Exception as e:
            self.logger.exception(f"Ошибка при обновлении {component}: {e}")
            return False

    def update_local_version_file(self) -> None:
        """Обновление локального файла версий."""
        self.logger.info("Обновление локального файла version_config.ini")
        version_url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/setting_version/version_config.ini"
        try:
            response = requests.get(version_url, timeout=10)
            response.raise_for_status()
            version_dir = os.path.join(BASE_FOLDER, "setting_version")
            os.makedirs(version_dir, exist_ok=True)
            local_version_file = os.path.join(version_dir, "version_config.ini")
            with open(local_version_file, "w", encoding='utf-8') as f:
                f.write(response.text)
            self.logger.info("Локальный version_config.ini успешно обновлён")
        except requests.RequestException as e:
            self.logger.exception(f"Ошибка при скачивании version_config.ini: {e}")
        except Exception as e:
            self.logger.exception(f"Ошибка при записи version_config.ini: {e}")

    def update_blacklists(self) -> bool:
        """Обновление чёрных списков."""
        self.logger.info("Начало обновления чёрных списков")
        success = True
        for blacklist in self.BLACKLISTS:
            name = blacklist['name']
            url = blacklist['url']
            output_file = blacklist['output_file']
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                self.logger.info(f"Чёрный список '{name}' успешно обновлён")
            except requests.RequestException as e:
                self.logger.exception(f"Ошибка при скачивании '{name}': {e}")
                success = False
            except Exception as e:
                self.logger.exception(f"Ошибка при записи '{name}': {e}")
                success = False
        self.logger.info(f"Обновление чёрных списков завершено, успех: {success}")
        return success

    def terminate_process(self, process_name: str) -> None:
        """Завершение процесса через ProcessUtils."""
        self.logger.info(f"Запрос на завершение процесса '{process_name}'")
        ProcessUtils.terminate_process(process_name)

    def stop_service(self, service_name: str) -> None:
        """Остановка службы через ProcessUtils."""
        self.logger.info(f"Запрос на остановку службы '{service_name}'")
        ProcessUtils.stop_service(service_name)

    def emit_config_updated(self) -> None:
        """Эмит сигнала обновления конфигурации."""
        self.logger.info("Эмит сигнала обновления конфигурации")
        self.config_updated_signal.emit()