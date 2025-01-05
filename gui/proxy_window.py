import sys
import re
import subprocess
import winreg
import requests

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QMessageBox, QCheckBox, QGroupBox
from qfluentwidgets import PushButton, TextEdit, ComboBox as QFComboBox

from utils.utils import tr

class ProxyTester(QThread):
    test_result = pyqtSignal(int)

    def __init__(self, proxy_ip, proxy_port, proxy_type):
        super().__init__()
        self.proxy_ip = proxy_ip
        self.proxy_port = proxy_port
        self.proxy_type = proxy_type

    def run(self):
        try:
            proxies = self.construct_proxies()
            response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=5)

            if 200 <= response.status_code < 300:
                self.test_result.emit(1)
            else:
                self.test_result.emit(0)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
            self.test_result.emit(0)

    def construct_proxies(self):
        proxy_url = f"{self.proxy_type.lower()}://{self.proxy_ip}:{self.proxy_port}"
        
        # Проверяем тип прокси и добавляем соответствующий протокол
        if self.proxy_type.lower() in ["http", "https"]:
            return {
                "http": proxy_url,
                "https": proxy_url
            }
        elif self.proxy_type.lower() in ["socks4", "socks5"]:
            return {
                "http": proxy_url,
                "https": proxy_url,
                "socks4": proxy_url,
                "socks5": proxy_url
            }
        else:
            return {}

