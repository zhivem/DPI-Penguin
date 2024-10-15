import locale
import logging
import os
import subprocess
from typing import List, Optional

from PyQt5 import QtCore


class WorkerThread(QtCore.QThread):
    """
    Класс WorkerThread для выполнения команд в отдельном потоке и передачи вывода через сигналы.
    """
    output_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal(str)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, command: List[str], process_name: str, encoding: Optional[str] = None, capture_output: bool = True):
        """
        Инициализация рабочего потока.

        Args:
            command (List[str]): Команда для выполнения.
            process_name (str): Имя процесса.
            encoding (Optional[str], optional): Кодировка. По умолчанию используется системная.
            capture_output (bool, optional): Флаг захвата вывода. По умолчанию True.
        """
        super().__init__()
        self.command = command
        self.process_name = process_name
        self.encoding = encoding or locale.getpreferredencoding()
        self.capture_output = capture_output
        self.process = None

    def run(self) -> None:
        """
        Метод, выполняемый при запуске потока. Запускает процесс и обрабатывает его вывод.
        """
        try:
            logging.debug(f"Запуск команды: {' '.join(self.command)}")

            popen_params = {
                'args': self.command,
                'text': True,
                'encoding': self.encoding,
                'creationflags': subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            }

            if self.capture_output:
                popen_params.update({
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.STDOUT
                })
            else:
                popen_params.update({
                    'stdout': subprocess.DEVNULL,
                    'stderr': subprocess.DEVNULL
                })

            self.process = subprocess.Popen(**popen_params)

            if self.capture_output and self.process.stdout:
                for output in self.process.stdout:
                    if output.strip():
                        self.output_signal.emit(output.strip())

            self.process.wait()
        except subprocess.SubprocessError as e:
            error_message = f"Ошибка запуска процесса {self.process_name}: {e}"
            logging.error(error_message)
            self.error_signal.emit(error_message)
        except Exception as e:
            error_message = f"Неожиданная ошибка в WorkerThread {self.process_name}: {e}"
            logging.critical(error_message, exc_info=True)
            self.error_signal.emit(error_message)
        finally:
            self.finished_signal.emit(self.process_name)

    def terminate_process(self) -> None:
        """
        Принудительно завершает процесс, если он еще выполняется.
        """
        if self.process and self.process.poll() is None:
            self.process.terminate()
            logging.info(f"Процесс {self.process_name} принудительно завершен.")
