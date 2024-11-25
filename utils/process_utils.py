import locale
import logging
import os
import subprocess
from typing import List, Optional

import psutil
from PyQt6 import QtCore
from utils.service_utils import stop_service

from utils.utils import tr

if os.name == 'nt':
    import win32api


class ProcessUtils:
    logger = logging.getLogger('ProcessUtils')

    @staticmethod
    def terminate_process(process_name: str) -> None:
        """
        Завершает процесс по имени.
        """
        try:
            ProcessUtils.logger.info(tr(f"Завершение процесса {process_name}..."))
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    ProcessUtils.logger.info(tr(f"Попытка завершить процесс {process_name} с PID {proc.info['pid']}"))
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                        ProcessUtils.logger.info(tr(f"Процесс {process_name} успешно завершён."))
                    except psutil.TimeoutExpired:
                        ProcessUtils.logger.warning(tr(f"Процесс {process_name} не завершился вовремя, пытаемся принудительно завершить."))
                        proc.kill()
                        proc.wait(timeout=5)
                        ProcessUtils.logger.info(tr(f"Процесс {process_name} принудительно завершён."))
        except Exception as e:
            ProcessUtils.logger.error(tr(f"Ошибка при завершении процесса {process_name}: {e}"))
            raise e

    @staticmethod
    def stop_service(service_name: str) -> None:
        """
        Останавливает службу по имени, используя внешнюю функцию stop_service.
        """
        try:
            ProcessUtils.logger.info(tr(f"Остановка службы {service_name}..."))
            stop_service(service_name)
            ProcessUtils.logger.info(tr(f"Служба {service_name} успешно остановлена."))
        except Exception as e:
            ProcessUtils.logger.error(tr(f"Ошибка при остановке службы {service_name}: {e}"))
            raise e


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
        self.logger.debug(tr("Запуск команды: {command}").format(command=' '.join(self.command)))
        try:
            self.process = self._start_process()
            if self.capture_output and self.process.stdout:
                self._capture_output()
            else:
                self.process.wait()
            self.logger.info(tr("Процесс {process_name} завершён с кодом {returncode}").format(
                process_name=self.process_name,
                returncode=self.process.returncode
            ))
        except subprocess.SubprocessError as e:
            self._handle_error(tr("Ошибка запуска процесса {process_name}: {error}").format(
                process_name=self.process_name,
                error=e
            ))
        except Exception as e:
            self._handle_error(tr("Неожиданная ошибка в WorkerThread {process_name}: {error}").format(
                process_name=self.process_name,
                error=e
            ), critical=True)
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
                self.logger.debug(tr("Завершение захвата вывода из-за принудительного завершения процесса"))
                break
            output = output.strip()
            if output:
                self.output_signal.emit(output)
                self.logger.debug(tr("[{process_name}] {output}").format(
                    process_name=self.process_name,
                    output=output
                ))
        self.process.stdout.close()

    def _handle_error(self, message: str, critical: bool = False) -> None:
        self.logger.error(message)
        if critical:
            self.logger.critical(message, exc_info=True)
        self.error_signal.emit(message)

    def terminate_process(self) -> None:
        """Общий метод для завершения процесса."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait()
                self._is_terminated = True
                self.logger.info(tr("Процесс {process_name} принудительно завершён").format(
                    process_name=self.process_name
                ))
            except Exception as e:
                self._handle_error(tr("Не удалось завершить процесс {process_name}: {error}").format(
                    process_name=self.process_name,
                    error=e
                ))

    def close_winws(self):
        """Завершаем процесс winws.exe с помощью общей логики."""
        self._close_process("winws.exe", "winws.exe")

    def _close_process(self, process_name: str, display_name: str):
        """Общий метод для завершения процессов через psutil."""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    psutil.Process(proc.info['pid']).terminate()
                    self.output_signal.emit(tr("Обход остановлен"))
                    self.logger.debug(f"{tr('Процесс')} {display_name} (PID: {proc.info['pid']}) {tr('завершён')}")
        except psutil.NoSuchProcess:
            self.logger.warning(f"{tr('Процесс')} {display_name} {tr('не найден.')}")
        except psutil.AccessDenied:
            error_msg = f"{tr('Недостаточно прав для завершения процесса')} {display_name}"
            self._handle_error(error_msg)
        except Exception as e:
            self._handle_error(f"{tr('Ошибка завершения процесса')} {display_name}: {str(e)}")


class InitializerThread(QtCore.QThread):
    initialization_complete = QtCore.pyqtSignal()
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, processes_to_terminate: List[str], service_to_stop: str):
        super().__init__()
        self.processes_to_terminate = processes_to_terminate
        self.service_to_stop = service_to_stop
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        try:
            self.logger.info(tr("Инициализация: завершение процессов и остановка службы"))
            self.terminate_processes(self.processes_to_terminate)
            self.stop_service(self.service_to_stop)
            self.logger.info(tr("Инициализация завершена"))
            self.initialization_complete.emit()
        except Exception as e:
            error_msg = tr("Ошибка инициализации: {e}").format(e=e)
            self.logger.error(error_msg, exc_info=True)
            self.error_signal.emit(error_msg)

    def terminate_processes(self, process_names: List[str]):
        """Общий метод для завершения нескольких процессов."""
        current_process_id = win32api.GetCurrentProcessId()
        for proc in psutil.process_iter(['pid', 'name']):
            pid = proc.info['pid']
            exe_name = proc.info['name']
            if exe_name is None:
                continue
            exe_base_name = os.path.basename(exe_name).lower()
            if exe_base_name in [name.lower() for name in process_names] and pid != current_process_id:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    self.logger.info(tr("Процесс {exe_base_name} (PID: {pid}) успешно завершён").format(
                        exe_base_name=exe_base_name, pid=pid
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
                    self.logger.warning(tr("Не удалось завершить PID {pid}: {e}").format(pid=pid, e=e))

    def stop_service(self, service_name: str):
        """
        Останавливает службу, используя ProcessUtils.
        """
        ProcessUtils.stop_service(service_name)