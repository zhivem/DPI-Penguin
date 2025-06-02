import logging
import time
from contextlib import suppress
from typing import Optional

import win32service
import win32serviceutil
import winerror
from pywintypes import error as WinError

logger = logging.getLogger(__name__)

_SERVICE_STATES = {
    win32service.SERVICE_STOPPED: "STOPPED",
    win32service.SERVICE_RUNNING: "RUNNING",
    win32service.SERVICE_START_PENDING: "START_PENDING",
    win32service.SERVICE_STOP_PENDING: "STOP_PENDING",
}

def stop_service(service_name: str, timeout: int = 15) -> bool:
    """
    Останавливает указанную службу Windows.

    Args:
        service_name: Название службы для остановки
        timeout: Максимальное время ожидания остановки в секундах (по умолчанию 15)

    Returns:
        True, если служба успешно остановлена или не существует,
        False, если не удалось остановить в отведённое время.

    Raises:
        WinError: при непредвиденных ошибках работы со службой.
    """
    logger.info(f"Попытка остановки службы '{service_name}' с таймаутом {timeout} сек")

    try:
        status = win32serviceutil.QueryServiceStatus(service_name)
        state = status[1]
        state_name = _SERVICE_STATES.get(state, f"UNKNOWN ({state})")

        if state != win32service.SERVICE_RUNNING:
            logger.info(f"Служба '{service_name}' не запущена (текущее состояние: {state_name})")
            return True

        win32serviceutil.StopService(service_name)
        logger.debug(f"Команда остановки службы '{service_name}' отправлена")

        for second in range(timeout):
            status = win32serviceutil.QueryServiceStatus(service_name)
            state = status[1]
            state_name = _SERVICE_STATES.get(state, f"UNKNOWN ({state})")

            if state == win32service.SERVICE_STOPPED:
                logger.info(f"Служба '{service_name}' успешно остановлена за {second + 1} сек")
                return True

            time.sleep(1)

        logger.warning(f"Служба '{service_name}' не остановилась за {timeout} сек (текущее состояние: {state_name})")
        return False

    except WinError as e:
        if e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
            logger.info(f"Служба '{service_name}' не существует в системе")
            return True
        logger.exception(f"Ошибка при остановке службы '{service_name}': {e}")
        raise
    except Exception as e:
        logger.exception(f"Неизвестная ошибка при работе со службой '{service_name}': {e}")
        raise


def is_service_running(service_name: str) -> Optional[bool]:
    """
    Проверяет, запущена ли служба.

    Args:
        service_name: Название службы для проверки

    Returns:
        True, если служба запущена,
        False, если остановлена,
        None, если служба не найдена.
    """
    with suppress(WinError):
        status = win32serviceutil.QueryServiceStatus(service_name)
        state = status[1]
        state_name = _SERVICE_STATES.get(state, f"UNKNOWN ({state})")
        logger.debug(f"Статус службы '{service_name}': {state_name}")
        return state == win32service.SERVICE_RUNNING

    logger.info(f"Служба '{service_name}' не найдена в системе")
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    service = "WinDivert"

    try:
        stopped = stop_service(service)
        print(f"Служба '{service}' остановлена: {stopped}")

        running = is_service_running(service)
        print(f"Служба '{service}' запущена: {running}")

    except Exception as e:
        print(f"Ошибка: {e}")