from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
from set_power_supply_window import Ui_Set_power_supply
from PyQt5 import QtCore
# Создание клиента Modbus RTU

# Отправлено главным компьютером: 01 10 00 40 00 02 04 00 00 (4E 20) (C3 E7) (При
#                                01 10 00 40 00 02 04 00 00  4E 20   C3 E7

# напряжении 200V, единица измерения 0,01 V)
# Ответ конечного устройства: 01 10 00 40 00 02 40 1C


# удаленная настройка выходного напряжения 0,01 В
class maisheng_power_class():
    def __init__(self) -> None:
        print("класс источника питания создан")
        self.client = 0
        # client.connect()
    def testprint(self,text):
        print(text)
    def show_setting_window(self):
        self.setting_window = Ui_Set_power_supply()
        self.setting_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setting_window.setupUi(self.setting_window)

        self.setting_window.type_work_enter.addItems(["Стабилизация напряжения", "Стабилизация тока", "Стабилизация мощности"])
        self.setting_window.type_work_enter.currentIndexChanged.connect(lambda: self.change_units())#если меняется режим, то нужно отобразить новые единицы измерения

        self.setting_window.triger_enter.addItems(["Таймер","Внешний сигнал"])
        self.setting_window.triger_enter.setEnabled(True)

        self.setting_window.type_step_enter.addItems(["Заданный шаг","Адаптивный шаг"])
        self.setting_window.type_step_enter.currentIndexChanged.connect(lambda: self.action_when_select_step())



        #+++++++++++++++++выбор ком порта+++++++++++++
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        active_ports = []
        for port in ports:
            try:
                # Попытаемся открыть порт
                ser = serial.Serial(port.device)
                # Если порт успешно открыт, добавляем его в список активных портов
                active_ports.append(port.device)
                # Закрываем порт
                ser.close()
            except (OSError, serial.SerialException):
                pass
        if len(active_ports) == 0:
            self.setting_window.comportslist.addItems(["Нет подключенных портов"])
        else:
            self.setting_window.comportslist.addItems(active_ports)
        #++++++++++++++++++++++++++++++++++++++++++
        self.setting_window.boudrate.addItems(["50", "75", "110", "150", "300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])





        print("открыть окно настройки прибора майшенг")
        self.setting_window.show()
        pass
    def change_units(self):
        if self.setting_window.type_work_enter.currentText() == "Стабилизация напряжения":
            self.setting_window.label_7.setText("V")
            self.setting_window.label_8.setText("V")
            self.setting_window.label_9.setText("V")
        if self.setting_window.type_work_enter.currentText() == "Стабилизация тока":
            self.setting_window.label_7.setText("A")
            self.setting_window.label_8.setText("A")
            self.setting_window.label_9.setText("A")
        if self.setting_window.type_work_enter.currentText() == "Стабилизация мощности":
            self.setting_window.label_7.setText("W")
            self.setting_window.label_8.setText("W")
            self.setting_window.label_9.setText("W")
    def action_when_select_step(self):
        if self.setting_window.type_step_enter.currentText() == "Адаптивный шаг":
            self.setting_window.step_enter.setEnabled(False)
            self.setting_window.triger_enter.clear()
            self.setting_window.triger_enter.addItems(["Внешний сигнал"])
        else:
            self.setting_window.step_enter.setEnabled(True)
            self.setting_window.triger_enter.clear()
            self.setting_window.triger_enter.addItems(["Таймер","Внешний сигнал"])


    def set_client(self, client):
        self.client = client

    def set_voltage(self, voltage):
        return self.client.write_registers(address=int("0040", 16), count=2, slave=1, values=[0, voltage])
# удаленная настройка выходного тока 0,01А

    def set_current(self, current):
        return self.client.write_registers(address=int("0041", 16), count=2, slave=1, values=[0, current])

    def output_switching_on(self):
        return self.client.write_registers(address=int("0042", 16), count=2, slave=1, values=[0, 1])

    def output_switching_off(self):
        return self.client.write_registers(address=int("0042", 16), count=2, slave=1, values=[0, 0])

    # удаленная настройка выходной частоты в Гц
    def set_frequency(self, frequency):
        high = 0
        if frequency > 65535:
            high = 1
        frequency = frequency - 65535 - 1
        return self.client.write_registers(address=int("0043", 16), count=2, slave=1, values=[high, frequency])

    def set_duty_cycle(self, duty_cycle):
        if duty_cycle > 100 or duty_cycle < 1:
            return False
        return self.client.write_registers(address=int("0044", 16), count=2, slave=1, values=[0, duty_cycle])

    def get_current_voltage(self):
        return self.client.read_input_registers(address=int("0000", 16), count=1, slave=1)

    def get_current_current(self):
        return self.client.read_input_registers(address=int("0001", 16), count=1, slave=1)

    def get_current_frequency(self):
        pass

    def get_current_duty_cycle(self):
        pass

    def get_setting_voltage(self):
        return self.client.read_holding_registers(address=int("0040", 16), count=2, slave=1)

    def get_setting_current(self):
        return self.lient.read_holding_registers(address=int("0041", 16), count=2, slave=1)

    def get_setting_frequency(self):
        return self.client.read_holding_registers(address=int("0043", 16), count=2, slave=1)

    def get_setting_state(self):
        return self.client.read_holding_registers(address=int("0042", 16), count=2, slave=1)

    def get_setting_duty_cycle(self):
        return self.client.read_holding_registers(address=int("0044", 16), count=2, slave=1)


if __name__ == "__main__":
    # Создание клиента Modbus RTU
    client = ModbusSerialClient(
        method='rtu', port='COM3', baudrate=9600, stopbits=1, bytesize=8, parity='E')

    power_supply = maisheng_power_class()
    power_supply.set_client(client)

    # set_voltage(client,20000)
    '''
    for i in range(0,20000,1000):
        set_voltage(client,i)
        time.sleep(5)
    '''
    power_supply.output_switching_off()
    power_supply.set_current(1500)
    i = power_supply.get_setting_voltage()

    print(i.registers)

    '''
    print("установка напряжения ответ", set_voltage(client,10000))
    time.sleep(1)
    print("напряжение текущее ",get_setting_voltage(client))
    time.sleep(1)
    print("установка тока ответ",set_current(client,100))
    time.sleep(1)
    print("включениие ответ",output_switching_on(client))
    time.sleep(1)
    print("напряжение текущее после включения",get_current_voltage(client))
    '''
    # client.read_discrete_inputs(address=40, count=2, slave=2)
    # client.read_exception_status()
    # client.readwrite_registers()
    # Чтение данных из регистров хранения (holding registers)
    # client.read_coils(address=40, count=2, slave=2)
    # result = client.read_holding_registers(address=2, count=5, unit=1)
    # if result.isError():
    # print("Ошибка чтения данных:", result)
    # else:
    # print("Прочитанные данные:", result.registers)

    # Запись данных в регистры хранения
    '''
    data = [10, 20, 30, 40, 50]
    result = client.write_registers(address=0, values=data, unit=1)
    if result.isError():
        print("Ошибка записи данных:", result)
    else:
        print("Данные успешно записаны")
    '''
    # Закрытие соединения
    client.close()
