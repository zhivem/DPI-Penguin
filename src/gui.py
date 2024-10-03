import os  # Модуль для работы с файловой системой.
from PyQt5 import QtWidgets, QtCore  # Импортируем виджеты и основные классы из PyQt5.
from PyQt5.QtGui import QIcon, QTextCursor, QDesktopServices  # Импортируем классы для иконок, работы с текстом и открытия URL.
from qfluentwidgets import PushButton, ComboBox, TextEdit, Theme, setTheme  # Импортируем пользовательские виджеты из qfluentwidgets.
from process_worker import WorkerThread  # Импортируем поток для выполнения команд (модуль process_worker).
from update_checker import UpdateCheckerThread  # Импортируем поток для проверки обновлений (модуль update_checker).
from blacklist_updater import update_blacklist  # Импортируем функцию обновления черного списка (модуль blacklist_updater).
from utils import BASE_FOLDER, BLACKLIST_FILES, GOODBYE_DPI_EXE, WIN_DIVERT_COMMAND, GOODBYE_DPI_PROCESS_NAME  # Импортируем утилиты и константы для работы.
import psutil  # Импортируем модуль для управления процессами на уровне системы.

class GoodbyeDPIApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()  # Вызов конструктора родительского класса QWidget.
        self.init_ui()  # Инициализация интерфейса.
        self.check_for_updates()  # Автоматическая проверка обновлений при запуске.

    def init_ui(self):
        """
        Инициализация графического интерфейса.
        """
        self.setWindowTitle("GoodByeDPI GUI by Zhivem")  # Устанавливаем заголовок окна.
        self.setFixedSize(420, 450)  # Задаем фиксированный размер окна.
        self.setWindowIcon(QIcon(os.path.join(BASE_FOLDER, "icon", 'fackrkn.ico')))  # Устанавливаем иконку окна.
        setTheme(Theme.LIGHT)  # Устанавливаем светлую тему интерфейса.

        layout = QtWidgets.QVBoxLayout(self)  # Создаем основной вертикальный макет.

        # Словарь с параметрами для различных скриптов.
        self.script_options = {
            "YouTube (Актуальный метод)": [
                "-9", "--blacklist", BLACKLIST_FILES[0], "--blacklist", BLACKLIST_FILES[1]
            ],
            "Ростелеком (Тестовая версия)": [
                "-5", "-e1", "--blacklist", BLACKLIST_FILES[0], "--blacklist", BLACKLIST_FILES[1]
            ]
        }

        self.selected_script = ComboBox()  # Выпадающий список для выбора скрипта.
        self.selected_script.addItems(self.script_options.keys())  # Добавляем в ComboBox названия скриптов.
        layout.addWidget(self.selected_script)  # Добавляем ComboBox в макет.

        # Кнопка для запуска выбранного скрипта.
        self.run_button = PushButton("Запустить")
        self.run_button.clicked.connect(self.run_exe)  # Привязываем метод run_exe к клику по кнопке.
        layout.addWidget(self.run_button)  # Добавляем кнопку в макет.

        # Кнопка для остановки процесса WinDivert и закрытия GoodbyeDPI.
        self.stop_close_button = PushButton("Остановить WinDivert и закрыть GoodbyeDPI")
        self.stop_close_button.setEnabled(False)  # Деактивируем кнопку, пока процесс не запущен.
        self.stop_close_button.clicked.connect(self.stop_and_close)  # Привязываем метод stop_and_close к клику по кнопке.
        layout.addWidget(self.stop_close_button)  # Добавляем кнопку в макет.

        # Кнопка для обновления черного списка.
        self.update_blacklist_button = PushButton("Обновить черный список")
        self.update_blacklist_button.clicked.connect(self.update_blacklist)  # Привязываем метод update_blacklist к клику по кнопке.
        layout.addWidget(self.update_blacklist_button)  # Добавляем кнопку в макет.

        # Кнопка для ручной проверки обновлений.
        self.update_button = PushButton("Проверить обновления")
        self.update_button.clicked.connect(self.check_for_updates)  # Привязываем метод check_for_updates к клику по кнопке.
        layout.addWidget(self.update_button)  # Добавляем кнопку в макет.

        # Поле для вывода текстовой информации (консоль).
        self.console_output = TextEdit()
        self.console_output.setReadOnly(True)  # Поле только для чтения.
        layout.addWidget(self.console_output)  # Добавляем консоль в макет.

    def run_exe(self):
        """
        Метод для запуска выбранного скрипта GoodbyeDPI.
        """
        command = [GOODBYE_DPI_EXE] + self.script_options[self.selected_script.currentText()]  # Формируем команду для запуска.
        self.start_process(command, "GoodbyeDPI", disable_run=True, clear_console_text="Процесс GoodbyeDPI запущен...")  # Запускаем процесс.

    def start_process(self, command, process_name, disable_run=False, clear_console_text=None):
        """
        Метод для запуска процесса в отдельном потоке.
        :param command: Команда для выполнения.
        :param process_name: Название процесса для завершения и логирования.
        :param disable_run: Если True, отключить кнопку запуска.
        :param clear_console_text: Текст для очистки консоли перед запуском.
        """
        if clear_console_text:
            self.clear_console(clear_console_text)  # Очищаем консоль и добавляем новый текст.

        # Создаем поток для выполнения команды.
        self.worker_thread = WorkerThread(command, process_name, encoding="cp866")
        self.worker_thread.output_signal.connect(self.update_output)  # Подключаем сигнал для обновления консоли.
        self.worker_thread.finished_signal.connect(self.on_finished)  # Подключаем сигнал для обработки завершения.
        self.worker_thread.start()  # Запускаем поток.

        if disable_run:
            self.run_button.setEnabled(False)  # Отключаем кнопку запуска.
            self.stop_close_button.setEnabled(True)  # Активируем кнопку остановки.

    def update_output(self, text):
        """
        Метод для обновления вывода в консоли.
        """
        self.console_output.append(text)  # Добавляем новый текст в консоль.
        max_lines = 100  # Максимальное количество строк в консоли.
        document = self.console_output.document()  # Получаем документ консоли.
        while document.blockCount() > max_lines:  # Если строк больше максимума, удаляем старые.
            cursor = self.console_output.textCursor()  # Получаем текстовый курсор.
            cursor.movePosition(QTextCursor.Start)  # Перемещаем курсор в начало.
            cursor.select(QTextCursor.BlockUnderCursor)  # Выбираем текущий блок текста.
            cursor.removeSelectedText()  # Удаляем выбранный текст.
            cursor.deleteChar()  # Удаляем символ.

    def on_finished(self, process_name):
        """
        Метод, вызываемый при завершении работы процесса.
        """
        if process_name == "GoodbyeDPI":
            self.run_button.setEnabled(True)  # Активируем кнопку запуска.
            self.stop_close_button.setEnabled(False)  # Отключаем кнопку остановки.
            self.console_output.append(f"Процесс {process_name} завершен.")  # Сообщаем о завершении процесса.
    
    def stop_and_close(self):
        """
        Метод для остановки процесса WinDivert и закрытия GoodbyeDPI.
        """
        self.start_process(WIN_DIVERT_COMMAND, "WinDivert")  # Запускаем команду для остановки WinDivert.
        self.close_goodbyedpi()  # Останавливаем GoodbyeDPI.

    def close_goodbyedpi(self):
        """
        Метод для завершения процесса GoodbyeDPI через psutil.
        """
        try:
            for proc in psutil.process_iter(['pid', 'name']):  # Итерируем по всем процессам.
                if proc.info['name'] == GOODBYE_DPI_PROCESS_NAME:  # Если находим процесс с нужным именем.
                    psutil.Process(proc.info['pid']).terminate()  # Завершаем процесс по PID.
                    return
            self.console_output.append("Процесс GoodbyeDPI не найден.")  # Если процесс не найден.
        except psutil.Error as e:
            self.console_output.append(f"Ошибка завершения процесса: {str(e)}")  # Логируем ошибку при завершении процесса.

    def update_blacklist(self):
        """
        Метод для обновления черного списка.
        """
        self.clear_console("Обновление черного списка...")  # Очищаем консоль и выводим сообщение.
        success = update_blacklist()  # Запускаем обновление черного списка.
        if success:
            self.console_output.append("Обновление черного списка успешно завершено.")  # Сообщение об успешном обновлении.
        else:
            self.console_output.append("Не удалось обновить черный список. Проверьте соединение с интернетом.")  # Сообщение об ошибке.

    def clear_console(self, initial_text=""):
        """
        Метод для очистки консоли.
        """
        self.console_output.clear()  # Очищаем консоль.
        if initial_text:
            self.console_output.append(initial_text)  # Добавляем новый текст, если он есть.

    def check_for_updates(self):
        """
        Метод для проверки обновлений.
        """
        self.update_thread = UpdateCheckerThread()  # Создаем поток для проверки обновлений.
        self.update_thread.update_available.connect(self.notify_update)  # Подключаем сигнал для уведомления об обновлении.
        self.update_thread.no_update.connect(self.no_update)  # Подключаем сигнал для уведомления об отсутствии обновлений.
        self.update_thread.update_error.connect(self.update_error)  # Подключаем сигнал для уведомления об ошибке.
        self.update_thread.start()  # Запускаем поток.

    def no_update(self):
        """
        Метод для обработки случая, когда обновлений нет.
        """
        self.console_output.append("Обновлений нет. Вы используете последнюю версию.")  # Выводим сообщение в консоль.

    def update_error(self, error_message):
        """
        Метод для обработки ошибок при проверке обновлений.
        """
        self.console_output.append(error_message)  # Логируем сообщение об ошибке в консоль.

    def notify_update(self, latest_version):
        """
        Метод для уведомления о доступности обновлений.
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            "Доступно обновление",  # Заголовок диалогового окна.
            f"Доступна новая версия {latest_version}. Хотите перейти на страницу загрузки?",  # Сообщение о доступной версии.
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No  # Опции "Да" или "Нет".
        )
        if reply == QtWidgets.QMessageBox.Yes:  # Если пользователь выбрал "Да".
            QDesktopServices.openUrl(QtCore.QUrl('https://github.com/zhivem/GUI/releases'))  # Открываем URL для загрузки новой версии.
