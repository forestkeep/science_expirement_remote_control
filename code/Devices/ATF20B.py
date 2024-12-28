# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

import logging
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Devices.Classes import (base_ch, base_device, ch_response_to_step,
                             not_ready_style_border, ready_style_border,
                             which_part_in_ch)
from Devices.freq_gen_class import FreqGen, chActFreqGen, chMeasFreqGen
from Devices.interfase.set_power_supply_window import Ui_Set_power_supply

logger = logging.getLogger(__name__)


class ATF20B(FreqGen):
    def __init__(self, name, installation_class) -> None:

        super().__init__(name, "modbus", installation_class)
        self.ch1_act = chActFreqGen(
            number = 1,
            device_class = self,
            max_ampl = 3,
            max_freq = 1000000,
            min_step_A=0.001,
            min_step_F=0.001,
        )
        self.ch1_meas = chMeasFreqGen(1, self)
        self.channels = self.create_channel_array()


    def set_remote_control(self, adr_dev):
        self.client.write(f"{adr_dev}RS232\r\n")

    def set_local_control(self, adr_dev):
        self.client.write(f"{adr_dev}LOCAL\r\n")

    def set_freq(self, channel, frequency):
        status = True
        if isinstance(channel, str):
            channel = channel.upper()
            if channel != "A" and channel != "B":
                status = False
        else:
            status = False

        if isinstance(frequency, float) or isinstance(frequency, int):
            if frequency < 0 or frequency > 10e6:
                status = False
            else:
                # вычислить юниты в зависимости от частоты
                unit = "MHz"
        else:
            status = False

        if status:
            self.client.write(f"CH{channel}:AFREQ:{frequency}:{unit}\r\n")

if __name__ == "__main__":
    import serial
    re = "rrererere"
    print(type(re))
    client = serial.Serial("COM5", 19200, timeout=1)
    dev = ATF20B(client)

    dev.set_remote_control()
    time.sleep(3)
    dev.set_freq("A", 1)


"CHA:AFREQ:1.31:MHz"


"""Code Waveform name Code Waveform name Code Waveform name Code Waveform name
00 Sine 08 Up stair 16 Exponent 24 Down stair
01 Square 09 Pos-DC 17 Logarithm 25 Po-bipulse
02 Triangle 10 Neg-DC 18 Half round 26 Ne-bipulse
03 Up ramp 11 All sine 19 Tangent 27 Trapezia
04 Down ramp 12 Half sine 20 Sin (x)/x 28 Cosine
05 Pos-pulse 13 Limit sine 21 Noise 29 Bidir-SCR
06 Neg-pulse 14 Gate sine 22 Duty 10% 30 Cardiogram
07 Tri-pulse 15 Squar-root 23 Duty 90% 31 Earthquake"""


"""
Таблица значений строки функции
Опция Строка
Частота сигнала в канале А CHA
Частота сигнала в канале В CHB
Свипирование частоты в канале А FSWP
Свипирование частоты в канале В ASWP
Частотная модуляция в канале А FM
Измерение частоты внешнего сигнала COUNT
Выход из режима дистанционного управления LOCAL
Система SYS
Пакетная генерация в канале А ABURST
Пакетная генерация в канале В BBURST
Частотная манипуляция в канале А FSK
Амплитудная манипуляция в канале А ASK
Фазовая манипуляция в канале А PSK
Логический сигнал ТТЛ TTL
Управление по интерфейсу RS232 RS232 

Таблица значений строки опции
Опция Строка Опция Строка
Форма сигнала (каналА) AWAVE Форма модулирующего сигнала MWAVE
Смещение (канал А) AOFFS Частота модулирующего сигнала MODUF
Частота (канал А) AFREQ Размах VPP
Ослабление (канал А) AATTE Звуковой сигнал BEEP
Период (канал А) APERD Временной интервал INTVL
Коэффициент заполнения (канал А) ADUTY Адрес интерфейса ADDR
Частота (канал В) BFREQ Режим свипирования MODEL
Гармоническая волна(канал В) BHARM Начальная амплитуда STARA
Период (канал В) BPERD Начальная частота STARF
Коэффициент заполнения (канал В) BDUTY Скачок амплитуды HOPA
Частота (TTL_A) TTLAF Скачок частоты HOPF
Коэффициент заполнения (TTL_A) TTLAD Скачок фазы HOPP
Частота (TTL_B) TTLBF Внешний запуск EXTTR
Коэффициент заполнения (TTL_B) TTLBD Внешняя модуляция EXT
Пусковой сигнал (TTL_A) TTLTR Сброс настроекmсистемы RESET
Шаг амплитуды STEPA Фаза PHASE
Шаг частоты STEPF Истинное среднеквадратичное значение (True RMS) VRMS
Форма BWAVE Установка языка LANG
Вызов параметра изпамяти RECAL Несущая амплитуда CARRA
Измерение частоты MEASF Несущая частота CARRF
Версия программы VER Время стробирования STROBE
Число циклов в пакете NCYCL Конечная амплитуда STOPA
Частота следованияпакетов BURSF Конечная частота STOPF
Одиночный пусковой сигнал TRIGG Автоматическое свипирование AUTO
Одиночный пакет ONCES Сохранение параметра STORE
Девиация частоты при частотной модуляции DEVIA Переключение выходного канала SWITCH

Таблица значений единиц измерения
Величина Строка Величина Строка
Частота MHz, kHz, Hz, mHz, uHz
Фаза DEG
Размах Vpp, mVpp 
Ослабление dB
Время s, ms, us, ns 
Порядковый номер No.
Гармоника TIME Процентное отношение %
Число циклов CYCL 
Смещение по напряжению Vdc, mVdc
Среднеквадратичное значение Vrms, mVrms

4.3.5. Строка данных
Максимальная длина строки данных составляет 10 символов. 



ПРИМЕР 1:
Канал А, генерация в одном канале, синусоидальный сигнал,
частота 1 МГц,
режим RS232: 88CHA:AWAVE:0:No.
 88CHA:AFREQ:1:MHz
ПРИМЕР 2:
Канал В, генерация в одном канале, пилообразный сигнал, частота 1 кГц,
режим RS232: 88CHB:BWAVE:2:No.
 88CHB:BTRIG:1:kHz
ПРИМЕР 3:
Канал А, генерация в одном канале, импульсный сигнал, коэффициент заполнения 25%,
режим RS232: 88CHA:ADUTY:25:%
ПРИМЕР 4:
Сигнал со свипированием частоты, начальная частота 1 кГц,
режим RS232: 88FSWP:STARF:1:kHz
ПРИМЕР 5:
Сигнал с частотной манипуляцией, несущая частота 25 кГц,
режим RS232: 88FSK:CARRF:25:kHz
ПРИМЕР 6:
Запрос значения частоты сигнала в канале А
режим RS232: 88CHA:?AFREQ
ПРИМЕР 7:
Возвращение в ручной режим управления и восстановление
функций кнопок управления
режим RS232: 88LOCAL


4.3.8. Интерактивная работа с прибором
В начале отправьте команды выбора интерфейса. Например,
отправьте команду «адрес + RS232» для выбора интерфейса
RS232. Прибор переключится в режим дистанционного управления через интерфейс RS232. Если адрес прибора – 88, то отправьте «88 RS232». Для выхода из режима дистанционного
управления отправьте команду «88LOCAL» или нажмите кнопку
[SYS] для возвращения прибора в обычный режим управления
кнопками с передней панели. В противном случае невозможно
будет использовать ни кнопки управления, ни дистанционное
управление. 
"""
