import locale
import logging
import os
import subprocess
from typing import List, Optional, Set

import psutil
from PyQt6 import QtCore
from utils.service_utils import stop_service
from utils.utils import tr

if os.name == 'nt':
    from win32con import CREATE_NO_WINDOW


class ProcessUtils:
    """Утилиты для работы с процессами и службами."""
    logger = logging.getLogger(__name__)

    @classmethod
    def terminate_process(cls, process_name: str) -> bool:
        """Завершает процесс по имени. Возвращает True при успехе."""
        cls.logger.debug(tr("Попытка завершить процесс: {name}").format(name=process_name))
        try:
            process_name_lower = process_name.lower()
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name_lower:
                    pid = proc.info['pid']
                    cls.logger.info(tr("Завершение процесса {name} (PID: {pid})").format(name=process_name, pid=pid))
                    proc.terminate()
                    proc.wait(timeout=10)
                    cls.logger.info(tr("Процесс успешно завершён"))
                    return True
            cls.logger.warning(tr("Процесс {name} не найден").format(name=process_name))
            return False
        except psutil.TimeoutExpired:
            cls.logger.warning(tr("Тайм-аут при завершении {name}, принудительное завершение").format(name=process_name))
            proc.kill()
            proc.wait(timeout=5)
            return True
        except Exception as e:
            cls.logger.error(tr("Ошибка завершения процесса {name}: {error}").format(name=process_name, error=e))
            raise

    @classmethod
    def stop_service(cls, service_name: str) -> None:
        """Останавливает службу."""
        cls.logger.info(tr("Остановка службы: {name}").format(name=service_name))
        try:
            stop_service(service_name)
            cls.logger.info(tr("Служба успешно остановлена"))
        except Exception as e:
            cls.logger.error(tr("Ошибка остановки службы {name}: {error}").format(name=service_name, error=e))
            raise


class WorkerThread(QtCore.QThread):
    """Поток для выполнения внешних процессов."""
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
        self._process: Optional[subprocess.Popen] = None
        self._running = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run(self) -> None:
        """Запуск процесса и обработка вывода."""
        self._running = True
        self.logger.debug(tr("Выполнение команды: {cmd}").format(cmd=' '.join(self.command)))
        try:
            with self._start_process() as process:
                self._process = process
                if self.capture_output and process.stdout:
                    self._handle_output(process.stdout)
                else:
                    process.wait()
                self._log_completion(process.returncode)
        except Exception as e:
            self.error_signal.emit(
                tr("Ошибка в процессе {name}: {error}").format(name=self.process_name, error=str(e))
            )
            self.logger.exception(tr("Исключение в WorkerThread"))

    def _start_process(self) -> subprocess.Popen:
        """Создание и настройка процесса."""
        popen_kwargs = {
            'args': self.command,
            'text': True,
            'encoding': self.encoding,
            'stdout': subprocess.PIPE if self.capture_output else subprocess.DEVNULL,
            'stderr': subprocess.STDOUT if self.capture_output else subprocess.DEVNULL,
            'shell': False,
        }
        if os.name == 'nt':
            popen_kwargs['creationflags'] = CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            popen_kwargs['startupinfo'] = startupinfo
        
        return subprocess.Popen(**popen_kwargs)

    def _handle_output(self, stdout) -> None:
        """Обработка вывода процесса."""
        for line in iter(stdout.readline, ''):
            if not self._running:
                break
            line = line.strip()
            if line:
                self.output_signal.emit(line)
                self.logger.debug(tr("[{name}] {output}").format(name=self.process_name, output=line))

    def _log_completion(self, returncode: int) -> None:
        """Логирование завершения процесса."""
        if returncode == 0:
            self.logger.info(tr("Процесс {name} завершён успешно").format(name=self.process_name))
        else:
            self.logger.warning(tr("Процесс {name} завершён с кодом {code}").format(
                name=self.process_name, code=returncode
            ))
        self.finished_signal.emit(self.process_name)

    def terminate_process(self) -> None:
        """Принудительное завершение процесса."""
        if self._process and self._process.poll() is None:
            self._running = False
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
                self.logger.info(tr("Процесс {name} завершён").format(name=self.process_name))
            except subprocess.TimeoutExpired:
                self._process.kill()
                self.logger.warning(tr("Процесс {name} убит после тайм-аута").format(name=self.process_name))

    def close_winws(self) -> None:
        """Завершение процесса winws.exe."""
        self._close_process("winws.exe")

    def _close_process(self, process_name: str) -> None:
        """Общий метод завершения процесса."""
        ProcessUtils.terminate_process(process_name)
        self.output_signal.emit(tr("Обход остановлен"))


class InitializerThread(QtCore.QThread):
    """Поток инициализации: завершает процессы и службы."""
    initialization_complete = QtCore.pyqtSignal()
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, processes_to_terminate: Set[str], service_to_stop: str):
        super().__init__()
        self.processes_to_terminate = set(map(str.lower, processes_to_terminate))
        self.service_to_stop = service_to_stop
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def run(self) -> None:
        """Запуск инициализации."""
        try:
            self.logger.info(tr("Начало инициализации"))
            self._terminate_processes()
            ProcessUtils.stop_service(self.service_to_stop)
            self.logger.info(tr("Инициализация завершена"))
            self.initialization_complete.emit()
        except Exception as e:
            self.error_signal.emit(tr("Ошибка инициализации: {error}").format(error=str(e)))
            self.logger.exception(tr("Ошибка в InitializerThread"))

    def _terminate_processes(self) -> None:
        """Завершение указанных процессов."""
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and proc.info['pid'] != current_pid:
                proc_name = proc.info['name'].lower()
                if proc_name in self.processes_to_terminate:
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                        self.logger.info(tr("Процесс {name} (PID: {pid}) завершён").format(
                            name=proc_name, pid=proc.info['pid']
                        ))
                    except psutil.TimeoutExpired:
                        proc.kill()
                        self.logger.warning(tr("Процесс {name} убит").format(name=proc_name))
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        self.logger.warning(tr("Ошибка завершения {name}: {error}").format(
                            name=proc_name, error=e
                        ))