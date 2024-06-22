from pymeasure.instruments.srs import SR830
from pymeasure.adapters import SerialAdapter
import time


class commandsSR830():
    def __init__(self, device) -> None:

        self.COMM_ID = '*IDN'

        self.COMM_TIME_CONSTANT = 'OFLT'

        self.COMM_GARMONIC = 'HARM'
        self.COMM_FREQUENCY = 'FREQ'

        self.PHASE = 'PHAS'

        self.SET_INT_FREQUENCY_SOURCE = 'FMOD'

        self.STR_SET_SIN_OUT = "SLVL{}\r\n"

        self.COMM_AUTO_GAIN = 'AGAN'
        self.COMM_AUTO_APHS = 'APHS'

        self.COMM_DISPLAY = 'OUTR'  # запрос значения с дисплея

        self.COMM_SERIAL_PULL_STATUS_BYTE = '*STB?\r\n'

        self.device = device
        
    def push_autogain(self):
        #print(bytes(self.COMM_AUTO_GAIN, "ascii") + b'\r\n')
        self.device.client.write(bytes(self.COMM_AUTO_GAIN, "ascii") + b'\r\n')

    def push_autophase(self):
        #print(bytes(self.COMM_AUTO_APHS, "ascii") + b'\r\n')
        self.device.client.write(bytes(self.COMM_AUTO_APHS, "ascii") + b'\r\n')

    def get_parameter(self, command, timeout, param=False):
        if param == False:
            self.device.client.write(bytes(command, "ascii") + b'?\r\n')
        else:
            param = str(param)
            self.device.client.write(bytes(command, "ascii") +
                              b'? ' + bytes(param, "ascii") + b'\r\n')
        if param != False:
                  pass
            #print("чтение параметров", bytes(command, "ascii") + b'? ' + bytes(param, "ascii") + b'\r\n')
        else:
            pass
            #print(bytes(command, "ascii") + b'?\r\n')

        start_time = time.time()
        while time.time() - start_time < timeout:
            line = self.device.client.readline().decode().strip()
            if line:
                #print("Received:", line)
                return line
        return False
# SLVL (?) {x} 5-4 Установите (запросите) амплитуду синусоидального выходного сигнала на x Vrms. 0.004 £ x £5.000.

    def _set_amplitude(self, ampl):
        try:
            ampl = float(ampl)
        except:
            return False
        if ampl < 0.004 or ampl > 5:
            return False
        #print(bytes("SLVL", "ascii") + bytes(str(ampl), "ascii") + b'\r\n')
        self.device.client.write(bytes("SLVL", "ascii") +
                          bytes(str(ampl), "ascii") + b'\r\n')
        return True

# FREQ (?) {f} 5-4 Установка (запрос) опорной частоты на f Гц. Устанавливается только в режиме внутренней ссылки.
    def _set_frequency(self, freq):
        try:
            freq = int(freq)
        except:
            return False
        if freq > 102000 or freq < 2:
            return False
        #print(bytes("FREQ", "ascii") + bytes(str(freq), "ascii") + b'\r\n')
        self.device.client.write(bytes("FREQ", "ascii") +
                          bytes(str(freq), "ascii") + b'\r\n')
        return True


# FMOD (?) {i} 5-4 Установка (запрос) источника опорного сигнала на внешний (0) или внутренний (1).

    def _set_sourse_base_signal(self, sourse="in"):
        dict_filter_slope = {0: "out",
                             1: "in"
                             }
        return self._set_something(dict_filter_slope, 'FMOD', sourse)


