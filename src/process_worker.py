from PyQt5 import QtCore
import subprocess
import logging

class WorkerThread(QtCore.QThread):
    output_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal(str)

    def __init__(self, command, process_name, encoding="utf-8"):
        super().__init__()
        self.command = command
        self.process_name = process_name
        self.encoding = encoding

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=self.encoding,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            for output in process.stdout:
                if output.strip():
                    self.output_signal.emit(output.strip())

            process.wait()
        except subprocess.SubprocessError as e:
            logging.error(f"Ошибка запуска процесса {self.process_name}: {e}")
            self.output_signal.emit(f"Ошибка: {str(e)}")
        finally:
            self.finished_signal.emit(self.process_name)
