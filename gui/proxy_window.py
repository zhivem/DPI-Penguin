import re
import subprocess
import winreg
import requests
import logging

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QGroupBox
)

from qfluentwidgets import PushButton, TextEdit as QFluentTextEdit, ComboBox, FluentIcon

from utils import theme_utils
from utils.utils import settings, BASE_FOLDER

# Настройка логирования
logger = logging.getLogger("dpipenguin")

DNS_SERVERS = {
    "DNS по умолчанию": ("", ""),
    "CloudFlare": ("1.1.1.1", "1.0.0.1"),
    "Google": ("8.8.8.8", "8.8.4.4"),
    "Quad9": ("9.9.9.9", "149.112.112.112"),
    "Adguard": ("94.140.14.14", "94.140.15.15"),
    "Yandex": ("77.88.8.8", "77.88.8.1")
}

class RegistryManager:
    """Управление настройками прокси через реестр Windows"""
    @staticmethod
    def set_proxy(enabled: bool, server: str = "") -> None:
        """Устанавливает или сбрасывает настройки прокси"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                              0, winreg.KEY_WRITE) as key:
                winreg.SetValue(key, "ProxyEnable", 0, winreg.REG_DWORD, int(enabled))
                if enabled and server:
                    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, server)
        except Exception as e:
            logger.error(f"Ошибка записи в реестр: {e}")
            raise

class ProxyTester(QThread):
    """Тестирование работоспособности прокси-сервера"""
    test_complete = pyqtSignal(bool)
    
    def __init__(self, proxy_data: dict):
        super().__init__()
        self.proxy_data = proxy_data

    def run(self):
        """Основной метод выполнения теста"""
        try:
            response = requests.get("https://httpbin.org/ip", 
                                  proxies=self.proxy_data, 
                                  timeout=10)
            self.test_complete.emit(response.ok)
        except Exception as e:
            logger.error(f"Ошибка тестирования прокси: {e}")
            self.test_complete.emit(False)

class DnsManager(QThread):
    """Управление настройками DNS"""
    operation_complete = pyqtSignal(str)

    def __init__(self, interface: str, primary: str = "", secondary: str = ""):
        super().__init__()
        self.interface = interface
        self.primary = primary
        self.secondary = secondary

    def run(self):
        """Выполняет настройку DNS"""
        try:
            if not self.primary:  # Сброс к DHCP
                self._execute_command(["netsh", "interface", "ip", "set", "dns", 
                                     f"name={self.interface}", "source=dhcp"])
                self.operation_complete.emit("DNS сброшены к настройкам по умолчанию")
                return

            # Установка первичного DNS
            self._execute_command(["netsh", "interface", "ip", "set", "dns", 
                                 f"name={self.interface}", "source=static", 
                                 f"address={self.primary}"])
            
            # Установка вторичного DNS при наличии
            if self.secondary:
                self._execute_command(["netsh", "interface", "ip", "add", "dns", 
                                     f"name={self.interface}", f"address={self.secondary}", 
                                     "index=2"])
            
            self.operation_complete.emit("DNS успешно обновлены")

        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка настройки DNS: {e}")
            self.operation_complete.emit(f"Ошибка: {e.stderr}")

    def _execute_command(self, command: list):
        """Выполняет системную команду"""
        return subprocess.run(command, 
                            check=True, 
                            capture_output=True, 
                            text=True, 
                            encoding='utf-8',  
                            errors='ignore',
                            creationflags=subprocess.CREATE_NO_WINDOW)

class ProxySettingsDialog(QDialog):
    """Главный диалог настроек прокси и DNS"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки сети")
        self.setFixedSize(550, 500)
        # Применяем текущую тему
        saved_theme = settings.value("theme", "light")
        theme_utils.apply_theme(self, saved_theme, settings, BASE_FOLDER)
        self._init_ui()
        self._load_network_interfaces()
        logger.info("Инициализация диалога настроек сети")

    def _init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()
        
        # Секция прокси
        main_layout.addWidget(self._create_proxy_section())
        
        # Секция DNS
        main_layout.addWidget(self._create_dns_section())
        
        # Область логов
        self.log_area = QFluentTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)

        self.setLayout(main_layout)

    def _create_proxy_section(self):
        """Создает секцию настроек прокси"""
        section = QGroupBox("Настройки прокси")
        layout = QVBoxLayout()

        # Поля ввода
        input_layout = QHBoxLayout()
        self.proxy_ip = QLineEdit(placeholderText="IP адрес")
        self.proxy_port = QLineEdit(placeholderText="Порт")
        self.proxy_type = ComboBox()
        self.proxy_type.addItems(["HTTP", "HTTPS", "SOCKS4", "SOCKS5"])
        
        input_layout.addWidget(self.proxy_ip)
        input_layout.addWidget(self.proxy_port)
        input_layout.addWidget(self.proxy_type)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.test_btn = PushButton("Проверить", self, FluentIcon.SYNC)
        self.apply_btn = PushButton("Применить", self, FluentIcon.VIEW)
        self.clear_btn = PushButton("Сбросить", self, FluentIcon.DELETE)
        
        self.test_btn.clicked.connect(self._test_proxy)
        self.apply_btn.clicked.connect(self._apply_proxy)
        self.clear_btn.clicked.connect(self._clear_proxy)

        btn_layout.addWidget(self.test_btn)
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(input_layout)
        layout.addLayout(btn_layout)
        section.setLayout(layout)
        return section

    def _create_dns_section(self):
        """Создает секцию настроек DNS"""
        section = QGroupBox("Настройки DNS")
        layout = QVBoxLayout()

        # Выбор интерфейса
        self.interface_combo = ComboBox()
        layout.addWidget(QLabel("Сетевой интерфейс:"))
        layout.addWidget(self.interface_combo)

        # Выбор DNS
        self.dns_combo = ComboBox()
        self.dns_combo.addItems(DNS_SERVERS.keys())
        layout.addWidget(QLabel("Предустановки DNS:"))
        layout.addWidget(self.dns_combo)

        # Кнопка применения
        self.apply_dns_btn = PushButton("Применить DNS", self, FluentIcon.ADD)
        self.apply_dns_btn.clicked.connect(self._apply_dns)
        layout.addWidget(self.apply_dns_btn)

        section.setLayout(layout)
        return section

    def _load_network_interfaces(self):
        """Загружает список сетевых интерфейсов"""
        try:
            result = subprocess.run(["netsh", "interface", "show", "interface"],
                                  capture_output=True,
                                  text=True,
                                  encoding='utf-8',  # Используем UTF-8
                                  errors='ignore',   # Игнорируем ошибки декодирования
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            
            interfaces = [line.split()[-1] for line in result.stdout.splitlines() 
                        if "Connected" in line or "Подключен" in line]
            
            self.interface_combo.addItems(interfaces or ["Ethernet"])
            
        except Exception as e:
            logger.error(f"Ошибка получения интерфейсов: {e}")
            self.interface_combo.addItem("Ethernet")

    def _validate_proxy_input(self) -> bool:
        """Проверяет корректность введенных данных"""
        ip = self.proxy_ip.text().strip()
        port = self.proxy_port.text().strip()
        
        if not all([ip, port]):
            self._show_warning("Заполните все поля прокси")
            return False
        
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
            self._show_warning("Некорректный IP-адрес")
            return False
        
        try:
            if not 0 < int(port) < 65536:
                raise ValueError
        except ValueError:
            self._show_warning("Некорректный номер порта")
            return False
        
        return True

    def _test_proxy(self):
        """Тестирует работоспособность прокси"""
        if not self._validate_proxy_input():
            return

        proxy_data = {
            "http": f"{self.proxy_type.currentText().lower()}://"
                    f"{self.proxy_ip.text()}:{self.proxy_port.text()}",
            "https": f"{self.proxy_type.currentText().lower()}://"
                    f"{self.proxy_ip.text()}:{self.proxy_port.text()}"
        }

        self.test_btn.setEnabled(False)
        self.tester = ProxyTester(proxy_data)
        self.tester.test_complete.connect(self._handle_test_result)
        self.tester.start()

    def _handle_test_result(self, success: bool):
        """Обрабатывает результат тестирования прокси"""
        self.test_btn.setEnabled(True)
        msg = "✅ Прокси работает" if success else "❌ Прокси недоступен"
        self.log_area.append(msg)

    def _apply_proxy(self):
        """Применяет настройки прокси"""
        if not self._validate_proxy_input():
            return

        server = f"{self.proxy_ip.text()}:{self.proxy_port.text()}"
        try:
            RegistryManager.set_proxy(True, server)
            self.log_area.append(f"Прокси {server} успешно применен")
        except Exception as e:
            self._show_error(f"Ошибка применения прокси: {e}")

    def _clear_proxy(self):
        """Сбрасывает настройки прокси"""
        try:
            RegistryManager.set_proxy(False)
            self.log_area.append("Настройки прокси сброшены")
        except Exception as e:
            self._show_error(f"Ошибка сброса прокси: {e}")

    def _apply_dns(self):
        """Применяет настройки DNS"""
        interface = self.interface_combo.currentText()
        primary, secondary = DNS_SERVERS[self.dns_combo.currentText()]
        
        self.dns_manager = DnsManager(interface, primary, secondary)
        self.dns_manager.operation_complete.connect(self.log_area.append)
        self.dns_manager.start()

    def _show_warning(self, text: str):
        """Отображает предупреждение"""
        QMessageBox.warning(self, "Внимание", text)

    def _show_error(self, text: str):
        """Отображает сообщение об ошибке"""
        QMessageBox.critical(self, "Ошибка", text)
