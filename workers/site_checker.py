import asyncio
import logging
from typing import List, Optional

import aiohttp
from PyQt6.QtCore import QObject, pyqtSignal

from utils.utils import DISPLAY_NAMES, get_site_by_name

DEFAULT_TIMEOUT = 5
SUCCESS_STATUS = 200
GREEN_COLOR = 'green'
RED_COLOR = 'red'
HTTP_PREFIX = "http"


class SiteCheckerWorker(QObject):
    site_checked = pyqtSignal(str, str)
    finished = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, sites: Optional[List[str]] = None) -> None:
        super().__init__()
        self.sites = sites if sites is not None else DISPLAY_NAMES
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        try:
            self.logger.debug("Запуск проверки сайтов.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.check_sites())
            loop.close()
        except Exception as e:
            error_message = f"Неожиданная ошибка при запуске проверки сайтов: {e}"
            self.logger.critical(error_message, exc_info=True)
            self.error_signal.emit(error_message)
            self.finished.emit()

    async def check_sites(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                tasks = [
                    self.check_site(session, site_name, self.get_site_url(site_name))
                    for site_name in self.sites
                ]
                self.logger.debug(f"Запуск {len(tasks)} задач проверки сайтов.")
                await asyncio.gather(*tasks)
        except Exception as e:
            error_message = f"Неизвестная ошибка при проверке сайтов: {e}"
            self.logger.critical(error_message, exc_info=True)
            self.error_signal.emit(error_message)
        finally:
            self.finished.emit()
            self.logger.debug("Проверка сайтов завершена.")

    async def check_site(self, session: aiohttp.ClientSession, site_name: str, url: str) -> None:
        color = RED_COLOR
        try:
            self.logger.debug(f"Проверка доступности сайта: {url}")
            async with session.get(url, timeout=DEFAULT_TIMEOUT) as response:
                if response.status == SUCCESS_STATUS:
                    color = GREEN_COLOR
                    self.logger.debug(f"Сайт {url} доступен.")
                else:
                    self.logger.warning(f"Сайт {url} недоступен. Статус: {response.status}")
        except aiohttp.ClientError as e:
            self.logger.error(f"Ошибка при проверке {url}: {e}")
        except asyncio.TimeoutError:
            self.logger.error(f"Тайм-аут при проверке {url}")
        except Exception as e:
            self.logger.critical(f"Неожиданная ошибка при проверке {url}: {e}", exc_info=True)
        finally:
            self.site_checked.emit(site_name, color)

    def get_site_url(self, site_name: str) -> str:
        site = get_site_by_name(site_name)
        if not site.startswith(HTTP_PREFIX):
            site = f"https://{site}"
            self.logger.debug(f"Добавлен префикс 'https://' к URL: {site}")
        return site
