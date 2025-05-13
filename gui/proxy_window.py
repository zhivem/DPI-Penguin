import re
import subprocess
import winreg
import requests
import logging

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QMessageBox, QCheckBox, QGroupBox
from qfluentwidgets import PushButton, TextEdit, ComboBox as QFComboBox

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DNS_SERVERS = {
    "DNS по умолчанию": ("", ""),
    "CloudFlare": ("1.1.1.1", "1.0.0.1"),
    "Google": ("8.8.8.8", "8.8.4.4"),
    "Quad9": ("9.9.9.9", "149.112.112.112"),
    "Adguard": ("94.140.14.14", "94.140.15.15"),
    "Comodo": ("8.26.56.26", "8.20.247.20"),
    "Яндекс": ("77.88.8.8", "77.88.8.1")
}

class RegistryManager:
    """Класс для работы с реестром Windows."""
    @staticmethod
    def set_value(registry_path, value_name, value_type, value_data):
        """Устанавливает значение в реестре."""
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, registry_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, value_name, 0, value_type, value_data)
            winreg.CloseKey(key)
            winreg.CloseKey(registry)
        except Exception as e:
            logger.exception(f"Ошибка при установке значения в реестр: {e}")
            raise

class ProxyTester(QThread):
    """Класс для тестирования прокси."""
    test_result = pyqtSignal(int)

    def __init__(self, proxy_ip, proxy_port, proxy_type):
        super().__init__()
        self.proxy_ip = proxy_ip
        self.proxy_port = proxy_port
        self.proxy_type = proxy_type

    def run(self):
        """Запуск тестирования прокси."""
        logger.info(f"Начало тестирования прокси: {self.proxy_type}://{self.proxy_ip}:{self.proxy_port}")
        try:
            proxies = self.construct_proxies()
            response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=5)
            if 200 <= response.status_code < 300:
                logger.info("Прокси успешно протестирован")
                self.test_result.emit(1)
            else:
                logger.warning(f"Прокси вернул код {response.status_code}")
                self.test_result.emit(0)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            logger.exception(f"Ошибка при тестировании прокси: {e}")
            self.test_result.emit(0)

    def construct_proxies(self):
        """Создает словарь с настройками прокси."""
        proxy_url = f"{self.proxy_type.lower()}://{self.proxy_ip}:{self.proxy_port}"
        if self.proxy_type.lower() in ["http", "https"]:
            return {"http": proxy_url, "https": proxy_url}
        elif self.proxy_type.lower() in ["sorks4", "socks5"]:
            return {"http": proxy_url, "https": proxy_url, "socks4": proxy_url, "socks5": proxy_url}
        return {}

