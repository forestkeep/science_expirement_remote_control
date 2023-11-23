from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
import time

# Создание клиента Modbus RTU
client = ModbusSerialClient(
    method='rtu', port='COM3', baudrate=9600, stopbits=1, bytesize=8, parity='E')
#computeCRC()

#Отправлено главным компьютером: 01 10 00 40 00 02 04 00 00 (4E 20) (C3 E7) (При
#                                01 10 00 40 00 02 04 00 00  4E 20   C3 E7
  



#напряжении 200V, единица измерения 0,01 V)
#Ответ конечного устройства: 01 10 00 40 00 02 40 1C

# Открытие соединения
ans = client.connect()
def set_voltage(ModbusSerialClient: client,voltage):#удаленная настройка выходного напряжения 0,01 В
    return client.write_registers(address=int ("0040",16), count=2, slave=1,values=[0,voltage])
    return True

def set_current(ModbusSerialClient: client,current):#удаленная настройка выходного тока 0,01А
    return client.write_registers(address=int ("0041",16), count=2, slave=1,values=[0,current])
    return True

def output_switching_on(ModbusSerialClient: client):
    return client.write_registers(address=int ("0042",16), count=2, slave=1,values=[0,1])
    return True

def output_switching_off(ModbusSerialClient: client):
    return client.write_registers(address=int ("0042",16), count=2, slave=1,values=[0,0])
    return True

def set_frequency(ModbusSerialClient: client,frequency):#удаленная настройка выходной частоты в Гц
    high = 0 
    if frequency > 65535:
        high = 1
        frequency = frequency - 65535 - 1
    return client.write_registers(address=int ("0043",16), count=2, slave=1,values=[high,frequency])
    return True

def set_duty_cycle(ModbusSerialClient: client,duty_cycle):
    if duty_cycle > 100 or duty_cycle < 1:
        return False
    return client.write_registers(address=int ("0044",16), count=2, slave=1,values=[0,duty_cycle])
    return True


def get_current_voltage(ModbusSerialClient: client):
    return client.read_input_registers(address=int ("0000",16), count=1, slave=1)
    pass
def get_current_current(ModbusSerialClient: client):
    return client.read_input_registers(address=int ("0001",16), count=1, slave=1)
    pass
def get_current_frequency(ModbusSerialClient: client):
    pass
def get_current_duty_cycle(ModbusSerialClient: client):
    pass


def get_setting_voltage(ModbusSerialClient: client):
    return client.read_holding_registers(address=int ("0040",16), count=2, slave=1)
    pass
def get_setting_current(ModbusSerialClient: client):
    return client.read_holding_registers(address=int ("0041",16), count=2, slave=1)
    pass
def get_setting_frequency(ModbusSerialClient: client):
    return client.read_holding_registers(address=int ("0043",16), count=2, slave=1)
    pass
def get_setting_state(ModbusSerialClient: client):
    return client.read_holding_registers(address=int ("0042",16), count=2, slave=1)
    pass
def get_setting_duty_cycle(ModbusSerialClient: client):
    return client.read_holding_registers(address=int ("0044",16), count=2, slave=1)
    pass

#set_voltage(client,20000)

'''
for i in range(0,20000,1000):
    set_voltage(client,i)
    time.sleep(1)
'''

output_switching_off(client)
set_current(client,1500)
i = get_setting_voltage(client)

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





#client.read_discrete_inputs(address=40, count=2, slave=2)
#client.read_exception_status()
#client.readwrite_registers()
# Чтение данных из регистров хранения (holding registers)
#client.read_coils(address=40, count=2, slave=2)
#result = client.read_holding_registers(address=2, count=5, unit=1)
#if result.isError():
    #print("Ошибка чтения данных:", result)
#else:
    #print("Прочитанные данные:", result.registers)

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
