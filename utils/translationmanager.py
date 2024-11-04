import os
import json
import logging

class TranslationManager:
    def __init__(self, translations_folder):
        self.translations_folder = translations_folder
        self.translations = {}
        self.current_language = 'ru'
        self.available_languages = ['ru', 'en']
        self.language_order = ['en'] 

        self.logger = logging.getLogger(self.__class__.__name__)

        self.load_translations()

        self.language_names = {
            'ru': 'Русский',
            'en': 'English',
        }

    def load_translations(self):
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

    def set_language(self, lang_code):
        if lang_code in self.available_languages:
            self.current_language = lang_code
            self.logger.info(f"Язык установлен на: {self.language_names.get(lang_code, lang_code)}")
        else:
            self.logger.warning(f"Язык '{lang_code}' не поддерживается.")

    def translate(self, text):
        if self.current_language == 'ru':
            return text 
        else:
            translated_text = self.translations.get(self.current_language, {}).get(text)
            if translated_text:
                return translated_text
            else:
                for fallback_lang in self.language_order:
                    translated_text = self.translations.get(fallback_lang, {}).get(text)
                    if translated_text:
                        return translated_text
                return text
