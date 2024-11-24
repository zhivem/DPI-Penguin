import json
import logging
import os
from typing import Dict, List


class TranslationManager:
    """
    Класс для управления переводами приложения.
    """

    def __init__(self, translations_folder: str):
        """
        Инициализирует менеджер переводов.

        :param translations_folder: Путь к папке с файлами переводов.
        """
        self.translations_folder = translations_folder
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language: str = 'ru'
        self.available_languages: List[str] = ['ru', 'en']
        self.language_order: List[str] = ['en'] 
        self.logger = logging.getLogger(self.__class__.__name__)
        self.language_names: Dict[str, str] = {
            'ru': 'Русский',
            'en': 'English',
        }
        self.load_translations()

    def load_translations(self) -> None:
        """
        Загружает файлы переводов из указанной папки.
        """
        for lang_code in self.language_order:
            filename = f"{lang_code}.json"
            file_path = os.path.join(self.translations_folder, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                        self.logger.info(f"Файл перевода загружен: {file_path}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Ошибка декодирования JSON в файле {file_path}: {e}")
            else:
                self.logger.warning(f"Файл перевода не найден: {file_path}")

    def set_language(self, lang_code: str) -> None:
        """
        Устанавливает текущий язык приложения.

        :param lang_code: Код языка для установки (например, 'en', 'ru').
        """
        if lang_code in self.available_languages:
            self.current_language = lang_code
            self.logger.info(f"Язык установлен на: {self.language_names.get(lang_code, lang_code)}")
        else:
            self.logger.warning(f"Язык '{lang_code}' не поддерживается")

    def translate(self, text: str) -> str:
        """
        Переводит заданный текст на текущий язык.

        :param text: Текст для перевода.
        :return: Переведённый текст или оригинальный, если перевод не найден.
        """
        if self.current_language == 'ru':
            return text

        # Попытка перевести на текущий язык
        translated_text = self.translations.get(self.current_language, {}).get(text)
        if translated_text:
            return translated_text

        # Фолбэк на другие языки в указанном порядке
        for fallback_lang in self.language_order:
            translated_text = self.translations.get(fallback_lang, {}).get(text)
            if translated_text:
                return translated_text

        # Если перевод не найден, вернуть оригинальный текст
        return text
