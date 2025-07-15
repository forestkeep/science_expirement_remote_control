import sys
import logging
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLineEdit, QPushButton, QLabel, QTextEdit, 
                            QGroupBox, QCheckBox, QGridLayout, QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QTime, QDate
from time import sleep
import csv

logger = logging.getLogger(__name__)

# Параметры подключения (изменяемый порт)
PORT = "COM4"
BAUDRATE = 19200
PARITY = "N"
STOPBITS = 1
BYTESIZE = 8
TIMEOUT = 1
SLAVE_ID = 1
RETRY_ATTEMPTS = 3

# Определение всех регистров с диапазонами и единицами измерения
REGISTERS = {
    'Измеренная температура (PV)': {'address': 0x0000, 'access': 'R', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Текущая измеренная температура'},
    'Индикатор LED (LED)': {'address': 0x0001, 'access': 'R', 'range': (0, 1), 'unit': '', 'tooltip': 'Состояние индикатора LED (0/1)'},
    'Заданная температура (SV)': {'address': 0x0002, 'access': 'R/W', 'range': (1, 9999), 'unit': '°C', 'tooltip': 'Заданное значение температуры'},
    'Процент выхода (OUT)': {'address': 0x0003, 'access': 'R', 'range': (0, 100.0), 'unit': '%', 'tooltip': 'Процент выходного сигнала'},
    'Автотюнинг (AT)': {'address': 0x0004, 'access': 'R/W', 'range': (0, 1), 'unit': '', 'tooltip': 'Включение/выключение автотюнинга (0 - выкл, 1 - вкл)'},
    'Тревога 1 (AL1)': {'address': 0x0005, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Значение первой тревоги'},
    'Тревога 2 (AL2)': {'address': 0x0006, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Значение второй тревоги'},
    'Гистерезис тревоги 1 (HY1)': {'address': 0x0007, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Гистерезис для первой тревоги'},
    'Гистерезис тревоги 2 (HY2)': {'address': 0x0008, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Гистерезис для второй тревоги'},
    'Пропорциональная составляющая (P)': {'address': 0x0009, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Пропорциональная часть ПИД-регулятора'},
    'Интегральная составляющая (I)': {'address': 0x000A, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Интегральная часть ПИД-регулятора'},
    'Дифференциальная составляющая (D)': {'address': 0x000B, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Дифференциальная часть ПИД-регулятора'},
    'Подавление перерегулирования (AR)': {'address': 0x000C, 'access': 'R/W', 'range': (0, 100.0), 'unit': '%', 'tooltip': 'Подавление интегрального перерегулирования'},
    'Цикл управления (T)': {'address': 0x000D, 'access': 'R/W', 'range': (0.5, 120.0), 'unit': 'с', 'tooltip': 'Период цикла управления'},
    'Коррекция измерения (PB_SC)': {'address': 0x000E, 'access': 'R/W', 'range': (-999.9, 999.9), 'unit': '°C', 'tooltip': 'Коррекция значения измерения'},
    'Мёртвая зона (HY)': {'address': 0x000F, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Мёртвая зона при P=0'},
    'Метод тревоги 1 (AL1T)': {'address': 0x0010, 'access': 'R/W', 'range': (0, 1), 'unit': '', 'tooltip': 'Метод активации первой тревоги (0/1)'},
    'Метод тревоги 2 (AL2T)': {'address': 0x0011, 'access': 'R/W', 'range': (0, 1), 'unit': '', 'tooltip': 'Метод активации второй тревоги (0/1)'},
    'Пропорциональность выхода 2 (PC)': {'address': 0x0012, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Пропорциональность второго выхода'},
    'Цикл управления выхода 2 (TC)': {'address': 0x0013, 'access': 'R/W', 'range': (0.5, 120.0), 'unit': 'с', 'tooltip': 'Период цикла второго выхода'},
    'Зона нечувствительности (DB)': {'address': 0x0014, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Зона нечувствительности'},
    'Вход детектора тока (CTH)': {'address': 0x0015, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Значение входа детектора тока'},
    'Значение аварийного обрыва (ACT)': {'address': 0x0016, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Значение для сигнала обрыва'},
    'Переключатель таймера (TON)': {'address': 0x0017, 'access': 'R', 'range': (0, 1), 'unit': '', 'tooltip': 'Состояние переключателя таймера (0/1)'},
    'Режим таймера (ET)': {'address': 0x0018, 'access': 'R/W', 'range': (0, 1), 'unit': '', 'tooltip': 'Режим работы таймера (0/1)'},
    'Единица времени таймера (TIE)': {'address': 0x0019, 'access': 'R/W', 'range': (0, 1), 'unit': '', 'tooltip': 'Единица времени таймера (0 - сек, 1 - мин)'},
    'Зона мёртвого времени таймера (ALT)': {'address': 0x001A, 'access': 'R/W', 'range': (0, 999.9), 'unit': '°C', 'tooltip': 'Зона мёртвого времени для таймера'},
    'Время тревоги после окончания (BL)': {'address': 0x001B, 'access': 'R/W', 'range': (0, 999.9), 'unit': 'с', 'tooltip': 'Время активации тревоги после таймера'},
    'Длительность таймера (ST)': {'address': 0x001C, 'access': 'R/W', 'range': (0, 9999), 'unit': 'с', 'tooltip': 'Общая длительность работы таймера'},
    'Текущее значение таймера (TIM)': {'address': 0x001D, 'access': 'R', 'range': (0, 9999), 'unit': 'с', 'tooltip': 'Текущее значение таймера'},
    'Текущее значение таймера в секундах (TIS)': {'address': 0x001E, 'access': 'R', 'range': (0, 9999), 'unit': 'с', 'tooltip': 'Текущее значение таймера в секундах'}
}

class PIDRegulatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Панель управления ПИД-регулятором")
        self.client = None
        self.read_fields = {}
        self.write_fields = {}
        self.measured_values = []  # Для хранения измеренных значений
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_measurements)
        self.is_measuring = False
        self.measure_count = 0  # Счетчик измерений
        self.init_ui()
        #self.connect_modbus()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Фиксированная панель управления
        control_layout = QHBoxLayout()
        
        # Поле для выбора порта
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Порт:"))
        self.port_input = QLineEdit(PORT)
        self.port_input.setToolTip("Укажите COM-порт устройства (например, COM4)")
        port_button = QPushButton("Применить порт")
        port_button.clicked.connect(self.update_port)
        port_layout.addWidget(self.port_input)
        port_layout.addWidget(port_button)
        control_layout.addLayout(port_layout)

        # Настройка времени между измерениями
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Интервал измерений (с):"))
        self.interval_input = QLineEdit("1")
        self.interval_input.setToolTip("Укажите интервал обновления измерений от 0.5 до 300 с")
        interval_layout.addWidget(self.interval_input)
        control_layout.addLayout(interval_layout)

        # Кнопка измерения
        self.measure_button = QPushButton("Измерить")
        self.measure_button.clicked.connect(self.measure_once)
        control_layout.addWidget(self.measure_button)
        
        # Кнопка включения/выключения измерений
        self.measure_toggle = QPushButton("Включить измерения")
        self.measure_toggle.clicked.connect(self.toggle_measurements)
        control_layout.addWidget(self.measure_toggle)
        
        # Кнопка сохранения измерений
        self.save_measurements_button = QPushButton("Сохранить измерения")
        self.save_measurements_button.clicked.connect(self.save_measurements)
        control_layout.addWidget(self.save_measurements_button)
        
        main_layout.addLayout(control_layout)

        # Блок настроек прибора
        write_scroll = QScrollArea()
        write_widget = QWidget()
        write_layout = QVBoxLayout(write_widget)
        write_groups = [
            ("Основные настройки", ['Заданная температура (SV)', 'Автотюнинг (AT)']),
            ("Настройки ПИД", ['Пропорциональная составляющая (P)', 'Интегральная составляющая (I)', 'Дифференциальная составляющая (D)', 'Цикл управления (T)']),
            ("Настройки тревог", ['Тревога 1 (AL1)', 'Тревога 2 (AL2)', 'Гистерезис тревоги 1 (HY1)', 'Гистерезис тревоги 2 (HY2)', 'Метод тревоги 1 (AL1T)', 'Метод тревоги 2 (AL2T)']),
            ("Дополнительные настройки", ['Подавление перерегулирования (AR)', 'Коррекция измерения (PB_SC)', 'Мёртвая зона (HY)', 'Зона нечувствительности (DB)', 'Вход детектора тока (CTH)', 'Значение аварийного обрыва (ACT)']),
            ("Настройки таймера", ['Режим таймера (ET)', 'Единица времени таймера (TIE)', 'Зона мёртвого времени таймера (ALT)', 'Время тревоги после окончания (BL)', 'Длительность таймера (ST)'])
        ]
        for group_title, params in write_groups:
            group_box = QGroupBox(group_title)
            grid_layout = QGridLayout()
            group_box.setLayout(grid_layout)
            for i, param in enumerate(params):
                reg_data = REGISTERS[param]
                h_layout = QHBoxLayout()
                h_layout.setAlignment(Qt.AlignCenter)  # Выравнивание по центру
                label = QLabel(f"{param}:")
                label.setToolTip(reg_data['tooltip'])
                h_layout.addWidget(label)
                if reg_data['range'] == (0, 1):
                    write_input = QCheckBox()
                    write_input.setToolTip(reg_data['tooltip'])
                    h_layout.addWidget(write_input, alignment=Qt.AlignCenter)  # Центрирование чекбокса
                else:
                    write_input = QLineEdit()
                    write_input.setFixedWidth(60)  # Уменьшенное поле ввода
                    write_input.setToolTip(reg_data['tooltip'])
                    h_layout.addWidget(write_input, alignment=Qt.AlignCenter)  # Центрирование поля ввода
                write_button = QPushButton("Записать")
                write_button.setFixedSize(100, 30)  # Единый размер для всех кнопок
                write_button.clicked.connect(lambda checked, p=param, w=write_input: self.write_register_action(p, w.text() if isinstance(w, QLineEdit) else str(int(w.isChecked()))))
                h_layout.addWidget(write_button, alignment=Qt.AlignCenter)  # Центрирование кнопки
                self.write_fields[param] = write_input
                col = i // (len(params) // 2 + len(params) % 2)  # Два столбца
                row = i % (len(params) // 2 + len(params) % 2)  # Распределение по строкам
                grid_layout.addLayout(h_layout, row, col * 2)  # Выравнивание по столбцам
            write_layout.addWidget(group_box)
        write_widget.setLayout(write_layout)
        write_scroll.setWidget(write_widget)
        write_scroll.setWidgetResizable(True)
        main_layout.addWidget(write_scroll)

        # Блок логов
        log_scroll = QScrollArea()
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)  # Уменьшенная высота лога
        log_layout.addWidget(QLabel("Логи операций:"))
        log_layout.addWidget(self.log_text)

        # Кнопки управления логом
        log_buttons_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("Очистить логи")
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button = QPushButton("Сохранить логи")
        self.save_log_button.clicked.connect(self.save_log)
        log_buttons_layout.addWidget(self.clear_log_button)
        log_buttons_layout.addWidget(self.save_log_button)
        log_layout.addLayout(log_buttons_layout)
        
        log_widget.setLayout(log_layout)
        log_scroll.setWidget(log_widget)
        log_scroll.setWidgetResizable(True)
        main_layout.addWidget(log_scroll)

        # Статус
        self.status_label = QLabel("Статус: Не подключено")
        main_layout.addWidget(self.status_label)

    def connect_modbus(self):
        """Инициализация и подключение к Modbus устройству"""
        global PORT
        self.client = ModbusSerialClient(
            port=PORT,
            baudrate=BAUDRATE,
            parity=PARITY,
            stopbits=STOPBITS,
            bytesize=BYTESIZE,
            timeout=TIMEOUT
        )
        attempt = 0
        while attempt < RETRY_ATTEMPTS:
            try:
                if self.client.connect():
                    self.status_label.setStyleSheet("color: green")
                    self.status_label.setText("Статус: Подключено")
                    self.log_text.append("Успешно подключено к устройству")
                    logger.info("Успешно подключено к устройству")
                    return True
                else:
                    attempt += 1
                    self.log_text.append(f"Не удалось подключиться, попытка {attempt}/{RETRY_ATTEMPTS}")
                    logger.warning(f"Не удалось подключиться, попытка {attempt}/{RETRY_ATTEMPTS}")
                    sleep(2)
            except PermissionError as e:
                self.log_text.append(f"Ошибка доступа: {e}. Запустите от администратора")
                logger.error(f"Ошибка доступа: {e}")
                self.status_label.setStyleSheet("color: red")
                self.status_label.setText("Статус: Ошибка доступа")
                return False
            except Exception as e:
                self.log_text.append(f"Ошибка: {e}")
                logger.error(f"Ошибка: {e}")
                attempt += 1
                sleep(2)
        
        self.log_text.append("Все попытки подключения исчерпаны")
        logger.error("Все попытки подключения исчерпаны")
        self.status_label.setStyleSheet("color: red")
        self.status_label.setText("Статус: Ошибка подключения")
        return False

    def update_port(self):
        """Обновление порта подключения"""
        global PORT
        new_port = self.port_input.text().strip()
        if new_port and new_port != PORT:
            print(f"Порт изменен на {new_port}")
            PORT = new_port
            if self.client:
                self.client.close()
            if self.connect_modbus():
                self.log_text.append(f"Порт изменен на {PORT} и подключение установлено")
                logger.info(f"Порт изменен на {PORT}")
            else:
                self.log_text.append(f"Не удалось подключиться к новому порту {PORT}")
                logger.error(f"Не удалось подключиться к новому порту {PORT}")

    def read_register(self, param):
        """Чтение значения регистра"""
        if not self.client or not self.client.is_socket_open():
            self.log_text.append("Ошибка: Не подключено к устройству")
            logger.error("Чтение не выполнено: не подключено")
            return None
        reg_data = REGISTERS[param]
        try:
            result = self.client.read_holding_registers(address=reg_data['address'], count=1, slave=SLAVE_ID)
            if not result.isError():
                value = result.registers[0]
                if reg_data['range'][0] <= value <= reg_data['range'][1]:
                    logger.info(f"Чтение {param}: {value}")
                    return value
                else:
                    logger.error(f"{param} вне диапазона: {value}")
                    return None
            else:
                logger.error(f"Ошибка чтения {param}: {result}")
                return None
        except ModbusException as e:
            logger.error(f"Modbus ошибка чтения {param}: {e}")
            return None

    def write_register_action(self, param, value_text):
        """Обработка записи значения в регистр по нажатию кнопки"""
        try:
            value = float(value_text) if value_text else 0
            if self.write_register(param, value):
                self.log_text.append(f"Запись {value} в {param} выполнена")
        except ValueError:
            self.log_text.append(f"Ошибка: Некорректное значение для {param}")
            logger.error(f"Некорректное значение для {param}: {value_text}")

    def write_register(self, param, value):
        """Запись значения в регистр"""
        if not self.client or not self.client.is_socket_open():
            self.log_text.append("Ошибка: Не подключено к устройству")
            logger.error("Запись не выполнена: не подключено")
            return False
        reg_data = REGISTERS[param]
        if reg_data['access'] == 'R':
            self.log_text.append(f"Ошибка: {param} только для чтения")
            logger.error(f"Попытка записи в только для чтения регистр {param}")
            return False
        try:
            if reg_data['range'][0] <= value <= reg_data['range'][1]:
                result = self.client.write_register(address=reg_data['address'], value=int(value), slave=SLAVE_ID)
                if not result.isError():
                    self.log_text.append(f"Успешно записано {value} в {param}")
                    logger.info(f"Успешно записано {value} в {param}")
                    return True
                else:
                    self.log_text.append(f"Ошибка записи в {param}: {result}")
                    logger.error(f"Ошибка записи в {param}: {result}")
                    return False
            else:
                self.log_text.append(f"Ошибка: {value} вне диапазона {reg_data['range']} для {param}")
                logger.error(f"Значение {value} вне диапазона для {param}")
                return False
        except ModbusException as e:
            self.log_text.append(f"Modbus ошибка записи в {param}: {e}")
            logger.error(f"Modbus ошибка записи в {param}: {e}")
            return False

    def write_all(self):
        """Запись всех данных из полей ввода"""
        success = True
        for param in self.write_fields:
            value_text = self.write_fields[param].text().strip() if isinstance(self.write_fields[param], QLineEdit) else str(int(self.write_fields[param].isChecked()))
            if value_text:
                try:
                    value = float(value_text)
                    if not self.write_register(param, value):
                        success = False
                except ValueError:
                    self.log_text.append(f"Ошибка: Некорректное значение для {param}")
                    logger.error(f"Некорректное значение для {param}: {value_text}")
                    success = False
        if success:
            self.log_text.append("Все данные успешно записаны")
            logger.info("Все данные успешно записаны")
        else:
            self.log_text.append("Ошибка при записи некоторых данных")
            logger.error("Ошибка при записи некоторых данных")

    def update_measurements(self):
        """Обновление измеренных значений с заданным интервалом"""
        if self.is_measuring:
            self.measure_count += 1
            current_values = {}
            for param in REGISTERS:
                if REGISTERS[param]['access'] == 'R':
                    value = self.read_register(param)
                    current_values[param] = value if value is not None else "Ошибка"
            self.measured_values.append((self.measure_count, QTime.currentTime().toString("hh:mm:ss") + " " + QDate.currentDate().toString("dd.MM.yyyy"), current_values))

    def toggle_measurements(self):
        """Включение/выключение периодических измерений"""
        if not self.is_measuring:
            try:
                interval = float(self.interval_input.text().strip())
                if 0.5 <= interval <= 300:
                    self.timer.start(int(interval * 1000))  # Преобразование в миллисекунды
                    self.is_measuring = True
                    self.measure_toggle.setText("Выключить измерения")
                    self.log_text.append(f"Периодические измерения включены с интервалом {interval} с")
                    logger.info(f"Периодические измерения включены с интервалом {interval} с")
                    self.measure_count = 0
                    self.measured_values = []  # Очистка перед началом измерений
                else:
                    self.log_text.append("Ошибка: Интервал должен быть от 0.5 до 300 с")
                    logger.error("Интервал вне допустимого диапазона")
            except ValueError:
                self.log_text.append("Ошибка: Некорректный интервал")
                logger.error("Некорректный интервал")
        else:
            self.timer.stop()
            self.is_measuring = False
            self.measure_toggle.setText("Включить измерения")
            self.log_text.append("Периодические измерения выключены")
            logger.info("Периодические измерения выключены")
            self.show_measurement_window()

    def measure_once(self):
        """Однократное измерение всех данных"""
        self.measure_count += 1
        current_values = {}
        for param in REGISTERS:
            if REGISTERS[param]['access'] == 'R':
                value = self.read_register(param)
                current_values[param] = value if value is not None else "Ошибка"
        self.measured_values.append((self.measure_count, QTime.currentTime().toString("hh:mm:ss") + " " + QDate.currentDate().toString("dd.MM.yyyy"), current_values))
        self.show_measurement_window()

    def show_measurement_window(self):
        """Отображение окна с текущими измеренными значениями"""
        if not self.measured_values:
            QMessageBox.warning(self, "Ошибка", "Нет данных для отображения")
            return
        latest_measure = self.measured_values[-1]
        message = f"Номер измерения: {latest_measure[0]}\nВремя измерения: {latest_measure[1]}\n"
        for param, value in latest_measure[2].items():
            message += f"{param}: {value} {REGISTERS[param]['unit']}\n"
        QMessageBox.information(self, "Измеренные значения", message)

    def save_measurements(self):
        """Сохранение измеренных значений в файл"""
        if not self.measured_values:
            self.log_text.append("Ошибка: Нет данных для сохранения")
            logger.error("Попытка сохранения без данных")
            return
        timestamp = QTime.currentTime().toString("hh:mm:ss") + " " + QDate.currentDate().toString("dd.MM.yyyy")
        filename = f"measurements_{timestamp.replace(':', '-').replace('.', '-')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ["Номер измерения", "Время измерения"] + [param for param in REGISTERS.keys() if REGISTERS[param]['access'] == 'R']
            writer.writerow(header)
            for measure in self.measured_values:
                row = [measure[0], measure[1]] + [str(measure[2].get(param, "N/A")) for param in REGISTERS.keys() if REGISTERS[param]['access'] == 'R']
                writer.writerow(row)
        self.log_text.append(f"Измерения сохранены в {filename}")
        logger.info(f"Измерения сохранены в {filename}")
        self.measured_values = []  # Очистка после сохранения

    def clear_log(self):
        """Очистка логов в интерфейсе"""
        self.log_text.clear()
        self.log_text.append("Логи очищены")
        logger.info("Логи в интерфейсе очищены")

    def save_log(self):
        """Сохранение логов в отдельный файл"""
        with open('pid_regulator_log_backup.txt', 'w', encoding='utf-8') as f:
            f.write(self.log_text.toPlainText())
        self.log_text.append("Логи сохранены в pid_regulator_log_backup.txt")
        logger.info("Логи сохранены в pid_regulator_log_backup.txt")

    def closeEvent(self, event):
        """Закрытие соединения при выходе"""
        if self.client:
            self.timer.stop()
            self.client.close()
            self.log_text.append("Соединение закрыто")
            logger.info("Соединение закрыто")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PIDRegulatorGUI()
    window.show()
    sys.exit(app.exec_())