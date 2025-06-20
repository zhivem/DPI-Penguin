import logging
import os
from typing import Optional, Union

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QWidget
from qfluentwidgets import PushButton, Theme, setTheme
import pywinstyles

from utils.utils import tr

# Константы
DARK_THEME_NAME = "dark"
LIGHT_THEME_NAME = "light"
STYLES_FOLDER = "resources/styles"
DARK_STYLESHEET = "dark_theme.qss"
LIGHT_STYLESHEET = "light_theme.qss"
ICON_FOLDER = "resources/icon"

# Логгер
logger = logging.getLogger("dpipenguin")

def apply_theme(
    window: QWidget,
    theme_name: str,
    settings: QSettings,
    base_folder: Union[str, os.PathLike]
) -> None:
    """
    Применяет тему (тёмную или светлую) к приложению и сохраняет выбор в настройках.
    """
    app = QApplication.instance()
    if app is None:
        logger.error(tr("QApplication не инициализирован"))
        return

    if theme_name == DARK_THEME_NAME:
        setTheme(Theme.DARK)
        pywinstyles.apply_style(window, DARK_THEME_NAME)
        stylesheet_name = DARK_STYLESHEET
    else:
        setTheme(Theme.LIGHT)
        pywinstyles.apply_style(window, LIGHT_THEME_NAME)
        stylesheet_name = LIGHT_STYLESHEET

    style_content = get_stylesheet(stylesheet_name, base_folder)
    if style_content:
        app.setStyleSheet(style_content)
        logger.info(tr("Применён стиль: {stylesheet}").format(stylesheet=stylesheet_name))
    else:
        logger.warning(tr("Не удалось применить стиль: {stylesheet}").format(stylesheet=stylesheet_name))

    settings.setValue("theme", theme_name)


def get_stylesheet_path(base_folder: Union[str, os.PathLike], stylesheet_name: str) -> str:
    """
    Возвращает полный путь к файлу стилей.
    """
    return os.path.join(base_folder, STYLES_FOLDER, stylesheet_name)


def get_stylesheet(stylesheet_name: str, base_folder: Union[str, os.PathLike]) -> Optional[str]:
    """
    Загружает содержимое файла стилей.
    """
    path = get_stylesheet_path(base_folder, stylesheet_name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(tr("Файл стилей не найден: {path}").format(path=path))
    except Exception as e:
        logger.error(tr("Ошибка при загрузке стиля {path}: {error}").format(path=path, error=e))
    return None


def update_theme_button_text(
    window: QWidget,
    settings: QSettings
) -> None:
    """
    Обновляет текст и подсказку кнопки переключения темы в зависимости от текущей темы.
    """
    current_theme = settings.value("theme", LIGHT_THEME_NAME)
    theme_button: Optional[PushButton] = getattr(window, "theme_toggle_button", None)

    if theme_button is None:
        logger.warning(tr("Кнопка 'theme_toggle_button' не найдена в окне"))
        return

    if current_theme == LIGHT_THEME_NAME:
        theme_button.setText(tr("Переключиться на тёмную тему"))
        theme_button.setToolTip(tr("Нажмите, чтобы переключиться на тёмную тему"))
    else:
        theme_button.setText(tr("Переключиться на светлую тему"))
        theme_button.setToolTip(tr("Нажмите, чтобы переключиться на светлую тему"))


def toggle_theme(
    window: QWidget,
    settings: QSettings,
    base_folder: Union[str, os.PathLike]
) -> None:
    """
    Переключает текущую тему между тёмной и светлой.
    """
    current_theme = settings.value("theme", LIGHT_THEME_NAME)
    new_theme = DARK_THEME_NAME if current_theme == LIGHT_THEME_NAME else LIGHT_THEME_NAME
    apply_theme(window, new_theme, settings, base_folder)
    update_theme_button_text(window, settings)
    logger.info(tr("Тема переключена с '{old}' на '{new}'").format(old=current_theme, new=new_theme))