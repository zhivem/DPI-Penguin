import locale
import logging
import os
import subprocess

from PyQt5.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
    """
    Класс для выполнения внешних команд в отдельном потоке.

    Сигналы:
        output_signal (str): Сигнал для передачи вывода процесса.
        finished_signal (str): Сигнал об окончании процесса.
    """
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, command, process_name, encoding=None, capture_output=True):
        super().__init__()
        self.command = command
        self.process_name = process_name
        self.encoding = encoding or locale.getpreferredencoding()
        self.capture_output = capture_output
        self.process = None

    def run(self):
        """
        Запускает процесс и обрабатывает его вывод.
        """
        try:
            logging.debug(f"Запуск команды: {self.command}")

            popen_params = {
                'args': self.command,
                'universal_newlines': True,
                'encoding': self.encoding,
                'errors': 'replace',
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

            if self.capture_output:
                for output in self.process.stdout:
                    if output.strip():
                        self.output_signal.emit(output.strip())

            self.process.wait()
        except FileNotFoundError:
            error_msg = f"Команда не найдена: {self.command}"
            logging.error(error_msg)
            if self.capture_output:
                self.output_signal.emit(error_msg)
        except subprocess.SubprocessError as e:
            error_msg = f"Ошибка запуска процесса {self.process_name}: {e}"
            logging.error(error_msg)
            if self.capture_output:
                self.output_signal.emit(error_msg)
        except Exception as e:
            error_msg = f"Неожиданная ошибка в WorkerThread {self.process_name}: {e}"
            logging.critical(error_msg, exc_info=True)
            if self.capture_output:
                self.output_signal.emit(error_msg)
        finally:
            if self.capture_output and self.process and self.process.stdout:
                self.process.stdout.close()
            self.finished_signal.emit(self.process_name)

    def terminate_process(self):
        """
        Принудительно завершает процесс.
        """
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logging.info(f"Процесс {self.process_name} принудительно завершен.")
