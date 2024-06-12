import pyvisa


class CommandsMNIPI:
    def __init__(self) -> None:
        self.PUSH_MENU = 1
        self.PUSH_RIGHT = b''
        self.PUSH_Z = b''
        self.PUSH_R = b''
        self.PUSH_DOWN = b''
        self.PUSH_ENTER = b''
        self.PUSH_UP = b''
        self.PUSH_L = b''
        self.PUSH_CALL = b''
        self.PUSH_LEFT = b''
        self.PUSH_I = b''
        self.PUSH_C = b''
        self.CHANGE_SHIFT=b''
        self.CHANGE_FREQ=  ''
        self.CHANGE_LEVEL=b''
        self.CHANGE_RANGE = b''  # = 
# Инициализация библиотеки PyVISA
rm = pyvisa.ResourceManager()
lib = rm.visalib


# Получение списка всех доступных ресурсов
resources = rm.list_resources()

# Вывод найденных ресурсов
print("Найденные ресурсы:")
for resource in resources:
    print(resource)

asdd = CommandsMNIPI()

instrument = rm.open_resource("ASRL8::INSTR")
#print(instrument.open())
print(instrument.last_status)
instrument.baud_rate = 9600
#instrument.write_binary_values('', values = [1])
#instrument.write("qwqwqwqwqwqwq")
instrument.read()
instrument.close()
print(instrument)
# Перебор ресурсов для запроса *IDN? и версии прошивки
for resource in resources:
    try:
        # Создание соединения с каждым ресурсом
        instrument = rm.open_resource(resource)

        # Запрос *IDN?
        idn_response = instrument.query('*IDN?')
        print(f"{resource} *IDN?: {idn_response.strip()}")

        # Запрос версии прошивки (предполагается, что устройство предоставляет эту информацию)
        firmware_version = instrument.query('FIRMWARE_VERSION?')
        print(f"{resource} Версия прошивки: {firmware_version.strip()}")

        # Закрытие соединения с ресурсом
        instrument.close()
    except pyvisa.errors.VisaIOError as e:
        # Обработка исключения, если что-то пошло не так при запросе
        print(f"Ошибка при запросе к {resource}: {str(e)}")
