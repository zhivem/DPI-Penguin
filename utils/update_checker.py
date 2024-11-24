import configparser
import io
import logging
import os
import zipfile
import time
from typing import Dict, List, Optional

import psutil
import requests
import win32service
import win32serviceutil
import winerror
from packaging.version import parse as parse_version
from PyQt6.QtCore import QObject, pyqtSignal 

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
        super().__init__()  # Инициализируем QObject
        self.logger = logging.getLogger(self.__class__.__name__)
        self.local_versions: Dict[str, str] = {}
        self.remote_versions: Dict[str, str] = {}

    def get_local_versions(self) -> None:
        version_file_path = os.path.join(BASE_FOLDER, "setting_version", "version_config.ini")
        versions: Dict[str, str] = {}
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

    def get_remote_versions(self) -> None:
        versions: Dict[str, str] = {}
        version_url = f"https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/setting_version/version_config.ini?t={int(time.time())}"
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

    def is_update_available(self, component: str) -> bool:
        local_version = self.local_versions.get(component)
        remote_version = self.remote_versions.get(component)
        if local_version and remote_version:
            return self.is_newer_version(remote_version, local_version)
        return False

    def is_newer_version(self, latest: str, current: str) -> bool:
        try:
            return parse_version(latest) > parse_version(current)
        except Exception as e:
            self.logger.error(f"Ошибка при сравнении версий: {e}")
            return False

    def download_and_update(self, component: str, dialog=None) -> bool:
        component_info = self.COMPONENTS.get(component)
        if not component_info:
            self.logger.error(tr(f"Неизвестный компонент для обновления: {component}"))
            return False
        try:
            
            if 'pre_update' in component_info:
                for method_name in component_info['pre_update']:
                    method = getattr(self, method_name, None)
                    if method:
                        args = component_info.get('pre_update_args', {}).get(method_name, {})
                        method(**args)

            self.logger.info(tr(f"Скачивание {component} с {component_info['url']}"))
            response = requests.get(component_info['url'], stream=True, timeout=30)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(component_info['destination']), exist_ok=True)
                if component_info.get('extract'):
                    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                        zip_ref.extractall(os.path.dirname(component_info['destination']))
                else:
                    with open(component_info['destination'], "w", encoding='utf-8') as f:
                        f.write(response.text)
                self.logger.info(tr(f"{component} успешно обновлён."))

                # Обработка post_update
                if 'post_update' in component_info and component_info['post_update'] == "emit_config_updated":
                    if dialog and hasattr(dialog, 'config_updated_signal'):
                        dialog.config_updated_signal.emit()
                        self.emit_config_updated()

                self.update_local_version_file()
                return True
            else:
                self.logger.warning(tr(f"Не удалось скачать {component}. Статус код: {response.status_code}"))
                return False
        except Exception as e:
            self.logger.error(tr(f"Ошибка при обновлении {component}: {e}"))
            return False

    def update_local_version_file(self) -> None:
        self.logger.info(tr("Обновление локального version_config.ini..."))
        try:
            version_url = "https://raw.githubusercontent.com/zhivem/DPI-Penguin/main/setting_version/version_config.ini"
            response = requests.get(version_url, timeout=10)
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
            self.logger.error(tr(f"Произошла ошибка при обновлении version_config.ini: {e}"))
            raise e

    def update_blacklists(self) -> bool:
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
                    self.logger.info(tr(f"{name} успешно обновлён."))
                else:
                    self.logger.warning(tr(f"Не удалось обновить {name}. Статус код: {response.status_code}"))
                    success = False
            except Exception as e:
                self.logger.error(tr(f"Ошибка при обновлении {name}: {e}"))
                success = False
        return success

    def terminate_process(self, process_name: str) -> None:
        try:
            self.logger.info(tr(f"Завершение процесса {process_name}..."))
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    self.logger.info(tr(f"Попытка завершить процесс {process_name} с PID {proc.info['pid']}"))
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                        self.logger.info(tr(f"Процесс {process_name} успешно завершён."))
                    except psutil.TimeoutExpired:
                        self.logger.warning(tr(f"Процесс {process_name} не завершился вовремя, пытаемся принудительно завершить."))
                        proc.kill()
                        proc.wait(timeout=5)
                        self.logger.info(tr(f"Процесс {process_name} принудительно завершён."))
        except Exception as e:
            self.logger.error(tr(f"Ошибка при завершении процесса {process_name}: {e}"))
            raise e

    def stop_service(self, service_name: str) -> None:
        try:
            self.logger.info(tr(f"Остановка службы {service_name}..."))
            service_status = win32serviceutil.QueryServiceStatus(service_name)
            if service_status[1] == win32service.SERVICE_RUNNING:
                win32serviceutil.StopService(service_name)
                self.logger.info(tr(f"Служба {service_name} отправлена на остановку."))
                # Ожидание остановки службы
                for _ in range(15):
                    service_status = win32serviceutil.QueryServiceStatus(service_name)
                    if service_status[1] == win32service.SERVICE_STOPPED:
                        self.logger.info(tr(f"Служба {service_name} успешно остановлена."))
                        break
                    time.sleep(1)
                else:
                    self.logger.warning(tr(f"Служба {service_name} не остановилась вовремя."))
            else:
                self.logger.info(tr(f"Служба {service_name} не запущена."))
        except Exception as e:
            if hasattr(e, 'winerror') and e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
                self.logger.warning(tr(f"Служба {service_name} не установлена."))
            else:
                self.logger.error(tr(f"Ошибка при остановке службы {service_name}: {e}"))
                raise e

    def emit_config_updated(self) -> None:
        """
        Метод для эмита сигнала обновления конфигурации.
        """
        self.logger.info(tr("Эмит сигнал обновления конфигурации."))
        self.config_updated_signal.emit()
