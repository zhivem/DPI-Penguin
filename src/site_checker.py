import logging
import asyncio

from PyQt5.QtCore import QObject, pyqtSignal

import aiohttp

from utils import DISPLAY_NAMES, get_site_by_name


class SiteCheckerWorker(QObject):
    site_checked = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, sites=None):
        super().__init__()
        self.sites = sites if sites is not None else DISPLAY_NAMES

    def run(self):
        asyncio.run(self.check_sites())

    async def check_sites(self):
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.check_site(session, site_name, self.get_site_url(site_name))
                for site_name in self.sites
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        self.finished.emit()

    async def check_site(self, session, site_name, url):
        try:
            logging.debug(f"Проверка {url}")
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    color = 'green'
                else:
                    color = 'red'
        except aiohttp.ClientError as e:
            logging.error(f"Ошибка при проверке {url}: {e}")
            color = 'red'
        except asyncio.TimeoutError:
            logging.error(f"Тайм-аут при проверке {url}")
            color = 'red'
        except Exception as e:
            logging.critical(f"Неожиданная ошибка при проверке {url}: {e}", exc_info=True)
            color = 'red'
        self.site_checked.emit(site_name, color)

    def get_site_url(self, site_name):
        site = get_site_by_name(site_name)
        return site if site.startswith("http") else f"https://{site}"
