import logging
import time
import win32service
import win32serviceutil
import winerror

logger = logging.getLogger("ServiceUtils")

def stop_service(service_name: str) -> None:
    try:
        logger.info(f"Остановка службы {service_name}...")
        service_status = win32serviceutil.QueryServiceStatus(service_name)
        if service_status[1] == win32service.SERVICE_RUNNING:
            win32serviceutil.StopService(service_name)
            logger.info(f"Служба {service_name} отправлена на остановку.")
            for _ in range(15):
                service_status = win32serviceutil.QueryServiceStatus(service_name)
                if service_status[1] == win32service.SERVICE_STOPPED:
                    logger.info(f"Служба {service_name} успешно остановлена.")
                    break
                time.sleep(1)
            else:
                logger.warning(f"Служба {service_name} не остановилась вовремя.")
        else:
            logger.info(f"Служба {service_name} не запущена.")
    except Exception as e:
        if hasattr(e, 'winerror') and e.winerror == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
            logger.warning(f"Служба {service_name} не установлена.")
        else:
            logger.error(f"Ошибка при остановке службы {service_name}: {e}")
            raise e 