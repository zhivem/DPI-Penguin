from PyQt5 import QtCore
import subprocess
import logging
import locale
import os

class WorkerThread(QtCore.QThread):
    output_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal(str)

    def __init__(self, command, process_name, encoding=None):
        super().__init__()
        self.command = command
        self.process_name = process_name
        self.encoding = encoding or locale.getpreferredencoding()

    def run(self):
        try:
            logging.debug(f"Запуск команды: {self.command}")
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=self.encoding,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            for output in process.stdout:
                if output.strip():
                    self.output_signal.emit(output.strip())

            process.wait()
        except subprocess.SubprocessError as e:
            logging.error(f"Ошибка запуска процесса {self.process_name}: {e}")
            self.output_signal.emit(f"Ошибка: {str(e)}")
        except Exception as e:
            logging.error(f"Неожиданная ошибка: {e}")
            self.output_signal.emit(f"Ошибка: {str(e)}")
        finally:
            self.finished_signal.emit(self.process_name)
