import json
import logging
from typing import Dict, List
from pathlib import Path

class TranslationManager:
    """
    Управление переводами приложения. Русский — базовый язык, английский — из en.json.
    """

    def __init__(self, translations_folder: str | Path):
        """
        Инициализация менеджера переводов.

        Args:
            translations_folder: Путь к папке с файлами переводов (ожидается en.json)
        """
        self.translations_folder = Path(translations_folder)
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language: str = "ru" 
        self.available_languages: List[str] = ["ru", "en"]
        self.fallback_language: str = "en"
        self.logger = logging.getLogger(__name__)
        self.language_names: Dict[str, str] = {
            "ru": "Русский",
            "en": "English",
        }
        self._load_translations()

    def _load_translations(self) -> None:
        """
        Загрузка переводов из JSON-файлов.

        Ожидается en.json, ru.json не требуется, так как русский — базовый.
        """
        for lang_code in self.available_languages:
            if lang_code == "ru":  
                self.translations[lang_code] = {}
                continue
            file_path = self.translations_folder / f"{lang_code}.json"
            if file_path.exists():
                try:
                    self.translations[lang_code] = json.loads(file_path.read_text(encoding="utf-8"))
                    self.logger.debug(f"Загружен перевод: {file_path}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Ошибка JSON в {file_path}: {e}")
                except Exception as e:
                    self.logger.error(f"Ошибка загрузки {file_path}: {e}")
            else:
                self.logger.debug(f"Файл перевода отсутствует: {file_path}")
                self.translations[lang_code] = {}

    def set_language(self, lang_code: str) -> None:
        """
        Установка текущего языка приложения.

        Args:
            lang_code: Код языка ("ru" или "en")

        Raises:
            ValueError: Если язык не поддерживается
        """
        if lang_code not in self.available_languages:
            self.logger.warning(f"Неподдерживаемый язык: {lang_code}")
            raise ValueError(f"Язык '{lang_code}' не поддерживается")
        
        self.current_language = lang_code
        self.logger.info(f"Установлен язык: {self.language_names.get(lang_code, lang_code)}")

    def translate(self, text: str) -> str:
        """
        Перевод текста на текущий язык.

        Args:
            text: Текст на русском для перевода

        Returns:
            str: Переведённый текст или исходный русский, если перевода нет
        """
        if not text or self.current_language == "ru":  # Русский — базовый
            return text

        # Прямой перевод на текущий язык (например, en)
        if translated := self.translations.get(self.current_language, {}).get(text):
            return translated

        # Fallback на английский, если текущий язык не ru и перевод не найден
        if self.current_language != "en":
            if translated := self.translations.get(self.fallback_language, {}).get(text):
                self.logger.debug(f"Fallback перевод с 'en' для '{text}'")
                return translated

        self.logger.debug(f"Перевод для '{text}' не найден на '{self.current_language}'")
        return text

    @staticmethod
    def translate_ini_section(ini_content: str, translation_manager: "TranslationManager") -> str:
        """
        Перевод секций в INI-файле.

        Args:
            ini_content: Содержимое INI-файла
            translation_manager: Экземпляр TranslationManager

        Returns:
            str: INI-файл с переведёнными секциями
        """
        sections = [
            "[Обход блокировок для РКН]",
            "[Универсальный обход]",
            "[Обход Discord + YouTube]"
        ]
        
        for section in sections:
            translated = translation_manager.translate(section)
            if translated != section:
                ini_content = ini_content.replace(section, translated)
        
        return ini_content

    def get_available_languages(self) -> Dict[str, str]:
        """
        Получение списка доступных языков.

        Returns:
            Dict[str, str]: Словарь кодов языков и их названий
        """
        return self.language_names.copy()