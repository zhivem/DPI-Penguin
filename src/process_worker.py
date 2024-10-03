from PyQt5 import QtCore  # Импортируем модуль QtCore из PyQt5 для использования классов, связанных с многопоточностью и сигналами.
import subprocess  # Импортируем модуль subprocess для выполнения команд в командной строке.

class WorkerThread(QtCore.QThread):
    # Определяем два пользовательских сигнала:
    # output_signal - для передачи данных (вывода из процесса),
    # finished_signal - для уведомления о завершении выполнения команды.
    output_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal(str)

    def __init__(self, command, process_name, encoding="utf-8"):
        """
        Инициализация рабочего потока.
        :param command: Команда, которую необходимо выполнить.
        :param process_name: Название процесса (для отправки при завершении).
        :param encoding: Кодировка для вывода данных.
        """
        super().__init__()  # Вызов конструктора родительского класса QThread.
        self.command = command  # Сохраняем команду для выполнения.
        self.process_name = process_name  # Сохраняем имя процесса для сигнала завершения.
        self.encoding = encoding  # Задаем кодировку для вывода текста.

    def run(self):
        """
        Метод, выполняемый в отдельном потоке.
        Здесь происходит выполнение команды и передача данных через сигнал.
        """
        try:
            # Запускаем процесс с помощью subprocess.Popen. Команда выполняется без открытия окна терминала.
            process = subprocess.Popen(
                self.command,  # Команда для выполнения.
                stdout=subprocess.PIPE,  # Перенаправляем стандартный вывод процесса.
                stderr=subprocess.STDOUT,  # Ошибки также перенаправляем в стандартный вывод.
                text=True,  # Включаем текстовый режим (чтение строк).
                encoding=self.encoding,  # Кодировка вывода.
                creationflags=subprocess.CREATE_NO_WINDOW  # Отключаем открытие окна терминала в Windows.
            )

            # Чтение построчно данных из стандартного вывода процесса.
            for output in process.stdout:
                self.output_signal.emit(output.strip())  # Отправляем каждую строку через сигнал output_signal.

            process.wait()  # Ожидаем завершения процесса.
        except subprocess.SubprocessError as e:
            # В случае ошибки отправляем сообщение об ошибке через сигнал output_signal.
            self.output_signal.emit(f"Ошибка: {str(e)}")
        finally:
            # Независимо от исхода, отправляем сигнал завершения с названием процесса.
            self.finished_signal.emit(self.process_name)
