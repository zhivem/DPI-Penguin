import logging
from typing import Optional
import time
from contextlib import suppress

import win32service
import win32serviceutil
import winerror
from pywintypes import error as WinError 

logger = logging.getLogger(__name__)

def stop_service(service_name: str, timeout: int = 15) -> bool:
    """
    Останавливает указанную службу Windows.

    Args:
        service_name: Название службы для остановки
        timeout: Максимальное время ожидания остановки в секундах (по умолчанию 15)

    Returns:
        bool: True если служба остановлена или не существует, False если не удалось остановить

    Raises:
        WinError: Если произошла непредвиденная ошибка при работе со службой
    """
    logger.info(f"Попытка остановки службы '{service_name}' (timeout={timeout} сек)")
    
    try:
        # Проверка статуса службы
        service_status = win32serviceutil.QueryServiceStatus(service_name)
        current_state = service_status[1]
        state_map = {
            win32service.SERVICE_STOPPED: "STOPPED",
            win32service.SERVICE_RUNNING: "RUNNING",
            win32service.SERVICE_START_PENDING: "START_PENDING",
            win32service.SERVICE_STOP_PENDING: "STOP_PENDING",
        }
        state_name = state_map.get(current_state, f"UNKNOWN ({current_state})")

        if current_state != win32service.SERVICE_RUNNING:
            logger.info(f"Служба '{service_name}' уже не запущена, текущее состояние: {state_name}")
            return True

        # Остановка службы
        win32serviceutil.StopService(service_name)

        # Ожидание остановки
        for attempt in range(timeout):
            service_status = win32serviceutil.QueryServiceStatus(service_name)
            current_state = service_status[1]
            state_name = state_map.get(current_state, f"UNKNOWN ({current_state})")
            if current_state == win32service.SERVICE_STOPPED:
                logger.info(f"Служба '{service_name}' успешно остановлена за {attempt + 1} секунд")
                return True
            time.sleep(1)

        logger.warning(f"Служба '{service_name}' не остановилась за {timeout} секунд, последнее состояние: {state_name}")
        return False

    except WinError as e:
        if e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
            logger.info(f"Служба '{service_name}' не существует в системе")
            return True
        logger.exception(f"Ошибка при остановке службы '{service_name}': {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"Неизвестная ошибка при работе со службой '{service_name}': {str(e)}")
        raise

def is_service_running(service_name: str) -> Optional[bool]:
    """
    Проверяет, запущена ли служба.

    Args:
        service_name: Название службы для проверки

    Returns:
        bool: True если служба запущена, False если остановлена, None если службы нет
    """
    with suppress(WinError):
        status = win32serviceutil.QueryServiceStatus(service_name)
        is_running = status[1] == win32service.SERVICE_RUNNING
        state_map = {
            win32service.SERVICE_STOPPED: "STOPPED",
            win32service.SERVICE_RUNNING: "RUNNING",
            win32service.SERVICE_START_PENDING: "START_PENDING",
            win32service.SERVICE_STOP_PENDING: "STOP_PENDING",
        }
        state_name = state_map.get(status[1], f"UNKNOWN ({status[1]})")
        return is_running
    logger.info(f"Служба '{service_name}' не найдена в системе")
    return None

if __name__ == "__main__":
    try:
        result = stop_service("WinDivert")
        print(f"Service stop result: {result}")
        running = is_service_running("WinDivert")
        print(f"Service running: {running}")
    except Exception as e:
        print(f"Failed with error: {e}")