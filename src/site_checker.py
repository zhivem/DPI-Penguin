from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSignal
import requests
import logging
from utils import SITES, DISPLAY_NAMES, get_site_by_name

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class SiteCheckerWorker(QObject):
    site_checked = pyqtSignal(str, str)
    finished = pyqtSignal()           

    def __init__(self, sites=None):
        super().__init__()
        self.sites = sites if sites is not None else DISPLAY_NAMES  

    def run(self):
        for site_name in self.sites:
            url = self.get_site_url(site_name)  
            try:
                logging.debug(f"Проверка {url}")
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    color = 'green'
                else:
                    color = 'red'
            except requests.RequestException as e:
                logging.error(f"Ошибка при проверке {url}: {e}")
                color = 'red'
            self.site_checked.emit(site_name, color)
        self.finished.emit()

    def get_site_url(self, site_name):
        site = get_site_by_name(site_name) 
        if not site.startswith("http"):
            return f"https://{site}"
        return site