class DnsSetter(QThread):
    """Класс для настройки DNS."""
    dns_result = pyqtSignal(str)

    def __init__(self, interface_name, primary_dns, secondary_dns):
        super().__init__()
        self.interface_name = interface_name
        self.primary_dns = primary_dns
        self.secondary_dns = secondary_dns

    def run(self):
        """Устанавливает DNS."""
        logger.info(f"Установка DNS для интерфейса {self.interface_name}: {self.primary_dns}, {self.secondary_dns}")
        try:
            subprocess.run(
                ["netsh", "interface", "ip", "set", "dns", f"name={self.interface_name}", "source=static", f"address={self.primary_dns}"],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            logger.info(f"Первичный DNS {self.primary_dns} установлен")
            self.dns_result.emit(f"Первичный DNS: {self.primary_dns} установлен.")

            if self.secondary_dns:
                subprocess.run(
                    ["netsh", "interface", "ip", "add", "dns", f"name={self.interface_name}", f"address={self.secondary_dns}", "index=2"],
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                logger.info(f"Вторичный DNS {self.secondary_dns} установлен")
                self.dns_result.emit(f"Вторичный DNS: {self.secondary_dns} установлен.")
        except subprocess.CalledProcessError as e:
            logger.exception(f"Ошибка при установке DNS: {e}")
            self.dns_result.emit(f"Ошибка при установке DNS: {e}")

    def clear_dns(self):
        """Очищает DNS, восстанавливая настройки по умолчанию."""
        logger.info(f"Очистка DNS для интерфейса {self.interface_name}")
        try:
            subprocess.run(
                ["netsh", "interface", "ip", "set", "dns", f"name={self.interface_name}", "source=dhcp"],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            logger.info(f"DNS для интерфейса {self.interface_name} очищены, используется DHCP")
            self.dns_result.emit(f"DNS для интерфейса {self.interface_name} очищены, используется DHCP.")
        except subprocess.CalledProcessError as e:
            logger.exception(f"Ошибка при очистке DNS: {e}")
            self.dns_result.emit(f"Ошибка при очистке DNS: {e}")

class ProxySettingsDialog(QDialog):
    """Основной класс диалога настроек прокси и DNS."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Прокси и DNS")
        self.setFixedSize(500, 600)
        self.init_ui()
        logger.info("Диалог настроек прокси и DNS инициализирован")

    def init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout()

        # Текстовое поле для вывода информации
        self.text_edit = TextEdit(self)
        self.text_edit.setPlaceholderText("Информация о прокси и DNS будет отображена здесь...")
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        # Группа для настроек прокси
        proxy_group = QGroupBox("Настройки прокси")
        proxy_group_layout = QVBoxLayout()

        proxy_input_layout = QHBoxLayout()
        self.proxy_ip_input = QLineEdit()
        self.proxy_ip_input.setPlaceholderText("Введите IP прокси")
        self.proxy_port_input = QLineEdit()
        self.proxy_port_input.setPlaceholderText("Введите порт")
        self.proxy_type_combo = QFComboBox()
        self.proxy_type_combo.addItems(["HTTP", "HTTPS", "SOCKS4", "SOCKS5"])

        proxy_input_layout.addWidget(QLabel("IP:"))
        proxy_input_layout.addWidget(self.proxy_ip_input)
        proxy_input_layout.addWidget(QLabel("Порт:"))
        proxy_input_layout.addWidget(self.proxy_port_input)
        proxy_input_layout.addWidget(QLabel("Тип:"))
        proxy_input_layout.addWidget(self.proxy_type_combo)

        proxy_group_layout.addLayout(proxy_input_layout)
        proxy_group.setLayout(proxy_group_layout)
        layout.addWidget(proxy_group)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(551)
        layout.addWidget(self.progress_bar)

        # Группа для кнопок управления прокси
        button_group = QGroupBox("Управление прокси")
        button_layout = QHBoxLayout()

        self.test_button = PushButton("Проверить прокси", self)
        self.test_button.clicked.connect(self.test_proxy)
        self.apply_button = PushButton("Применить прокси", self)
        self.apply_button.clicked.connect(self.apply_proxy)
        self.clear_button = PushButton("Сбросить прокси", self)
        self.clear_button.clicked.connect(self.clear_proxy)

        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.clear_button)

        button_group.setLayout(button_layout)
        layout.addWidget(button_group)

        # Группа для дополнительных параметров
        checkbox_group = QGroupBox("Дополнительные параметры")
        checkbox_layout = QVBoxLayout()

        self.clear_text_checkbox = QCheckBox("Очищать поле перед проверкой прокси", self)
        checkbox_layout.addWidget(self.clear_text_checkbox)
        checkbox_group.setLayout(checkbox_layout)
        layout.addWidget(checkbox_group)

        # Группа для настроек DNS
        dns_group = QGroupBox("Настройки DNS")
        dns_group_layout = QVBoxLayout()

        self.interface_combo = QFComboBox()
        self.populate_interface_list()
        dns_group_layout.addWidget(QLabel("Выберите интерфейс:"))
        dns_group_layout.addWidget(self.interface_combo)

        self.dns_type_combo = QFComboBox()
        self.dns_type_combo.addItems(DNS_SERVERS.keys())
        dns_group_layout.addWidget(QLabel("Выберите DNS:"))
        dns_group_layout.addWidget(self.dns_type_combo)

        self.apply_dns_button = PushButton("Применить DNS", self)
        self.apply_dns_button.clicked.connect(self.apply_dns)
        dns_group_layout.addWidget(self.apply_dns_button)

        dns_group.setLayout(dns_group_layout)
        layout.addWidget(dns_group)

        self.setLayout(layout)

    def populate_interface_list(self):
        """Заполняет список интерфейсов."""
        logger.info("Получение списка сетевых интерфейсов")
        try:
            output = subprocess.check_output(
                ["netsh", "interface", "show", "interface"],
                encoding="cp1251",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            lines = output.splitlines()

            for line in lines:
                if "Подключен" in line or "Connected" in line:
                    interface_name = line.split()[-1]
                    self.interface_combo.addItem(interface_name)

            if self.interface_combo.count() == 0:
                self.interface_combo.addItem("Ethernet")
                logger.warning("Список интерфейсов пуст, добавлен стандартный 'Ethernet'")
        except Exception as e:
            logger.exception(f"Ошибка при получении списка интерфейсов: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить список интерфейсов: {e}")
            self.interface_combo.addItem("Ethernet")

    def validate_proxy_input(self, proxy_ip, proxy_port):
        """Проверяет корректность введенных данных прокси."""
        if not proxy_ip or not proxy_port:
            logger.warning("Попытка проверки/применения прокси без IP или порта")
            QMessageBox.warning(self, "Ошибка", "Введите IP и порт прокси.")
            return False

        if not self.is_valid_ip(proxy_ip):
            logger.warning(f"Некорректный IP-адрес прокси: {proxy_ip}")
            QMessageBox.warning(self, "Ошибка", "Некорректный IP адрес прокси.")
            return False

        try:
            port = int(proxy_port)
            if not (0 < port < 65536):
                raise ValueError
        except ValueError:
            logger.warning(f"Некорректный порт прокси: {proxy_port}")
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом от 1 до 65535.")
            return False

        return True

    def is_valid_ip(self, ip):
        """Проверяет, является ли строка валидным IP-адресом."""
        pattern = r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return re.match(pattern, ip) is not None

    def test_proxy(self):
        """Тестирует прокси."""
        proxy_ip = self.proxy_ip_input.text().strip()
        proxy_port = self.proxy_port_input.text().strip()
        proxy_type = self.proxy_type_combo.currentText().strip()

        if not self.validate_proxy_input(proxy_ip, proxy_port):
            return

        logger.info(f"Запуск проверки прокси: {proxy_type}://{proxy_ip}:{proxy_port}")
        if self.clear_text_checkbox.isChecked():
            self.text_edit.clear()

        self.text_edit.append("Проверка прокси...")
        self.progress_bar.setVisible(True)

        self.tester = ProxyTester(proxy_ip, proxy_port, proxy_type)
        self.tester.test_result.connect(self.handle_test_result)
        self.tester.start()

    def handle_test_result(self, result):
        """Обрабатывает результат тестирования прокси."""
        self.progress_bar.setVisible(False)
        if result == 1:
            logger.info("Прокси успешно прошел проверку")
            self.text_edit.append("✅ Прокси работает успешно")
        else:
            logger.warning("Прокси не прошел проверку")
            self.text_edit.append("⛔ Прокси не работает")

    def apply_proxy(self):
        """Применяет настройки прокси."""
        proxy_ip = self.proxy_ip_input.text().strip()
        proxy_port = self.proxy_port_input.text().strip()
        proxy_type = self.proxy_type_combo.currentText().strip()

        if not self.validate_proxy_input(proxy_ip, proxy_port):
            return

        logger.info(f"Применение прокси: {proxy_type}://{proxy_ip}:{proxy_port}")
        try:
            RegistryManager.set_value(
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "ProxyEnable",
                winreg.REG_DWORD,
                1
            )
            RegistryManager.set_value(
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "ProxyServer",
                winreg.REG_SZ,
                f"{proxy_ip}:{proxy_port}"
            )
            logger.info(f"Прокси {proxy_ip}:{proxy_port} ({proxy_type}) успешно применен")
            self.text_edit.append(f"Прокси {proxy_ip}:{proxy_port} ({proxy_type}) применен.")
        except Exception as e:
            logger.exception(f"Не удалось применить настройки прокси: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось применить настройки прокси: {e}")

    def clear_proxy(self):
        """Сбрасывает настройки прокси."""
        logger.info("Сброс настроек прокси")
        try:
            RegistryManager.set_value(
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "ProxyEnable",
                winreg.REG_DWORD,
                0
            )
            logger.info("Настройки прокси успешно сброшены")
            self.text_edit.append("Прокси настройки сброшены.")
        except Exception as e:
            logger.exception(f"Не удалось сбросить настройки прокси: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сбросить настройки прокси: {e}")

    def apply_dns(self):
        """Применяет настройки DNS."""
        dns_choice = self.dns_type_combo.currentText()
        interface_name = self.interface_combo.currentText()
        primary_dns, secondary_dns = DNS_SERVERS.get(dns_choice, ("", ""))

        logger.info(f"Применение DNS для интерфейса {interface_name}: {dns_choice}")
        self.dns_setter = DnsSetter(interface_name, primary_dns, secondary_dns)
        if dns_choice == "DNS по умолчанию":
            self.dns_setter.clear_dns()
            self.text_edit.append(f"DNS для интерфейса {interface_name} по умолчанию.")
        else:
            self.dns_setter.dns_result.connect(self.handle_dns_result)
            self.dns_setter.start()
            self.text_edit.append(f"DNS для интерфейса {interface_name} установлен на {dns_choice} ({primary_dns}, {secondary_dns}).")

    def handle_dns_result(self, message):
        """Обрабатывает результат настройки DNS."""
        self.text_edit.append(message)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = ProxySettingsDialog()
    dialog.show()
    sys.exit(app.exec())