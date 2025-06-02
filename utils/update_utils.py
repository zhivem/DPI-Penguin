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
        self.logger = logging.getLogger(__name__)
        self.local_versions: Dict[str, str] = {}
        self.remote_versions: Dict[str, str] = {}

    def get_local_versions(self) -> None:
        """Читает локальные версии из version_config.ini."""
        version_file = os.path.join(BASE_FOLDER, "setting_version", "version_config.ini")
        self.local_versions = {}
        if os.path.exists(version_file):
            try:
                config = configparser.ConfigParser()
                config.read(version_file, encoding='utf-8')
                if 'VERSION' in config:
                    self.local_versions = {k: v.strip() for k, v in config['VERSION'].items()}
                    self.local_versions.setdefault('ver_programm', CURRENT_VERSION)
                else:
                    self.logger.warning(f"Файл {version_file} не содержит секцию [VERSION]")
            except Exception as e:
                self.logger.exception(f"Ошибка при чтении локального файла версий: {e}")
        else:
            self.logger.warning(f"Локальный файл версий не найден: {version_file}")
            self.local_versions['ver_programm'] = CURRENT_VERSION

    def get_remote_versions(self) -> None:
        """Получает версии с GitHub."""
        url = f"https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/setting_version/version_config.ini?t={int(time.time())}"
        self.remote_versions = {}
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            config = configparser.ConfigParser()
            config.read_string(response.text)
            if 'VERSION' in config:
                self.remote_versions = {k: v.strip() for k, v in config['VERSION'].items()}
            else:
                self.logger.warning("Удалённый файл версий не содержит секцию [VERSION]")
        except Exception as e:
            self.logger.exception(f"Ошибка при получении удалённых версий: {e}")

    def is_update_available(self, component: str) -> bool:
        """Проверяет, доступно ли обновление для компонента."""
        local = self.local_versions.get(component)
        remote = self.remote_versions.get(component)
        if local and remote:
            return self.is_newer_version(remote, local)
        self.logger.warning(f"Нет информации о версиях для '{component}': локальная={local}, удалённая={remote}")
        return False

    @staticmethod
    def is_newer_version(latest: str, current: str) -> bool:
        """Сравнивает версии."""
        try:
            return parse_version(latest) > parse_version(current)
        except Exception:
            return False

    def download_and_update(self, component: str, dialog=None) -> bool:
        """Скачивает и обновляет компонент."""
        info = self.COMPONENTS.get(component)
        if not info:
            self.logger.error(f"Неизвестный компонент: '{component}'")
            return False
        try:
            # Pre-update actions
            for method_name in info.get('pre_update', []):
                method = getattr(self, method_name, None)
                if method:
                    args = info.get('pre_update_args', {}).get(method_name, {})
                    method(**args)
                else:
                    self.logger.warning(f"Метод '{method_name}' не найден")

            # Download
            self.logger.info(f"Скачивание {component} с {info['url']}")
            response = requests.get(info['url'], stream=True, timeout=30)
            response.raise_for_status()
            os.makedirs(os.path.dirname(info['destination']), exist_ok=True)

            if info.get('extract'):
                self._extract_zip(response.content, os.path.dirname(info['destination']))
            else:
                self._write_file(info['destination'], response.text)

            self.logger.info(f"{component} успешно обновлён")

            # Post-update actions
            if info.get('post_update') == "emit_config_updated":
                if dialog and hasattr(dialog, 'config_updated_signal'):
                    dialog.config_updated_signal.emit()
                self.emit_config_updated()

            self.update_local_version_file()
            return True
        except Exception as e:
            self.logger.exception(f"Ошибка при обновлении {component}: {e}")
            return False

    def update_local_version_file(self) -> None:
        """Обновляет локальный version_config.ini."""
        url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/setting_version/version_config.ini"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            version_dir = os.path.join(BASE_FOLDER, "setting_version")
            os.makedirs(version_dir, exist_ok=True)
            self._write_file(os.path.join(version_dir, "version_config.ini"), response.text)
            self.logger.info("Локальный version_config.ini успешно обновлён")
        except Exception as e:
            self.logger.exception(f"Ошибка при обновлении version_config.ini: {e}")

    def update_blacklists(self) -> bool:
        """Обновляет все чёрные списки."""
        self.logger.info("Обновление чёрных списков")
        success = True
        for bl in self.BLACKLISTS:
            try:
                self._download_and_write(bl['url'], bl['output_file'])
                self.logger.info(f"Чёрный список '{bl['name']}' успешно обновлён")
            except Exception as e:
                self.logger.exception(f"Ошибка при обновлении '{bl['name']}': {e}")
                success = False
        return success

    def terminate_process(self, process_name: str) -> None:
        """Завершает процесс."""
        self.logger.info(f"Завершение процесса '{process_name}'")
        ProcessUtils.terminate_process(process_name)

    def stop_service(self, service_name: str) -> None:
        """Останавливает службу."""
        self.logger.info(f"Остановка службы '{service_name}'")
        ProcessUtils.stop_service(service_name)

    def emit_config_updated(self) -> None:
        """Эмитирует сигнал обновления конфигурации."""
        self.logger.info("Сигнал обновления конфигурации")
        self.config_updated_signal.emit()

    # --- Вспомогательные методы ---
    def _extract_zip(self, content: bytes, target_dir: str) -> None:
        """Распаковывает zip-архив в указанную директорию."""
        with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
            zip_ref.extractall(target_dir)

    def _write_file(self, path: str, text: str) -> None:
        """Записывает текст в файл."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _download_and_write(self, url: str, path: str) -> None:
        """Скачивает содержимое url и записывает в файл."""
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        self._write_file(path, response.text)
