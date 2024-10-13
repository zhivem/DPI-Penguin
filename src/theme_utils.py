import logging
import os

from qfluentwidgets import Theme, setTheme
import pywinstyles


def apply_theme(app_instance, theme_name, settings, base_folder):
    """
    Применяет выбранную тему к приложению.

    Параметры:
        app_instance: Экземпляр приложения или виджета.
        theme_name (str): Имя темы ('light' или 'dark').
        settings (QSettings): Объект настроек для сохранения выбранной темы.
        base_folder (str): Базовая директория для поиска файлов стилей.
    """
    if theme_name == "dark":
        setTheme(Theme.DARK)
        pywinstyles.apply_style(app_instance, "dark")
        apply_stylesheet(app_instance, "dark_theme.qss", base_folder)
    else:
        setTheme(Theme.LIGHT)
        pywinstyles.apply_style(app_instance, "dark") ## Можете оставить light если хотите чтоб шапка была белой
        apply_stylesheet(app_instance, "light_theme.qss", base_folder)

    settings.setValue("theme", theme_name)


def apply_stylesheet(app_instance, stylesheet_name, base_folder):
    """
    Применяет файл стилей к приложению.

    Параметры:
        app_instance: Экземпляр приложения или виджета.
        stylesheet_name (str): Имя файла стилей.
        base_folder (str): Базовая директория для поиска файлов стилей.
    """
    style_path = os.path.join(base_folder, "styles", stylesheet_name)
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            style = f.read()
            app_instance.setStyleSheet(style)
    except Exception as e:
        logging.error(f"Не удалось загрузить файл стилей: {e}")

def update_theme_button_text(app_instance, settings):
    """
    Обновляет текст и подсказку на кнопке переключения темы.

    Параметры:
        app_instance: Экземпляр приложения или виджета.
        settings (QSettings): Объект настроек для получения текущей темы.
    """
    current_theme = settings.value("theme", "light")
    button = getattr(app_instance, 'theme_toggle_button', None)
    if button:
        if current_theme == "light":
            button.setText("Переключиться на тёмную тему")
            button.setToolTip("Нажмите, чтобы переключиться на тёмную тему")
        else:
            button.setText("Переключиться на светлую тему")
            button.setToolTip("Нажмите, чтобы переключиться на светлую тему")
    else:
        logging.error("У приложения нет атрибута 'theme_toggle_button'")


def toggle_theme(app_instance, settings, base_folder):
    """
    Переключает тему приложения между светлой и тёмной.

    Параметры:
        app_instance: Экземпляр приложения или виджета.
        settings (QSettings): Объект настроек для получения и сохранения текущей темы.
        base_folder (str): Базовая директория для поиска файлов стилей.
    """
    current_theme = settings.value("theme", "light")
    if current_theme == "light":
        apply_theme(app_instance, "dark", settings, base_folder)
    else:
        apply_theme(app_instance, "light", settings, base_folder)
    update_theme_button_text(app_instance, settings)
