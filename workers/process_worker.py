import locale
import logging
import os
import subprocess
from typing import List, Optional

from PyQt6 import QtCore

class WorkerThread(QtCore.QThread):
    output_signal = QtCore.pyqtSignal(str)
    finished_signal = QtCore.pyqtSignal(str)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(
        self,
        command: List[str],
        process_name: str,
        encoding: Optional[str] = None,
        capture_output: bool = True
    ):
        super().__init__()
        self.command = command
        self.process_name = process_name
        self.encoding = encoding or locale.getpreferredencoding()
        self.capture_output = capture_output
        self.process = None
        self._is_terminated = False
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        self.logger.debug(f"Запуск команды: {' '.join(self.command)}")
        try:
            self.process = self._start_process()
            if self.capture_output and self.process.stdout:
                self._capture_output()
            self.process.wait()
            self.logger.info(f"Процесс {self.process_name} завершён с кодом {self.process.returncode}")
        except subprocess.SubprocessError as e:
            self._handle_error(f"Ошибка запуска процесса {self.process_name}: {e}")
        except Exception as e:
            self._handle_error(f"Неожиданная ошибка в WorkerThread {self.process_name}: {e}", critical=True)
        finally:
            self.finished_signal.emit(self.process_name)
            self.process = None

    def _start_process(self) -> subprocess.Popen:
        popen_params = {
            'args': self.command,
            'text': True,
            'encoding': self.encoding,
            'creationflags': subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            'stdout': subprocess.PIPE if self.capture_output else subprocess.DEVNULL,
            'stderr': subprocess.STDOUT if self.capture_output else subprocess.DEVNULL,
            'shell': False
        }

        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            popen_params['startupinfo'] = startupinfo

        return subprocess.Popen(**popen_params)

    def _capture_output(self) -> None:
        for output in self.process.stdout:
            if self._is_terminated:
                self.logger.debug("Завершение захвата вывода из-за принудительного завершения процесса.")
                break
            output = output.strip()
            if output:
                self.output_signal.emit(output)
                self.logger.debug(f"[{self.process_name}] {output}")

    def _handle_error(self, message: str, critical: bool = False) -> None:
        self.logger.error(message)
        if critical:
            self.logger.critical(message, exc_info=True)
        self.error_signal.emit(message)

    def terminate_process(self) -> None:
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self._is_terminated = True
                self.logger.info(f"Процесс {self.process_name} принудительно завершён.")
            except Exception as e:
                self.logger.error(f"Не удалось завершить процесс {self.process_name}: {e}")
