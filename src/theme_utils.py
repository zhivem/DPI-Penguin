import logging
import os
from typing import Any

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor
from qfluentwidgets import Theme, setTheme
import pywinstyles


def apply_theme(app_instance: QApplication, theme_name: str, settings: Any, base_folder: str) -> None:
    """
    Применяет выбранную тему к приложению.

    Args:
        app_instance (QApplication): Экземпляр приложения PyQt5.
        theme_name (str): Название темы ("dark" или "light").
        settings (QSettings): Экземпляр QSettings для сохранения настроек.
        base_folder (str): Базовая папка приложения для поиска файлов стилей.
    """
    if theme_name == "dark":
        setTheme(Theme.DARK)
        pywinstyles.apply_style(app_instance, "dark")
        apply_stylesheet(app_instance, "dark_theme.qss", base_folder)
    else:
        setTheme(Theme.LIGHT)
        pywinstyles.apply_style(app_instance, "dark")  # Если хотите белую шапку то поменяйте на "light"
        apply_stylesheet(app_instance, "light_theme.qss", base_folder)

    settings.setValue("theme", theme_name)


def apply_stylesheet(app_instance: QApplication, stylesheet_name: str, base_folder: str) -> None:
    """
    Применяет файл стилей к приложению.

    Args:
        app_instance (QApplication): Экземпляр приложения PyQt5.
        stylesheet_name (str): Имя файла стилей (например, "dark_theme.qss").
        base_folder (str): Базовая папка приложения для поиска файлов стилей.
    """
    style_path = os.path.join(base_folder, "styles", stylesheet_name)
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            style = f.read()
            app_instance.setStyleSheet(style)
        logging.info(f"Применен стиль: {stylesheet_name}")
    except FileNotFoundError:
        logging.error(f"Файл стилей не найден: {style_path}")
    except Exception as e:
        logging.error(f"Не удалось загрузить файл стилей {style_path}: {e}")


def update_theme_button_text(app_instance: Any, settings: Any) -> None:
    """
    Обновляет текст и подсказку кнопки переключения темы в зависимости от текущей темы.

    Args:
        app_instance (Any): Экземпляр главного окна приложения с кнопкой `theme_toggle_button`.
        settings (Any): Экземпляр QSettings для получения текущей темы.
    """
    current_theme = settings.value("theme", "light")
    if current_theme == "light":
        app_instance.theme_toggle_button.setText("Переключиться на тёмную тему")
        app_instance.theme_toggle_button.setToolTip("Нажмите, чтобы переключиться на тёмную тему")
    else:
        app_instance.theme_toggle_button.setText("Переключиться на светлую тему")
        app_instance.theme_toggle_button.setToolTip("Нажмите, чтобы переключиться на светлую тему")


def toggle_theme(app_instance: Any, settings: Any, base_folder: str) -> None:
    """
    Переключает тему приложения между тёмной и светлой.

    Args:
        app_instance (Any): Экземпляр приложения PyQt5.
        settings (Any): Экземпляр QSettings для сохранения текущей темы.
        base_folder (str): Базовая папка приложения для поиска файлов стилей.
    """
    current_theme = settings.value("theme", "light")
    new_theme = "dark" if current_theme == "light" else "light"
    apply_theme(app_instance, new_theme, settings, base_folder)
    update_theme_button_text(app_instance, settings)
