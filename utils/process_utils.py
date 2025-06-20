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

logger = logging.getLogger("dpipenguin")

class ProcessUtils:
    """Утилиты для работы с процессами и службами."""

    @classmethod
    def terminate_process(cls, process_name: str) -> bool:
        """Завершает процесс по имени. Возвращает True при успехе."""
        process_name_lower = process_name.lower()
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name_lower:
                    pid = proc.info['pid']
                    logger.info(tr("Завершение процесса {name} (PID: {pid})").format(name=process_name, pid=pid))
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                        logger.info(tr("Процесс {name} успешно завершён").format(name=process_name))
                    except psutil.TimeoutExpired:
                        logger.warning(tr("Тайм-аут при завершении {name}, принудительное завершение").format(name=process_name))
                        proc.kill()
                        proc.wait(timeout=5)
                        logger.info(tr("Процесс {name} принудительно завершён").format(name=process_name))
                    return True
            logger.warning(tr("Процесс {name} не найден").format(name=process_name))
            return False
        except Exception as e:
            logger.exception(tr("Ошибка завершения процесса {name}: {error}").format(name=process_name, error=e))
            return False

    @classmethod
    def stop_service(cls, service_name: str) -> None:
        """Останавливает службу."""
        logger.info(tr("Остановка службы: {name}").format(name=service_name))
        try:
            stop_service(service_name)
            logger.info(tr("Служба {name} успешно остановлена").format(name=service_name))
        except Exception as e:
            logger.exception(tr("Ошибка остановки службы {name}: {error}").format(name=service_name, error=e))
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

    def run(self) -> None:
        """Запуск процесса и обработка вывода."""
        self._running = True
        logger.info(tr("Запуск процесса {name}: {cmd}").format(
            name=self.process_name, cmd=' '.join(self.command)
        ))
        try:
            with self._start_process() as process:
                self._process = process
                if self.capture_output and process.stdout:
                    self._handle_output(process.stdout)
                else:
                    process.wait()
                self._log_completion(process.returncode)
        except Exception as e:
            error_msg = tr("Ошибка в процессе {name}: {error}").format(name=self.process_name, error=str(e))
            logger.exception(error_msg)
            self.error_signal.emit(error_msg)

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
                logger.info(tr("Обработка вывода прервана для {name}").format(name=self.process_name))
                break
            line = line.strip()
            if line:
                self.output_signal.emit(line)

    def _log_completion(self, returncode: int) -> None:
        """Логирование завершения процесса."""
        if returncode == 0:
            logger.info(tr("Процесс {name} завершён успешно").format(name=self.process_name))
        else:
            logger.warning(tr("Процесс {name} завершён с кодом ошибки {code}").format(
                name=self.process_name, code=returncode
            ))
        self.finished_signal.emit(self.process_name)

    def terminate_process(self) -> None:
        """Принудительное завершение процесса."""
        if self._process and self._process.poll() is None:
            self._running = False
            logger.info(tr("Попытка завершить процесс {name}").format(name=self.process_name))
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
                logger.info(tr("Процесс {name} успешно завершён").format(name=self.process_name))
            except subprocess.TimeoutExpired:
                self._process.kill()
                logger.warning(tr("Процесс {name} принудительно убит после тайм-аута").format(name=self.process_name))

    def close_winws(self) -> None:
        """Завершение процесса winws.exe."""
        logger.info(tr("Запрос на завершение winws.exe"))
        self._close_process("winws.exe")

    def _close_process(self, process_name: str) -> None:
        """Общий метод завершения процесса."""
        if ProcessUtils.terminate_process(process_name):
            self.output_signal.emit(tr("Обход остановлен"))
            logger.info(tr("Процесс {name} остановлен, обход завершён").format(name=process_name))


class InitializerThread(QtCore.QThread):
    """Поток инициализации: завершает процессы и службы."""
    initialization_complete = QtCore.pyqtSignal()
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, processes_to_terminate: Set[str], service_to_stop: str):
        super().__init__()
        self.processes_to_terminate = set(map(str.lower, processes_to_terminate))
        self.service_to_stop = service_to_stop

    def run(self) -> None:
        """Запуск инициализации."""
        logger.info(tr("Запуск инициализации процессов и служб"))
        try:
            self._terminate_processes()
            ProcessUtils.stop_service(self.service_to_stop)
            logger.info(tr("Инициализация успешно завершена"))
            self.initialization_complete.emit()
        except Exception as e:
            error_msg = tr("Ошибка инициализации: {error}").format(error=str(e))
            logger.exception(error_msg)
            self.error_signal.emit(error_msg)

    def _terminate_processes(self) -> None:
        """Завершение указанных процессов."""
        logger.info(tr("Завершение процессов: {procs}").format(procs=', '.join(self.processes_to_terminate)))
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and proc.info['pid'] != current_pid:
                proc_name = proc.info['name'].lower()
                if proc_name in self.processes_to_terminate:
                    try:
                        logger.info(tr("Завершение процесса {name} (PID: {pid})").format(
                            name=proc_name, pid=proc.info['pid']
                        ))
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                            logger.info(tr("Процесс {name} успешно завершён").format(name=proc_name))
                        except psutil.TimeoutExpired:
                            proc.kill()
                            logger.warning(tr("Процесс {name} принудительно убит после тайм-аута").format(name=proc_name))
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.warning(tr("Ошибка завершения процесса {name}: {error}").format(
                            name=proc_name, error=e
                        ))