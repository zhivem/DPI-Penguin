import configparser
import logging
import os
import zipfile
import io
import psutil
import win32serviceutil
import win32service
import winerror

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

    COMPONENTS = {
        "zapret": {
            "url": "https://github.com/zhivem/DPI-Penguin/raw/refs/heads/main/zapret/zapret.zip",
            "destination": os.path.join(BASE_FOLDER, "zapret", "zapret.zip"),
            "extract": True,
            "pre_update": ["terminate_process", "stop_service"],
            "pre_update_args": {"process_name": "winws.exe", "service_name": "WinDivert"}
        },
        "config": {
            "url": "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/config/default.ini",
            "destination": os.path.join(BASE_FOLDER, "config", "default.ini"),
            "extract": False,
            "post_update": "emit_config_updated"
        }
    }

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

    def download_and_update(self, component, dialog=None):
        component_info = self.COMPONENTS.get(component)
        if not component_info:
            self.logger.error(tr(f"Неизвестный компонент для обновления: {component}"))
            return False
        try:
            self.logger.info(tr(f"Скачивание {component} с {component_info['url']}"))
            response = requests.get(component_info['url'], stream=True)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(component_info['destination']), exist_ok=True)
                if component_info.get('extract'):
                    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                        zip_ref.extractall(os.path.dirname(component_info['destination']))
                else:
                    with open(component_info['destination'], "w", encoding='utf-8') as f:
                        f.write(response.text)
                self.logger.info(tr(f"{component} успешно обновлён."))

                if 'pre_update' in component_info:
                    method = getattr(dialog, component_info['pre_update'][0], None)
                    if method:
                        method(**component_info['pre_update_args'])

                if 'post_update' in component_info and component_info['post_update'] == "emit_config_updated":
                    if hasattr(dialog, 'config_updated_signal'):
                        dialog.config_updated_signal.emit()

                self.update_local_version_file()
                return True
            else:
                self.logger.warning(tr(f"Не удалось скачать {component}. Статус код: {response.status_code}"))
                return False
        except Exception as e:
            self.logger.error(tr(f"Ошибка при обновлении {component}: {e}"))
            return False

    def update_local_version_file(self):
        self.logger.info(tr("Обновление локального version_config.ini..."))
        try:
            version_url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/refs/heads/main/setting_version/version_config.ini"
            response = requests.get(version_url)
            if response.status_code == 200:
                version_dir = os.path.join(BASE_FOLDER, "setting_version")
                os.makedirs(version_dir, exist_ok=True)
                local_version_file = os.path.join(version_dir, "version_config.ini")
                with open(local_version_file, "w", encoding='utf-8') as f:
                    f.write(response.text)
                self.logger.info(tr("Локальный version_config.ini успешно обновлён."))
            else:
                self.logger.warning(tr(f"Не удалось скачать version_config.ini. Статус код: {response.status_code}"))
        except Exception as e:
            self.logger.error(tr(f"Произошла ошибка при обновлении version_zapret.ini: {e}"))
            raise e

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

    def terminate_process(self, process_name):
        try:
            self.logger.info(tr(f"Завершение процесса {process_name}..."))
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    proc.terminate()
                    proc.wait(timeout=5)
                    self.logger.info(tr(f"Процесс {process_name} успешно завершён."))
        except Exception as e:
            self.logger.error(tr(f"Ошибка при завершении процесса {process_name}: {e}"))
            raise e

    def stop_service(self, service_name):
        try:
            self.logger.info(tr(f"Остановка службы {service_name}..."))
            service_status = win32serviceutil.QueryServiceStatus(service_name)
            if service_status[1] == win32service.SERVICE_RUNNING:
                win32serviceutil.StopService(service_name)
                self.logger.info(tr(f"Служба {service_name} успешно остановлена."))
            else:
                self.logger.info(tr(f"Служба {service_name} не запущена."))
        except Exception as e:
            if hasattr(e, 'winerror') and e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
                self.logger.warning(tr(f"Служба {service_name} не установлена."))
            else:
                self.logger.error(tr(f"Ошибка при остановке службы {service_name}: {e}"))
                raise e

    def emit_config_updated(self):
        pass