class DnsSetter(QThread):
    dns_result = pyqtSignal(str)

    def __init__(self, interface_name, primary_dns, secondary_dns):
        super().__init__()
        self.interface_name = interface_name
        self.primary_dns = primary_dns
        self.secondary_dns = secondary_dns

    def run(self):
        try:
            # Устанавливаем первичный DNS
            subprocess.run(
                ["netsh", "interface", "ip", "set", "dns", f"name={self.interface_name}", f"source=static", f"address={self.primary_dns}"],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW 

            )
            self.dns_result.emit(f"Первичный DNS: {self.primary_dns} установлен.")

            # Устанавливаем вторичный DNS
            subprocess.run(
                ["netsh", "interface", "ip", "add", "dns", f"name={self.interface_name}", f"address={self.secondary_dns}", "index=2"],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.dns_result.emit(f"{tr('Вторичный DNS:')} {self.secondary_dns} {tr('установлен.')}")
        except subprocess.CalledProcessError as e:
            self.dns_result.emit(f"{tr('Ошибка при установке DNS:')} {e}")

    def clear_dns(self):
        try:
            # Восстановление настройки DNS с DHCP (удаляем статические DNS)
            subprocess.run(
                ["netsh", "interface", "ip", "set", "dns", f"name={self.interface_name}", "source=dhcp"], 
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.dns_result.emit(f"{tr('DNS для интерфейса')} {self.interface_name} {tr('очищены, используется DHCP.')}")
        except subprocess.CalledProcessError as e:
            self.dns_result.emit(f"{tr('Ошибка при очистке DNS:')} {e}")

class ProxySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Прокси и DNS"))
        self.setFixedSize(500, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Проверка текущих настроек прокси
        current_proxy = self.get_current_proxy_settings()
        self.text_edit = TextEdit(self)
        if current_proxy:
            self.text_edit.setText(f"{tr('Текущие настройки прокси:')} {current_proxy}")
        else:
            self.text_edit.setPlaceholderText(tr("Информация о прокси будет отображена здесь..."))
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        # Создаем группу для ввода данных прокси
        proxy_group = QGroupBox(tr("Настройки прокси"))
        proxy_group_layout = QVBoxLayout()

        proxy_input_layout = QHBoxLayout()
        self.proxy_ip_input = QLineEdit()
        self.proxy_ip_input.setPlaceholderText(tr("Введите IP прокси"))
        self.proxy_port_input = QLineEdit()
        self.proxy_port_input.setPlaceholderText(tr("Введите порт"))
        self.proxy_type_combo = QFComboBox()
        self.proxy_type_combo.addItems(["HTTP", "HTTPS", "SOCKS4", "SOCKS5"])

        proxy_input_layout.addWidget(QLabel("IP:"))
        proxy_input_layout.addWidget(self.proxy_ip_input)
        proxy_input_layout.addWidget(QLabel(tr("Порт:")))
        proxy_input_layout.addWidget(self.proxy_port_input)
        proxy_input_layout.addWidget(QLabel(tr("Тип:")))
        proxy_input_layout.addWidget(self.proxy_type_combo)

        proxy_group_layout.addLayout(proxy_input_layout)
        proxy_group.setLayout(proxy_group_layout)

        layout.addWidget(proxy_group)

        # Прогресс-бар 
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  
        self.progress_bar.setVisible(False)  
        layout.addWidget(self.progress_bar)
        self.progress_bar.setFixedWidth(551)

        # Создаем группу для кнопок
        button_group = QGroupBox(tr("Управление прокси"))
        button_layout = QHBoxLayout()

        self.test_button = PushButton(tr("Проверить прокси"), self)
        self.test_button.clicked.connect(self.test_proxy)
        self.apply_button = PushButton(tr("Применить прокси"), self)
        self.apply_button.clicked.connect(self.apply_proxy)
        self.clear_button = PushButton(tr("Сбросить прокси"), self)
        self.clear_button.clicked.connect(self.clear_proxy)

        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.clear_button)

        button_group.setLayout(button_layout)

        layout.addWidget(button_group)

        # Дополнительные параметры
        checkbox_group = QGroupBox(tr("Дополнительные параметры"))
        checkbox_layout = QVBoxLayout()

        self.clear_text_checkbox = QCheckBox(tr("Очищать поле перед проверкой прокси"), self)
        checkbox_layout.addWidget(self.clear_text_checkbox)
        checkbox_group.setLayout(checkbox_layout)

        layout.addWidget(checkbox_group)

        dns_group = QGroupBox(tr("Настройки DNS"))
        dns_group_layout = QVBoxLayout()

        # Выпадающий список для выбора интерфейса
        self.interface_combo = QFComboBox()
        self.populate_interface_list()
        dns_group_layout.addWidget(QLabel(tr("Выберите интерфейс:")))
        dns_group_layout.addWidget(self.interface_combo)

        # Выпадающее меню для выбора типа DNS
        self.dns_type_combo = QFComboBox()
        self.dns_type_combo.addItems([
            tr("Google Public DNS"), 
            tr("Cloudflare DNS"), 
            tr("AdGuard DNS"),
            tr("Comss DNS"),
            tr("DNS по умолчанию")
        ])
        dns_group_layout.addWidget(QLabel(tr("Выберите DNS:")))
        dns_group_layout.addWidget(self.dns_type_combo)

        # Кнопка для применения DNS
        self.apply_dns_button = PushButton(tr("Применить DNS"), self)
        self.apply_dns_button.clicked.connect(self.apply_dns)
        dns_group_layout.addWidget(self.apply_dns_button)

        dns_group.setLayout(dns_group_layout) 
        layout.addWidget(dns_group)

        self.setLayout(layout)

    def populate_interface_list(self):
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
                self.interface_combo.addItem("Ethernet")  # Значение по умолчанию

        except Exception as e:
            QMessageBox.critical(self, tr("Ошибка"), f"{tr('Не удалось получить список интерфейсов:')} {e}")
            self.interface_combo.addItem("Ethernet") 

    def get_current_proxy_settings(self):
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            internet_settings = winreg.OpenKey(
                registry,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0,
                winreg.KEY_READ
            )

            proxy_enable = winreg.QueryValueEx(internet_settings, "ProxyEnable")[0]
            proxy_server = winreg.QueryValueEx(internet_settings, "ProxyServer")[0] if proxy_enable else ""

            winreg.CloseKey(internet_settings)
            winreg.CloseKey(registry)

            if proxy_enable and proxy_server:
                return proxy_server
            else:
                return None
        except Exception as e:
            return f"{tr('Ошибка:')} {e}"

    def is_valid_ip(self, ip):
        pattern = r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return re.match(pattern, ip) is not None

    def test_proxy(self):
        proxy_ip = self.proxy_ip_input.text().strip()
        proxy_port = self.proxy_port_input.text().strip()
        proxy_type = self.proxy_type_combo.currentText().strip()

        if not proxy_ip or not proxy_port:
            QMessageBox.warning(self, tr("Ошибка"), tr("Введите IP и порт прокси."))
            return

        if not self.is_valid_ip(proxy_ip):
            QMessageBox.warning(self, tr("Ошибка"), tr("Некорректный IP адрес прокси."))
            return

        try:
            port = int(proxy_port)
            if not (0 < port < 65536):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, tr("Ошибка"), tr("Порт должен быть числом от 1 до 65535."))
            return

        if self.clear_text_checkbox.isChecked():
            self.text_edit.clear()

        self.text_edit.append(tr("Проверка прокси..."))
        self.progress_bar.setVisible(True)

        self.tester = ProxyTester(proxy_ip, proxy_port, proxy_type)
        self.tester.test_result.connect(self.handle_test_result)
        self.tester.start()

    def handle_test_result(self, result):
        self.progress_bar.setVisible(False)
        if result == 1:
            self.text_edit.append(tr("✅ Прокси работает успешно"))
        else:
            self.text_edit.append(tr("⛔ Прокси не работает"))
    
    def apply_proxy(self):
        proxy_ip = self.proxy_ip_input.text().strip()
        proxy_port = self.proxy_port_input.text().strip()
        proxy_type = self.proxy_type_combo.currentText().strip()

        if not proxy_ip or not proxy_port:
            QMessageBox.warning(self, tr("Ошибка"), tr("Введите IP и порт прокси."))
            return

        if not self.is_valid_ip(proxy_ip):
            QMessageBox.warning(self, tr("Ошибка"), tr("Некорректный IP адрес прокси."))
            return

        try:
            port = int(proxy_port)
            if not (0 < port < 65536):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, tr("Ошибка"), tr("Порт должен быть числом от 1 до 65535."))
            return

        self.set_proxy_settings(proxy_ip, proxy_port, proxy_type)

    def set_registry_value(self, registry_path, value_name, value_type, value_data):
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, registry_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, value_name, 0, value_type, value_data)
            winreg.CloseKey(key)
            winreg.CloseKey(registry)
        except Exception as e:
            QMessageBox.critical(self, tr("Ошибка"), f"{tr('Не удалось установить значение в реестр:')} {e}")

    
    def set_proxy_settings(self, proxy_ip, proxy_port, proxy_type):
        try:
            # Устанавливаем настройки прокси в реестр
            self.set_registry_value(
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 
                "ProxyEnable", 
                winreg.REG_DWORD, 
                1
            )
            self.set_registry_value(
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 
                "ProxyServer", 
                winreg.REG_SZ, 
                f"{proxy_ip}:{proxy_port}"
            )

            self.text_edit.append(f"{tr('Прокси')} {proxy_ip}:{proxy_port} ({proxy_type}) {tr('применен.')}")
        except Exception as e:
            QMessageBox.critical(self, tr("Ошибка"), f"{tr('Не удалось применить настройки прокси:')} {e}")


    def clear_proxy(self):
        try:
            # Сбрасываем настройки прокси в реестре
            self.set_registry_value(
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 
                "ProxyEnable", 
                winreg.REG_DWORD, 
                0
            )

            self.text_edit.append(tr("Прокси настройки сброшены."))
        except Exception as e:
            QMessageBox.critical(self, tr("Ошибка"), f"{tr('Не удалось сбросить настройки прокси:')} {e}")


    def apply_dns(self):
        dns_choice = self.dns_type_combo.currentText()
        interface_name = self.interface_combo.currentText()

        # Если выбрано "Отключить DNS", очищаем DNS
        if dns_choice == tr("DNS по умолчанию"):
            self.dns_setter = DnsSetter(interface_name, "", "")
            self.dns_setter.clear_dns()  # Очищаем DNS
            self.text_edit.append(f"{tr('DNS для интерфейса')} {interface_name} {tr('по умолчанию.')}")

        # Для других вариантов применяем соответствующие DNS
        elif dns_choice == tr("Google Public DNS"):
            self.dns_setter = DnsSetter(interface_name, "8.8.8.8", "8.8.4.4")
            self.dns_setter.start()  # Применяем DNS Google
            self.text_edit.append(f"{tr('DNS для интерфейса')} {interface_name} {tr('установлен на Google Public DNS (8.8.8.8, 8.8.4.4).')}")

        elif dns_choice == tr("Cloudflare DNS"):
            self.dns_setter = DnsSetter(interface_name, "1.1.1.1", "1.0.0.1")
            self.dns_setter.start()  # Применяем DNS Cloudflare
            self.text_edit.append(f"{tr('DNS для интерфейса')} {interface_name} {tr('установлен на Cloudflare DNS (1.1.1.1, 1.0.0.1).')}")

        elif dns_choice == tr("AdGuard DNS"):
            self.dns_setter = DnsSetter(interface_name, "94.140.14.14", "94.140.15.15")
            self.dns_setter.start()  # Применяем AdGuard DNS
            self.text_edit.append(f"{tr('DNS для интерфейса')} {interface_name} {tr('установлен на AdGuard DNS (94.140.14.14, 94.140.15.15).')}")    

        elif dns_choice == tr("Comss DNS"):
            self.dns_setter = DnsSetter(interface_name, "208.67.222.222", "208.67.220.220")
            self.dns_setter.start()  # Применяем DNS ComsDNS
            self.text_edit.append(f"{tr('DNS для интерфейса')} {interface_name} {tr('установлен на ComsDNS (208.67.222.222, 208.67.220.220).')}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = ProxySettingsDialog()
    dialog.show()
    sys.exit(app.exec())
