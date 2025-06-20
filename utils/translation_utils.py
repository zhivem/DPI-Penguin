import json
import logging
from typing import Dict, List, Union
from pathlib import Path


class TranslationManager:
    """
    Управление переводами приложения.
    Русский — базовый язык (переводы отсутствуют),
    английский — загружается из en.json.
    """

    def __init__(self, translations_folder: Union[str, Path]):
        self.translations_folder = Path(translations_folder)
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language: str = "ru"
        self.available_languages: List[str] = ["ru", "en"]
        self.fallback_language: str = "en"
        self.language_names: Dict[str, str] = {
            "ru": "Русский",
            "en": "English",
        }
        self.logger = logging.getLogger("dpipenguin")
        self.logger.info(f"Инициализация TranslationManager с папкой: {self.translations_folder}")
        self._load_translations()

    def _load_translations(self) -> None:
        """Загружает переводы из JSON-файлов, кроме русского."""
        for lang_code in self.available_languages:
            if lang_code == "ru":
                self.translations[lang_code] = {}
                continue
            file_path = self.translations_folder / f"{lang_code}.json"
            if not file_path.exists():
                self.logger.warning(f"Файл перевода для '{lang_code}' отсутствует: {file_path}")
                self.translations[lang_code] = {}
                continue
            try:
                with file_path.open(encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)
                self.logger.info(f"Загружен перевод для '{lang_code}' из {file_path}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Ошибка JSON в {file_path}: {e}")
                self.translations[lang_code] = {}
            except Exception as e:
                self.logger.error(f"Ошибка при загрузке {file_path}: {e}")
                self.translations[lang_code] = {}

    def set_language(self, lang_code: str) -> None:
        """Устанавливает текущий язык, если он поддерживается."""
        if lang_code not in self.available_languages:
            self.logger.warning(f"Попытка установить неподдерживаемый язык: {lang_code}")
            raise ValueError(f"Язык '{lang_code}' не поддерживается")
        old_lang = self.current_language
        self.current_language = lang_code
        self.logger.info(f"Язык изменён с '{old_lang}' на '{self.language_names.get(lang_code, lang_code)}'")

    def translate(self, text: str) -> str:
        """
        Переводит текст на текущий язык.
        Возвращает исходный текст, если перевод не найден.
        """
        if not text or self.current_language == "ru":
            return text

        # Пробуем текущий язык
        translation = self.translations.get(self.current_language, {}).get(text)
        if translation:
            return translation

        # Фоллбек на английский, если текущий язык не английский
        if self.current_language != self.fallback_language:
            translation = self.translations.get(self.fallback_language, {}).get(text)
            if translation:
                self.logger.debug(f"Fallback перевод с '{self.fallback_language}' для '{text}': '{translation}'")
                return translation

        self.logger.debug(f"Перевод для '{text}' не найден, возвращаем исходный текст")
        return text

    def translate_ini_section(self, ini_content: str) -> str:
        """
        Переводит названия секций в INI-файле.
        """
        self.logger.info("Начало перевода секций INI-файла")
        sections = [
            "[Обход блокировок для РКН]",
            "[Универсальный обход]",
            "[Обход Discord + YouTube]"
        ]
        for section in sections:
            translated = self.translate(section)
            if translated != section:
                ini_content = ini_content.replace(section, translated)
        self.logger.info("Перевод секций INI-файла завершён")
        return ini_content

    def get_available_languages(self) -> Dict[str, str]:
        """Возвращает копию словаря доступных языков."""
        return self.language_names.copy()