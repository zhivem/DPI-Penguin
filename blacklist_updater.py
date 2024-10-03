import os
import requests
from datetime import datetime
from utils import BASE_FOLDER

# Функция для обновления черного списка доменов.
def update_blacklist():
    # URL, откуда загружается список доменов.
    url = "https://p.thenewone.lol/domains-export.txt"
    # Путь для сохранения черного списка.
    output_file = os.path.join(BASE_FOLDER, "russia-blacklist.txt")
    # Путь для логирования загрузок.
    log_file = os.path.join(BASE_FOLDER, "download_log.txt")

    # Вспомогательная функция для записи сообщений в лог.
    def log_message(message):
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"{message}\n")  # Запись сообщения в лог

    # Логирование начала процесса загрузки.
    log_message("====================================")
    log_message(f"[INFO] Starting download at {datetime.now()}")

    try:
        # Выполнение запроса для получения файла по указанному URL.
        response = requests.get(url)
        response.raise_for_status()  # Проверка на ошибки запроса
        # Сохранение загруженного контента в файл.
        with open(output_file, 'wb') as file:
            file.write(response.content)
        # Логирование успешной загрузки.
        log_message(f"[INFO] Download completed successfully at {datetime.now()}")
        return True
    except requests.RequestException as e:
        # Логирование ошибки при загрузке.
        log_message(f"[ERROR] Failed to download file from {url} at {datetime.now()}: {e}")
        return False
