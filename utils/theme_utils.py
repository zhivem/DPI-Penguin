import logging
import os
from typing import Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QWidget
from qfluentwidgets import PushButton, Theme, setTheme
# import pywinstyles  # Импортируем модуль для шапки 

from utils.utils import tr

# Константы для тем и путей к стилям
DARK_THEME_NAME = "dark"
LIGHT_THEME_NAME = "light"
DARK_STYLESHEET = "dark_theme.qss"
LIGHT_STYLESHEET = "light_theme.qss"
STYLES_FOLDER = "resources/styles"
ICON_FOLDER = "resources/icon"


def apply_theme(
    app_instance: QApplication,
    theme_name: str,
    settings: QSettings,
    base_folder: str
) -> None:
    """
    Применяет выбранную тему к приложению.

    :param app_instance: Экземпляр QApplication.
    :param theme_name: Название темы ('dark' или 'light').
    :param settings: Экземпляр QSettings для сохранения выбранной темы.
    :param base_folder: Базовая папка приложения.
    """
    if theme_name == DARK_THEME_NAME:
        setTheme(Theme.DARK)
        # pywinstyles.apply_style(app_instance, DARK_THEME_NAME)  # Настройка темы шапки 
        stylesheet = DARK_STYLESHEET
    else:
        setTheme(Theme.LIGHT)
        # pywinstyles.apply_style(app_instance, LIGHT_THEME_NAME)  # Настройка темы шапки 
        stylesheet = LIGHT_STYLESHEET

    apply_stylesheet(app_instance, stylesheet, base_folder)
    settings.setValue("theme", theme_name)
    logging.info(tr("Тема '{theme_name}' применена").format(theme_name=theme_name))


def apply_stylesheet(
    app_instance: QApplication,
    stylesheet_name: str,
    base_folder: str
) -> None:
    """
    Применяет заданный файл стилей к приложению.

    :param app_instance: Экземпляр QApplication.
    :param stylesheet_name: Имя файла стилей (.qss).
    :param base_folder: Базовая папка приложения.
    """
    style_path = os.path.join(base_folder, STYLES_FOLDER, stylesheet_name)
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            style = f.read()
            app_instance.setStyleSheet(style)
        logging.info(tr("Применен стиль: {stylesheet_name}").format(stylesheet_name=stylesheet_name))
    except FileNotFoundError:
        logging.error(tr("Файл стилей не найден: {style_path}").format(style_path=style_path))
    except Exception as e:
        logging.error(tr("Не удалось загрузить файл стилей {style_path}: {e}").format(style_path=style_path, e=e))


def update_theme_button_text(
    app_instance: QWidget,
    settings: QSettings
) -> None:
    """
    Обновляет текст и подсказку на кнопке переключения темы в зависимости от текущей темы.

    :param app_instance: Экземпляр QWidget, содержащий кнопку переключения темы.
    :param settings: Экземпляр QSettings для получения текущей темы.
    """
    current_theme = settings.value("theme", LIGHT_THEME_NAME)
    theme_button: Optional[PushButton] = getattr(app_instance, "theme_toggle_button", None)

    if not theme_button:
        logging.warning(tr("Кнопка 'theme_toggle_button' не найдена в app_instance"))
        return

    if current_theme == LIGHT_THEME_NAME:
        theme_button.setText(tr("Переключиться на тёмную тему"))
        theme_button.setToolTip(tr("Нажмите, чтобы переключиться на тёмную тему"))
    else:
        theme_button.setText(tr("Переключиться на светлую тему"))
        theme_button.setToolTip(tr("Нажмите, чтобы переключиться на светлую тему"))

    logging.debug(tr("Текст кнопки переключения темы обновлён на '{text}'").format(text=theme_button.text()))


def toggle_theme(
    app_instance: QApplication,
    settings: QSettings,
    base_folder: str
) -> None:
    """
    Переключает тему приложения между светлой и тёмной.

    :param app_instance: Экземпляр QApplication.
    :param settings: Экземпляр QSettings для сохранения выбранной темы.
    :param base_folder: Базовая папка приложения.
    """
    current_theme = settings.value("theme", LIGHT_THEME_NAME)
    new_theme = DARK_THEME_NAME if current_theme == LIGHT_THEME_NAME else LIGHT_THEME_NAME
    apply_theme(app_instance, new_theme, settings, base_folder)
    update_theme_button_text(app_instance, settings)
    logging.info(tr("Тема переключена с '{current_theme}' на '{new_theme}'.").format(current_theme=current_theme, new_theme=new_theme))


def get_stylesheet_path(base_folder: str, stylesheet_name: str) -> str:
    """
    Возвращает полный путь к файлу стилей.

    :param base_folder: Базовая папка приложения.
    :param stylesheet_name: Имя файла стилей.
    :return: Полный путь к файлу стилей.
    """
    return os.path.join(base_folder, STYLES_FOLDER, stylesheet_name)


def get_stylesheet(
    stylesheet_name: str,
    base_folder: str
) -> Optional[str]:
    """
    Возвращает содержимое файла стилей.

    :param stylesheet_name: Имя файла стилей (.qss).
    :param base_folder: Базовая папка приложения.
    :return: Содержимое стилей или None, если файл не найден или произошла ошибка.
    """
    style_path = get_stylesheet_path(base_folder, stylesheet_name)
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logging.error(tr("Файл стилей не найден: {style_path}").format(style_path=style_path))
    except Exception as e:
        logging.error(tr("Не удалось загрузить файл стилей {style_path}: {e}").format(style_path=style_path, e=e))
    return None