# OFLT (?) {i} 5-6 Установка (запрос) постоянной времени от 10 мкс (0) до 30 кс (19).


    def _set_time_const(self, time_constant):
        dict_time_code = {0: 10/1000000,
                          1: 30/1000000,
                          2: 100/1000000,
                          3: 300/1000000,
                          4: 1/1000,
                          5: 3/1000,
                          6: 10/1000,
                          7: 30/1000,
                          8: 100/1000,
                          9: 300/1000,
                          10: 1,
                          11: 3,
                          12: 10,
                          13: 30,
                          14: 100,
                          15: 300,
                          16: 1000,
                          17: 3000,
                          18: 10000,
                          19: 30000
                          }
        return self._set_something(dict_time_code, 'OFLT', time_constant)
    # ---------------------------------
    # SENS (?) {i} 5-6 Установка (запрос) чувствительности в диапазоне от 2 нВ (0) до 1 В (26) среднеквадратичных значений полной шкалы.
    """
			i=0(≙2 nV/fA), i=1(≙5 nV/fA), i=2(≙10 nV/fA), i=3(≙20 nV/fA), i=4(≙50 nV/fA), i=5(≙100 nV/fA), i=6(≙200 nV/fA), 
			i=7(≙500 nV/fA), i=8(≙1 μV/pA), i=9(≙2 μV/pA), i=10(≙5 μV/pA), i=11(≙10 μV/pA), i=12(≙20 μV/pA), i=13(≙50 μV/pA),
			i=14(≙100 μV/pA), i=15(≙200 μV/pA), i=16(≙500 μV/pA), i=17(≙1 mV/nA), i=18(≙2 mV/nA), i=19(≙5 mV/nA), i=20(≙10 mV/nA),
			i=21(≙20 mV/nA), i=22(≙50 mV/nA), i=23(≙100 mV/nA), i=24(≙200 mV/nA), i=25(≙500 mV/nA), i=26(≙1 V/μA)
	"""

    def _set_sens(self, sens=2/1000000000):
        dict_sens_code = {
            0: 2/1000000000,
            1: 5/1000000000,
            2: 10/1000000000,
            3: 20/1000000000,
            4: 50/1000000000,
            5: 100/1000000000,
            6: 200/1000000000,
            7: 500/1000000000,
            8: 1/1000000,
            9: 2/1000000,
            10: 5/1000000,
            11: 10/1000000,
            12: 20/1000000,
            13: 50/1000000,
            14: 100/1000000,
            15: 200/1000000,
            16: 500/1000000,
            17: 1/1000,
            18: 2/1000,
            19: 5/1000,
            20: 10/1000,
            21: 20/1000,
            22: 50/1000,
            23: 100/1000,
            24: 200/1000,
            25: 500/1000,
            26: 1,
        }
        return self._set_something(dict_sens_code, 'SENS', sens)
    # ---------------------------------
    # OFSL (?) {i} 5-6 Установите (запрос) крутизну фильтра нижних частот на 6 (0), 12 (1), 18 (2) или 24 (3) дБ/окт.

    def _set_filter_slope(self, slope):
        dict_filter_slope = {0: 6,
                             1: 12,
                             2: 18,
                             3: 24
                             }
        return self._set_something(dict_filter_slope, 'OFSL', slope)

    # RMOD (?) {i} 5-6 Установите (запросите) режим динамического резерва на HighReserve (0), Normal (1) или Low Noise (2).
    def _set_reserve(self, reserve="high reserve"):
        dict_reserve = {0: "high reserve",
                        1: "normal",
                        2: "low noise",
                        }
        return self._set_something(dict_reserve, 'RMOD', reserve)

    # ISRC (?) {i} 5-5 Установите (запросите) конфигурацию входа на A (0), A-B (1) , I (1 МВт) (2) или I (100 МВт) (3).
    def _set_input_conf(self, conf="A"):
        dict_input_conf = {0: "A",
                           1: "A - B",
                           2: "I (10^6)",
                           3: "I (10^8)"
                           }
        return self._set_something(dict_input_conf, 'ISRC', conf)

    # ICPL (?) {i} 5-5 Установка (запрос) входной связи на переменный (0) или постоянный (1) ток.
    def _set_input_type_conf(self, type_conf="AC"):
        dict_input_type_conf = {0: "AC",
                                1: "DC",
                                }
        return self._set_something(dict_input_type_conf, 'ICPL', type_conf)

    # IGND (?) {i} 5-5 Установите (запрос) для заземления входного экрана значение Float (0) или Ground (1).
    def _set_input_type_connect(self, input_ground="float"):
        dict_input_type_conn = {0: "float",
                                1: "ground",
                                }
        return self._set_something(dict_input_type_conn, 'IGND', input_ground)

    # ILIN (?) {i} 5-5 Установите (запрос) для фильтров линейных засечек значения Out (0), Line In (1) , 2xLine In (2) или Both In (3).
    def _set_line_filters(self, type="out"):
        dict_line = {0: "out",
                     1: "line",
                     2: "2X line",
                     3: "both"
                     }
        return self._set_something(dict_line, 'ILIN', type)

    def _set_something(self, dict_some, command, value):
        code = False
        for val, key in zip(dict_some.values(), dict_some.keys()):
            if val == value:
                code = key
                break
        if code is not False:
            #print(bytes(command, "ascii") + bytes(str(code), "ascii") + b'\r\n')
            self.device.client.write(bytes(command, "ascii") +
                              bytes(str(code), "ascii") + b'\r\n')
            return True
        return False

    def _set_phase(self, x):
        if x < -360 or x > 730:
            return False
        self.device.client.write(b'PHAS' + str(x) + b'\r\n')
        b'PHAS' + str(x) + b'\r\n'  # -360.00 ≤ x ≤ 729.99
        return True

    def _set_reference_sourse(self, x):
        if x == "ext":
            self.device.client.write(b'FMOD 0\r\n')
        else:
            self.device.client.write(b'FMOD 1\r\n')


