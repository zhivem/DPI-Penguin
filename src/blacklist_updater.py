import os
import requests
from datetime import datetime
from utils import BASE_FOLDER

def update_blacklist():
    url = "https://p.thenewone.lol/domains-export.txt"
    output_file = os.path.join(BASE_FOLDER, "black", "russia-blacklist.txt")
    log_file = os.path.join(BASE_FOLDER, "download_log.txt")

    def log_message(message):
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"{message}\n")

    log_message("====================================")
    log_message(f"[ИНФО] Начало загрузки в {datetime.now()}")

    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(output_file, 'wb') as file:
            file.write(response.content)
        log_message(f"[ИНФО] Загрузка успешно завершена в {datetime.now()}")
        return True
    except requests.RequestException as e:
        log_message(f"[ОШИБКА] Не удалось загрузить файл с {url} в {datetime.now()}: {e}")
        return False
