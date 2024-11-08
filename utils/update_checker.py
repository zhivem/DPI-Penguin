import configparser
import logging
import os

import requests
from packaging.version import parse as parse_version

from utils.utils import BASE_FOLDER, CURRENT_VERSION, tr

class UpdateChecker:
    BLACKLISTS = [
        {
            "name": "russia-blacklist",
            "url": "https://p.thenewone.lol/domains-export.txt",
            "output_file": os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")
        },
        {
            "name": "discord-blacklist",
            "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/black/discord-blacklist.txt",
            "output_file": os.path.join(BASE_FOLDER, "black", "discord-blacklist.txt")
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
        },
        {
            "name": "youtube-blacklist",
            "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/black/youtube-blacklist.txt",
            "output_file": os.path.join(BASE_FOLDER, "black", "youtube-blacklist.txt")
        }
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.local_versions = {}
        self.remote_versions = {}

    def get_local_versions(self):
        version_file_path = os.path.join(BASE_FOLDER, "setting_version", "version_config.ini")
        versions = {}
        if os.path.exists(version_file_path):
            config = configparser.ConfigParser()
            config.read(version_file_path, encoding='utf-8')
            if 'VERSION' in config:
                versions = {k: v.strip() for k, v in config['VERSION'].items()}
                versions.setdefault('ver_programm', CURRENT_VERSION)
            else:
                self.logger.warning(tr("Файл версии не содержит секцию [VERSION]"))
        else:
            self.logger.warning(tr(f"Локальный файл версии не найден: {version_file_path}"))
            versions['ver_programm'] = CURRENT_VERSION
        self.local_versions = versions

    def get_remote_versions(self):
        versions = {}
        version_url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/setting_version/version_config.ini"
        try:
            response = requests.get(version_url, timeout=10)
            if response.status_code == 200:
                config = configparser.ConfigParser()
                config.read_string(response.text)
                if 'VERSION' in config:
                    versions = {k: v.strip() for k, v in config['VERSION'].items()}
                else:
                    self.logger.warning(tr("Удалённый файл версии не содержит секцию [VERSION]"))
            else:
                self.logger.warning(tr(f"Не удалось получить удалённую версию. Код ответа: {response.status_code}"))
        except requests.RequestException as e:
            self.logger.error(tr(f"Ошибка запроса к GitHub: {e}"))
        self.remote_versions = versions

    def is_update_available(self, component):
        local_version = self.local_versions.get(component)
        remote_version = self.remote_versions.get(component)
        if local_version and remote_version:
            return self.is_newer_version(remote_version, local_version)
        return False

    def is_newer_version(self, latest, current):
        try:
            return parse_version(latest) > parse_version(current)
        except Exception as e:
            self.logger.error(f"Ошибка при сравнении версий: {e}")
            return False

    def update_blacklists(self):
        success = True
        for blacklist in self.BLACKLISTS:
            name = blacklist['name']
            url = blacklist['url']
            output_file = blacklist['output_file']
            self.logger.info(tr(f"Обновление {name} из {url}"))
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    self.logger.info(tr(f"{name} успешно обновлен."))
                else:
                    self.logger.warning(tr(f"Не удалось обновить {name}. Статус код: {response.status_code}"))
                    success = False
            except Exception as e:
                self.logger.error(tr(f"Ошибка при обновлении {name}: {e}"))
                success = False
        return success
