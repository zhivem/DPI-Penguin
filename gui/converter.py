import re
import logging
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QCheckBox, QGroupBox, QFileDialog
from PyQt6.QtGui import QGuiApplication
from qfluentwidgets import PushButton, TextEdit, LineEdit, ComboBox
from utils.utils import tr

class ConfigConverterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.initUI()

    def initUI(self):
        self.setWindowTitle(tr('Конвертер конфигурации в правильный формат'))
        self.setFixedSize(800, 600)
        layout = QVBoxLayout()

        self.config_name_input = LineEdit(self)
        self.config_name_input.setPlaceholderText(tr("Введите название конфигурации..."))
        layout.addWidget(self.config_name_input)

        self.method_groupbox = QGroupBox(tr("Выбор метода"), self)
        method_layout = QVBoxLayout()

        self.method_combobox = ComboBox(self)
        self.method_combobox.addItems([
            tr("Общий метод"),
            tr("Метод для Discord + YouTube"),
            tr("Метод для РКН")
        ])
        method_layout.addWidget(self.method_combobox)

        self.method_groupbox.setLayout(method_layout)
        layout.addWidget(self.method_groupbox)

        self.options_groupbox = QGroupBox(tr("Дополнительные опции"), self)
        options_layout = QVBoxLayout()

        self.script_options_checkbox = QCheckBox(tr("Добавить [SCRIPT_OPTIONS]"), self)
        self.script_options_checkbox.setChecked(True)
        options_layout.addWidget(self.script_options_checkbox)

        self.options_groupbox.setLayout(options_layout)
        layout.addWidget(self.options_groupbox)

        self.input_text = TextEdit(self)
        self.input_text.setPlaceholderText(tr("Введите команду здесь..."))
        layout.addWidget(self.input_text)

        self.convert_button = PushButton(tr('Конвертировать'), self)
        self.convert_button.clicked.connect(self.convert_command)
        layout.addWidget(self.convert_button)

        self.output_text = TextEdit(self)
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText(tr("Результат конвертации появится здесь..."))
        layout.addWidget(self.output_text)

        self.copy_button = PushButton(tr('Копировать в буфер'), self)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_button)

        self.save_as_button = PushButton(tr('Сохранить как'), self)
        self.save_as_button.clicked.connect(self.save_as_file)
        layout.addWidget(self.save_as_button)

        self.setLayout(layout)

    def convert_command(self):
        config_name = self.config_name_input.text().strip()

        if not config_name:
            self.logger.warning("Попытка конвертации без имени конфигурации")
            QMessageBox.warning(self, tr("Ошибка"), tr("Название конфигурации обязательно!"))
            return

        method = self.method_combobox.currentText()
        add_script_options = self.script_options_checkbox.isChecked()
        command = self.input_text.toPlainText()

        self.logger.info(f"Конвертация команды для конфигурации '{config_name}' с методом '{method}'")
        converted_config = self.convert_command_to_config(command, config_name, method, add_script_options)
        self.output_text.setPlainText(converted_config)
        # Убрано self.logger.debug("Конвертация успешно завершена") - избыточная деталь, успех виден по отсутствию ошибок

    def copy_to_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        text = self.output_text.toPlainText()
        if text:
            clipboard.setText(text)
            self.logger.info("Результат конвертации скопирован в буфер обмена")
            QMessageBox.information(self, tr("Скопировано"), tr("Результат скопирован в буфер обмена!"))
        else:
            self.logger.warning("Попытка копирования пустого результата")
            QMessageBox.warning(self, tr("Ошибка"), tr("Нет данных для копирования!"))

    def save_as_file(self):
        config_text = self.output_text.toPlainText()

        if not config_text:
            self.logger.warning("Попытка сохранить пустой файл")
            QMessageBox.warning(self, tr("Ошибка"), tr("Нет данных для сохранения!"))
            return

        file_name, _ = QFileDialog.getSaveFileName(self, tr("Сохранить файл"), "", tr("INI Files (*.ini)"))
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as file:
                    file.write(config_text)
                self.logger.info(f"Файл успешно сохранен: {file_name}")
                QMessageBox.information(self, tr("Сохранено"), tr("Файл успешно сохранен!"))
            except Exception as e:
                self.logger.error(f"Ошибка при сохранении файла {file_name}: {str(e)}")
                QMessageBox.warning(self, tr("Ошибка"), tr("Не удалось сохранить файл!"))

    def convert_command_to_config(self, command: str, config_name: str, method: str, add_script_options: bool) -> str:
        # Убрано логирование внутри функции, так как процесс преобразования - внутренняя деталь
        command = re.sub(r'start.*?winws\.exe', '', command, flags=re.IGNORECASE).strip()
        command = command.replace('"', '').replace('^', '').strip()

        args = re.split(r'\s+--', command)
        args = [arg.strip() for arg in args if arg.strip()]

        if method == tr("Универсальный метод"):
            hostlist_var = "{BLACKLIST_FILES_2}"
        elif method == tr("Обход Discord + YouTube"):
            hostlist_var = "{BLACKLIST_FILES_1}"
        elif method == tr("Обход блокировок для РКН"):
            hostlist_var = "{BLACKLIST_FILES_0}"
        else:
            hostlist_var = "{BLACKLIST_FILES_2}"

        variables = {
            "%~dp0": "{ZAPRET_FOLDER}\\",
            "%~dp0ipset-discord.txt": "{BLACKLIST_FOLDER}\\ipset-discord.txt",
            "%~dp0tls_clienthello_www_google_com.bin": "{ZAPRET_FOLDER}\\tls_clienthello_www_google_com.bin",
            "%~dp0quic_initial_www_google_com.bin": "{ZAPRET_FOLDER}\\quic_initial_www_google_com.bin",
        }

        formatted_args = []
        for arg in args:
            if not arg.startswith("--"):
                arg = "--" + arg

            if arg.startswith("--hostlist"):
                arg = f"--hostlist={hostlist_var};"
            else:
                if arg.startswith("--ipset"):
                    arg = arg.replace("%~dp0", "{BLACKLIST_FOLDER}\\")
                else:
                    for key, value in variables.items():
                        arg = arg.replace(key, value)

            formatted_args.append("    " + arg + ";")

        config = ""
        if add_script_options:
            config += "[SCRIPT_OPTIONS]\n\n"
        config += f"[{config_name}]\n"
        config += "executable = {ZAPRET_FOLDER}\\winws.exe\n"
        config += "args =\n" + "\n".join(formatted_args)
        return config