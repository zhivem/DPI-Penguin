import logging
import os
from typing import Any, Optional

from PyQt5.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme
import pywinstyles

# Константы
DARK_THEME_NAME = "dark"
LIGHT_THEME_NAME = "light"
DARK_STYLESHEET = "dark_theme.qss"
LIGHT_STYLESHEET = "light_theme.qss"
STYLES_FOLDER = "resources/styles"  
ICON_FOLDER = "resources/icon" 

def apply_theme(
    app_instance: QApplication,
    theme_name: str,
    settings: Any, 
    base_folder: str
) -> None:
    """
    Применяет выбранную тему к приложению.

    Args:
        app_instance (QApplication): Экземпляр приложения PyQt5.
        theme_name (str): Название темы ("dark" или "light").
        settings (Any): Экземпляр QSettings для сохранения настроек.
        base_folder (str): Базовая папка приложения для поиска файлов стилей.
    """
    if theme_name == DARK_THEME_NAME:
        setTheme(Theme.DARK)
        pywinstyles.apply_style(app_instance, DARK_THEME_NAME)
        stylesheet = DARK_STYLESHEET
    else:
        setTheme(Theme.LIGHT)
        pywinstyles.apply_style(app_instance, DARK_THEME_NAME)  # Если хотите белую шапку, то LIGHT_THEME_NAME
        stylesheet = LIGHT_STYLESHEET

    apply_stylesheet(app_instance, stylesheet, base_folder)
    settings.setValue("theme", theme_name)
    logging.info(f"Тема '{theme_name}' применена.")

def apply_stylesheet(
    app_instance: QApplication,
    stylesheet_name: str,
    base_folder: str
) -> None:
    """
    Применяет файл стилей к приложению.

    Args:
        app_instance (QApplication): Экземпляр приложения PyQt5.
        stylesheet_name (str): Имя файла стилей (например, "dark_theme.qss").
        base_folder (str): Базовая папка приложения для поиска файлов стилей.
    """
    style_path = os.path.join(base_folder, STYLES_FOLDER, stylesheet_name)
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            style = f.read()
            app_instance.setStyleSheet(style)
        logging.info(f"Применен стиль: {stylesheet_name}")
    except FileNotFoundError:
        logging.error(f"Файл стилей не найден: {style_path}")
    except Exception as e:
        logging.error(f"Не удалось загрузить файл стилей {style_path}: {e}")

def update_theme_button_text(
    app_instance: Any,  
    settings: Any
) -> None:
    """
    Обновляет текст и подсказку кнопки переключения темы в зависимости от текущей темы.

    Args:
        app_instance (Any): Экземпляр главного окна приложения с кнопкой `theme_toggle_button`.
        settings (Any): Экземпляр QSettings для получения текущей темы.
    """
    current_theme = settings.value("theme", LIGHT_THEME_NAME)
    theme_button = getattr(app_instance, "theme_toggle_button", None)

    if not theme_button:
        logging.warning("Кнопка 'theme_toggle_button' не найдена в app_instance.")
        return

    if current_theme == LIGHT_THEME_NAME:
        theme_button.setText("Переключиться на тёмную тему")
        theme_button.setToolTip("Нажмите, чтобы переключиться на тёмную тему")
    else:
        theme_button.setText("Переключиться на светлую тему")
        theme_button.setToolTip("Нажмите, чтобы переключиться на светлую тему")

    logging.debug(f"Текст кнопки переключения темы обновлён на '{theme_button.text()}'.")

def toggle_theme(
    app_instance: Any,
    settings: Any,
    base_folder: str
) -> None:
    """
    Переключает тему приложения между тёмной и светлой.

    Args:
        app_instance (Any): Экземпляр приложения PyQt5.
        settings (Any): Экземпляр QSettings для сохранения текущей темы.
        base_folder (str): Базовая папка приложения для поиска файлов стилей.
    """
    current_theme = settings.value("theme", LIGHT_THEME_NAME)
    new_theme = DARK_THEME_NAME if current_theme == LIGHT_THEME_NAME else LIGHT_THEME_NAME
    apply_theme(app_instance, new_theme, settings, base_folder)
    update_theme_button_text(app_instance, settings)
    logging.info(f"Тема переключена с '{current_theme}' на '{new_theme}'.")

def get_stylesheet_path(base_folder: str, stylesheet_name: str) -> str:
    """
    Возвращает полный путь к файлу стилей.

    Args:
        base_folder (str): Базовая папка приложения.
        stylesheet_name (str): Имя файла стилей.

    Returns:
        str: Полный путь к файлу стилей.
    """
    return os.path.join(base_folder, STYLES_FOLDER, stylesheet_name)

def get_stylesheet(
    app_instance: QApplication,
    stylesheet_name: str,
    base_folder: str
) -> Optional[str]:
    """
    Получает содержимое файла стилей.

    Args:
        app_instance (QApplication): Экземпляр приложения PyQt5.
        stylesheet_name (str): Имя файла стилей.
        base_folder (str): Базовая папка приложения.

    Returns:
        Optional[str]: Содержимое стилей, если файл найден, иначе None.
    """
    style_path = get_stylesheet_path(base_folder, stylesheet_name)
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Файл стилей не найден: {style_path}")
    except Exception as e:
        logging.error(f"Не удалось загрузить файл стилей {style_path}: {e}")
    return None
