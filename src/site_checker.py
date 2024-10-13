import asyncio
import logging

import aiohttp
from PyQt5.QtCore import QObject, pyqtSignal

from utils import DISPLAY_NAMES, get_site_by_name


class SiteCheckerWorker(QObject):
    """
    Класс для асинхронной проверки доступности сайтов.

    Сигналы:
        site_checked (str, str): Передает имя сайта и цвет статуса.
        finished (): Уведомляет об окончании проверки.
    """

    site_checked = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, sites=None, retries=3):
        super().__init__()
        self.sites = list(sites) if sites is not None else DISPLAY_NAMES
        self.retries = retries  # Количество попыток при неудачной проверке

    def run(self):
        """Запускает асинхронную проверку сайтов."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.check_sites())
        loop.close()

    async def check_sites(self):
        """Асинхронно проверяет доступность сайтов."""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.check_site(session, site_name, self.get_site_url(site_name))
                for site_name in self.sites
            ]
            await asyncio.gather(*tasks)
        self.finished.emit()

    async def check_site(self, session, site_name, url):
        """Проверяет доступность одного сайта с ретраем."""
        for attempt in range(self.retries):
            try:
                logging.debug(f"Проверка {url}, попытка {attempt + 1}")
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        color = 'green'
                    else:
                        color = 'red'
                    break  # Успешная проверка, прерываем попытки
            except aiohttp.ClientError as e:
                logging.error(f"Ошибка при проверке {url}: {e}")
                color = 'red'
            except asyncio.TimeoutError:
                logging.error(f"Тайм-аут при проверке {url}")
                color = 'red'
            except Exception as e:
                logging.critical(f"Неожиданная ошибка при проверке {url}: {e}", exc_info=True)
                color = 'red'
            else:
                break  # Успешная проверка, выход из цикла
        self.site_checked.emit(site_name, color)

    def get_site_url(self, site_name):
        """Получает полный URL сайта по его имени."""
        site = get_site_by_name(site_name)
        return site if site.startswith("http") else f"https://{site}"