if __name__ == "__main__":
    sr = commandsSR830(125)
    #print(100 * 0.000001)
    sr._set_sens(10/1000000)

'''
		device = SR830(SerialAdapter("COM10"))
		device.auto_phase()
		print(device.ask("open 1"))
		print("stop")
'''
'''
	b'FMOD \r\n'
	b'FREQ \r\n'
	b'RSLP \r\n'
	b'HARM \r\n'
	b'SLVL \r\n'
	b'ISRC \r\n'
	b'IGND \r\n'
	b'ICPL \r\n'
	b'ILIN \r\n'
	b'SENS \r\n'
	b'RMOD \r\n'
	b'OFLT \r\n'
	b'OFSL \r\n'
	b'SYNC \r\n'
	b'DDEF \r\n'
	b'Aux \r\n' 
	b'FPOP \r\n'
	b'OEXP \r\n'
	b'OAUX \r\n'
	b'UXV \r\n'
	b'OUTX \r\n'
	b'OVRM \r\n'
	b'KCLK \r\n'
	b'ALRM \r\n'
	b'SSET \r\n'
	b'RSET \r\n'
	b'AGAN \r\n'
	b'ARSV \r\n'
	b'APHS \r\n'
	b'AOFF \r\n'
	b'SRAT \r\n'
	b'SEND \r\n'
	b'TRIG \r\n'
	b'TSTR \r\n'
	b'STRT \r\n'
	b'PAUS \r\n'
	b'REST \r\n'
	b'OUTP? \r\n'
	b'OUTR? \r\n'
	b'SNAP? \r\n'
	b'OAUX? \r\n'
	b'SPTS? \r\n'
	b'TRCA? \r\n'
	b'TRCB? \r\n'
	b'TRCL? \r\n'
	b'FAST \r\n'
	b'STRD \r\n'
	b'*RST \r\n'
	b'*IDN? \r\n'
	b'LOCL  \r\n'
	b'OVRM  \r\n'
	b'TRIG \r\n'
	b'*CLS \r\n'
	b'*ESE  \r\n'
	b'*ESE  \r\n'
	b'*ESR?  \r\n'
	b'*SRE  \r\n'
	b'*STB?  \r\n'
	b'*PSC  \r\n'
	b'*ERRE  \r\n'
	b'*ERRS?  \r\n'
	b'*LIAE  \r\n'
	b'*LIAS?  \r\n'

	OFLT (?) {i} 5-6 Установка (запрос) постоянной времени от 10 мкс (0) до 30 кс (19).

	COMMAND LIST
	VARIABLES i,j,k,l,m Integers
	f Frequency (real)
	x,y,z Real Numbers
	s String
	REFERENCE and PHASE page description
	PHAS (?) {x} 5-4 Установите (запросите) фазовый сдвиг на x градусов.
	FMOD (?) {i} 5-4 Установка (запрос) источника опорного сигнала на внешний (0) или внутренний (1).
	FREQ (?) {f} 5-4 Установка (запрос) опорной частоты на f Гц. Устанавливается только в режиме внутренней ссылки.
	RSLP (?) {i} 5-4 Установите (запросите) наклон внешнего опорного сигнала на синус (0), TTL нарастание (1) или TTL спад (2).
	HARM (?) {i} 5-4 Установите (запросите) гармонику обнаружения на 1 £ i £ 19999 и i-f £ 102 кГц.
	SLVL (?) {x} 5-4 Установите (запросите) амплитуду синусоидального выходного сигнала на x Vrms. 0.004 £ x £5.000.

	INPUT and FILTER page description
	ISRC (?) {i} 5-5 Установите (запросите) конфигурацию входа на A (0), A-B (1) , I (1 МВт) (2) или I (100 МВт) (3).
	IGND (?) {i} 5-5 Установите (запрос) для заземления входного экрана значение Float (0) или Ground (1).
	ICPL (?) {i} 5-5 Установка (запрос) входной связи на переменный (0) или постоянный (1) ток.
	ILIN (?) {i} 5-5 Установите (запрос) для фильтров линейных засечек значения Out (0), Line In (1) , 2xLine In (2) или Both In (3).
	Описание страницы GAIN и TIME CONSTANT
	SENS (?) {i} 5-6 Установка (запрос) чувствительности в диапазоне от 2 нВ (0) до 1 В (26) среднеквадратичных значений полной шкалы.
	RMOD (?) {i} 5-6 Установите (запросите) режим динамического резерва на HighReserve (0), Normal (1) или Low Noise (2).
	OFLT (?) {i} 5-6 Установка (запрос) постоянной времени от 10 мкс (0) до 30 кс (19).
	OFSL (?) {i} 5-6 Установите (запрос) крутизну фильтра нижних частот на 6 (0), 12 (1), 18 (2) или 24 (3) дБ/окт.
	SYNC (?) {i} 5-7 Установите (запрос) для синхронного фильтра значение "Выкл." (0) или "Вкл." ниже 200 Гц (1).
	DISPLAY and OUTPUT page description
	DDEF (?) i {, j, k} 5-8 Установите (запросите) для дисплея CH1 или CH2 (i=1,2) значения XY, Rq, XnYn, Aux 1,3 или Aux 2,4 (j=0..4)
	и соотношение дисплея к None, Aux1,3 или Aux 2,4 (k=0,1,2).
	FPOP (?) i {, j} 5-8 Установка (запрос) источника выхода CH1 (i=1) или CH2 (i=2) на X или Y (j=1) или дисплей (j=0).
	OEXP (?) i {, x, j} 5-8 Установка (запрос) смещения X, Y, R (i=1,2,3) на x процентов ( -105.00 £ x £ 105.00)
	и расширить до 1, 10 или 100 (j=0,1,2).
	AOFF i 5-8 Автоматическое смещение X, Y, R (i=1,2,3).
	AUX INPUT/OUTPUT page description
	OAUX ? i 5-9 Запрос значения входа Aux i (1,2,3,4).
	AUXV (?) i {, x} 5-9 Установка (запрос) напряжения на входе Aux Output i (1,2,3,4) на x Вольт. -10.500 £ x £ 10.500.
	Описание страницы SETUP
	OUTX (?) {i} 5-10 Установка (запрос) интерфейса выхода на RS232 (0) или GPIB (1).
	OVRM (?) {i} 5-10 Установите (запрос) состояние дистанционного управления овердрайвом GPIB на Off (0) или On (1).
	KCLK (?) {i} 5-10 Установка (запрос) состояния щелчка клавиш в положение Off (0) или On (1).
	ALRM (?) {i} 5-10 Установите (запрос) для сигналов тревоги значение Выкл (0) или Вкл (1).
	SSET i 5-10 Сохранить текущую настройку в буфере настроек i (1£i£9).
	RSET i 5-10 Вызов текущей настройки из буфера настроек i (1£i£9).
	AUTO FUNCTIONS page description
	AGAN 5-11 Функция автоматического усиления. Аналогично нажатию кнопки [AUTO GAIN].
	ARSV 5-11 Функция автоматического резерва. Аналогично нажатию клавиши [AUTO RESERVE].
	APHS 5-11 Функция автоматической фазы. Аналогично нажатию клавиши [AUTO PHASE].
	AOFF i 5-11 Автосмещение X,Y или R (i=1,2,3).
	DATA STORAGE page description
	SRAT (?) {i} 5-13 Установите (запрос) частоту дискретизации данных от 62,5 мГц (0) до 512 Гц (13) или триггер (14).
	SEND (?) {i} 5-13 Установка (запрос) режима сканирования данных на 1 кадр (0) или цикл (1).
	TRIG 5-13 Команда программного триггера. То же, что и вход триггера.
	TSTR (?) {i} 5-13 Установка (запрос) режима сканирования триггера на Нет (0) или Да (1).
	STRT 5-13 Начать или продолжить сканирование.
	PAUS 5-13 Приостановка сканирования. Не сбрасывает приостановленное или завершенное сканирование.
	REST 5-14 Сброс сканирования. Все сохраненные данные теряются.
	DATA TRANSFER page description
	OUTP? i 5-15 Запрос значения X (1), Y (2), R (3) или q (4). Возвращает значение ASCII с плавающей точкой.
	OUTR? i 5-15 Запрос значения дисплея i (1,2). Возвращает значение с плавающей точкой ASCII.
	SNAP?i,j{,k,l,m,n} 5-15 Запрос значения от 2 до 6 параметров одновременно.
	OAUX? i 5-16 Запрос значения входа Aux Input i (1,2,3,4). Возвращает значение ASCII с плавающей точкой.
	SPTS? 5-16 Запрос количества точек, хранящихся в буфере дисплея.
	TRCA? i,j,k 5-16 Считывание k³1 точек, начиная с бина j³0, из буфера дисплея i (1,2) в формате ASCII с плавающей точкой.
	TRCB? i,j,k 5-16 Чтение k³1 точки, начиная с бина j³0, из буфера Display i (1,2) в двоичном формате IEEE с плавающей точкой.
	TRCL? i,j,k 5-17 Чтение k³1 точек, начинающихся в бине j³0, из буфера дисплея i (1,2) в ненормированном двоичном формате с плавающей запятой.
	FAST (?) {i} 5-17 Установка (запрос) режима быстрой передачи данных Вкл (1 или 2) или Выкл (0). Вкл будет передавать двоичные X и Y каждый образец во время сканирования через интерфейс GPIB.
	STRD 5-18 Запуск сканирования после задержки 0,5 с. Используется с режимом быстрой передачи данных.
	INTERFACE page description
	kRST 5-19 Сброс настроек устройства к конфигурациям по умолчанию.
	kIDN? 5-19 Чтение строки идентификации устройства SR830.
	LOCL(?) {i} 5-19 Установка (запрос) состояния "Местный/дистанционный" в LOCAL (0), REMOTE (1) или LOCAL LOCKOUT (2).
	OVRM (?) {i} 5-19 Установка (запрос) состояния GPIB Overide Remote в Off (0) или On (1).
	TRIG 5-19 Команда программного триггера. То же, что и вход триггера.
	STATUS page description
	kCLS 5-20 Очистить все байты состояния.
	kESE (?) {i} {,j} 5-20 Установить (запросить) в регистре Standard Event Status Byte Enable Register десятичное значение i (0-255).
	kESE i,j устанавливает бит i (0-7) в j (0 или 1). kESE? запрашивает весь байт. kESE?i запрашивает только бит i.
	kESR? {i} 5-20 Запрос байта состояния стандартного события. Если i включено, запрашивается только бит i.
	kSRE (?) {i} {,j} 5-20 Установка (запрос) регистра разрешения последовательного опроса в десятичное значение i (0-255). kSRE i,j устанавливает бит i (0-...
	7) в j (0 или 1). kSRE? запрашивает байт, kSRE?i запрашивает только бит i.
	kSTB? {i} 5-20 Запрос байта состояния последовательного опроса. Если включен i, запрашивается только бит i.
	kPSC (?) {i} 5-20 Установка (запрос) бита Power On Status Clear в состояние Set (1) или Clear (0).
	ERRE (?) {i} {,j} 5-20 Установка (запрос) регистра разрешения статуса ошибки в десятичное значение i (0-255). ERRE i,j устанавливает бит i
	(0-7) в j (0 или 1). ERRE? запрашивает байт, ERRE?i запрашивает только бит i.
	ERRS? {i} 5-20 Запрос байта состояния ошибки. Если i включено, запрашивается только бит i.
	LIAE (?) {i} {,j} 5-20 Установка (запрос) регистра разрешения состояния LIA в десятичное значение i (0-255). LIAE i,j устанавливает
	бит i (0-7) в j (0 или 1). LIAE? запрашивает весь байт, LIAE?i запрашивает только бит i.
	LIAS? {i} 5-20 Запрос байта состояния LIA. Если включен i, запрашивается только бит i.

	SERIAL POLL STATUS BYTE (5-21)
	0 SCN Данные не получены
	1 IFC Выполнение команды не ведется
	2 ERR Установлен не маскируемый бит в байте состояния ошибки
	3 LIA Несмаскированный бит в наборе байтов состояния LIA
	4 MAV Выходной буфер интерфейса не пуст
	5 ESB Несмаскированный бит в байте стандартного состояния
	6 SRQ Произошел SRQ (запрос на обслуживание)
	7 Неиспользуемый

	STANDARD EVENT STATUS BYTE (5-22)
	0 INP Устанавливается при переполнении очереди входов
	1 Не используется
	2 QRY Устанавливается при переполнении выходной очереди
	3 Не используется
	4 EXE Устанавливается при возникновении ошибки выполнения команды
	5 CMD Устанавливается при получении недопустимой команды
	6 URQ Устанавливается при нажатии любой клавиши или повороте ручки
	7 PON Устанавливается при включении питания
	БАЙТ СОСТОЯНИЯ LIA (5-23)
	0 RSRV/INPT Устанавливается при перегрузке RESERVE или INPUT
	1 FILTR Устанавливается при перегрузке FILTR
	2 OUTPT Устанавливается при перегрузке OUTPT
	3 UNLK Устанавливается при разблокировке эталона
	4 RANGE Устанавливается, когда частота детектирования пересекает 200 Гц
	5 TC Устанавливается при изменении постоянной времени
	6 TRIG Устанавливается при срабатывании устройства
	7 Неиспользуемый
	БАЙТ СОСТОЯНИЯ ОШИБКИ (5-23)
	0 Не используется
	1 Ошибка резервного копирования Устанавливается при сбое резервного копирования батареи
	2 RAM Error Устанавливается, когда тест памяти RAM обнаруживает ошибку
	3 Не используется
	4 ROM Error Устанавливается, когда тест памяти ROM обнаруживает ошибку
	5 GPIB Error Устанавливается при прерывании передачи двоичных данных по GPIB
	6 DSP Error Устанавливается, когда тест DSP обнаруживает ошибку
	7 Math Error Устанавливается при возникновении внутренней математической ошибки
'''
