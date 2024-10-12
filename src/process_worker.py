import locale
import logging
import os
import subprocess

from PyQt5 import QtCore


class WorkerThread(QtCore.QThread):
    output_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal(str)

    def __init__(self, command, process_name, encoding=None, capture_output=True):
        super().__init__()
        self.command = command
        self.process_name = process_name
        self.encoding = encoding or locale.getpreferredencoding()
        self.capture_output = capture_output
        self.process = None 

    def run(self):
        try:
            logging.debug(f"Запуск команды: {self.command}")

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

            if self.capture_output:
                for output in self.process.stdout:
                    if output.strip():
                        self.output_signal.emit(output.strip())

            self.process.wait()
        except subprocess.SubprocessError as e:
            logging.error(f"Ошибка запуска процесса {self.process_name}: {e}")
            if self.capture_output:
                self.output_signal.emit(f"Ошибка запуска процесса {self.process_name}: {str(e)}")
        except Exception as e:
            logging.critical(f"Неожиданная ошибка в WorkerThread {self.process_name}: {e}", exc_info=True)
            if self.capture_output:
                self.output_signal.emit(f"Неожиданная ошибка: {str(e)}")
        finally:
            self.finished_signal.emit(self.process_name)

    def terminate_process(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            logging.info(f"Процесс {self.process_name} принудительно завершен.")
