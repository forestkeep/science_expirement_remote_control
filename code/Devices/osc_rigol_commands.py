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
import random
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pyvisa

logger = logging.getLogger(__name__)

class oscRigolCommands:
    def __init__(self, device) -> None:
        self.device = device
        self.channels_number = 4

    def get_all_data_sourse(self, max_points_on_screen) -> list:
        new_data = []
        state = True
        balance = max_points_on_screen
        step_point = 120000
        if step_point > balance:
            step_point = balance
        start = 1
        end = step_point
        while balance > 0:

            status, data = self.get_data(start, end)
            if status:
                for data in data:
                    new_data.append(data)
            else:
                state = False

            balance -= step_point
            start = end + 1
            if step_point > balance:
                step_point = balance
            end += step_point

        new_data = np.asarray(new_data)
        return state, new_data

    def check_parameters(self, command, focus_answer) -> bool:  #
        ans = self.device.client.query(command)

        if isinstance(
            focus_answer, (int, float)
        ):  # если число, то и ответ нужно преобразовать в число
            ans = float(ans)

        if ans == focus_answer:

            return True
        else:
            return False

    def calc_integral(self, arr, step):
        return np.sum((arr[:-1] + arr[1:]) * step / 2)

    def format_scientific(self, number):
        return f"{number:.6e}"

    def get_raw_wave_data(
        self, channels_number: list, is_debug: bool = False, timeout=3
    ) -> dict:
        """
            поочередно считываем данные на переданных каналах
        возвращаем статус + словарь, где ключи - это номера каналов, а значения списки данных
        """
        if not is_debug:
            status = True
            self.set_wave_form_mode(mode="RAW")
            self.set_wave_format(format="ASC")
            points = self.calculate_num_points()
            result = {}

            for num_ch in channels_number:
                self.set_wave_sourse(num_ch)
                status_local, arr = self.get_all_data_sourse(points)
                if status_local:
                    result[num_ch] = arr
                else:
                    status = False
                    print("неудачное считывание")
        else:
            status = True
            result = {}
            for num_ch in channels_number:
                frequency = np.random.uniform(
                    0.5, 5.0
                )  # Частота в диапазоне от 0.5 до 5.0
                x = np.linspace(0, 2 * np.pi, 3000)
                sine_wave = np.round(
                    np.sin(frequency * x), 2
                )  # Округляем до 2 знаков после запятой
                arr = sine_wave
                result[num_ch] = arr

        return status, result

    def calculate_num_points(self):
        scale = self.get_scale()

        sample_rate = self.get_sample_rate()

        max_points_on_screen = (
            sample_rate[0] * scale * 12
        )  # 12 - это чсло клеток по горизонтальной оси

        return max_points_on_screen

    def calculate_step_time(self) -> float:
        """return step beetwen points"""
        sample_rate = self.get_sample_rate()
        return 1 / sample_rate[0]
    
    def get_data(self, start_point, end_point):
        new_data = []

        self.set_start_point(start_point)
        self.set_end_point(end_point)
        self.device.client.write(f":WAV:DATA?\r\n")
        status = True
        try:
            data = self.device.client.read_raw()
            data = str(data)
            data = data.split(",")
            for i in range(1, len(data) - 1, 1):
                new_data.append(round(float(data[i]), 2))
        except pyvisa.errors.VisaIOError:
            status = False

        return status, new_data

    def set_start_point(self, point):
        self.device.client.write(f":WAV:STARt {point}\r\n")

    def set_end_point(self, point):
        self.device.client.write(f":WAV:STOP {point}\r\n")

    def get_sample_rate(self):
        sample_rate = self.device.client.query_ascii_values(f"ACQ:SRATe?\r\n")
        return sample_rate

    def set_band_width(self, number_ch: int, is_enable: bool) -> bool:  #
        if number_ch < 1 or number_ch > self.channels_number:
            return False
        if is_enable:
            self.device.client.write(f":CHANnel{number_ch}:BWLimit 20M\r\n")
            is_ok = self.check_parameters(
                command=f":CHANnel{number_ch}:BWLimit?\r\n", focus_answer="20M\n"
            )
        else:
            self.device.client.write(f":CHANnel{number_ch}:BWLimit OFF\r\n")
            is_ok = self.check_parameters(
                command=f":CHANnel{number_ch}:BWLimit?\r\n", focus_answer="OFF\n"
            )
        return is_ok

    def set_coupling(self, number_ch: int, coupling="DC") -> bool:  #
        if number_ch < 1 or number_ch > self.channels_number:
            return False
        self.device.client.write(f":CHANnel{number_ch}:COUPling {coupling}\r\n")
        is_ok = self.check_parameters(
            command=f":CHANnel{number_ch}:COUPling?\r\n", focus_answer=f"{coupling}\n"
        )
        return is_ok

    def set_trigger_mode(self, mode) -> bool:  #
        self.device.client.write(f":TRIGger:MODE {mode}\r\n")
        is_ok = self.check_parameters(
            command=f":TRIGger:MODE?\r\n", focus_answer=f"{mode}\n"
        )
        return is_ok

    def set_trigger_edge_slope(self, slope) -> bool:  #
        if slope == "POSitive":
            slope = "POS"
        elif slope == "NEGative":
            slope = "NEG"
        elif slope == "RFALl":
            slope = "RFAL"
        self.device.client.write(f":TRIGger:EDGe:SLOPe {slope}\r\n")
        is_ok = self.check_parameters(
            command=f":TRIGger:EDGe:SLOPe?\r\n", focus_answer=f"{slope}\n"
        )
        return is_ok

    def set_trigger_sweep(self, sweep) -> bool:  #
        if sweep == "NORMal":
            sweep = "NORM"
        elif sweep == "SINGle":
            sweep = "SING"
        self.device.client.write(f":TRIGger:SWEep {sweep}\r\n")
        is_ok = self.check_parameters(
            command=f":TRIGger:SWEep?\r\n", focus_answer=f"{sweep}\n"
        )
        return is_ok

    def set_trigger_sourse(self, number_ch) -> bool:  #
        try:
            number_ch = int(number_ch)
        except:
            return False
        if number_ch < 1 or number_ch > self.channels_number:
            return False
        self.device.client.write(f":TRIGger:EDGe:SOURce CHANnel{number_ch}\r\n")
        is_ok = self.check_parameters(
            command=f":TRIGger:EDGe:SOURce?\r\n", focus_answer=f"CHAN{number_ch}\n"
        )
        return is_ok

    def set_trigger_edge_level(self, level) -> bool:  #
        try:
            level = float(level)
        except:
            return False
        self.device.client.write(f":TRIGger:EDGe:LEVel {level}\r\n")
        is_ok = self.check_parameters(
            command=f":TRIGger:EDGe:LEVel?\r\n",
            focus_answer=self.format_scientific(level) + "\n",
        )
        return is_ok

    def get_meas_parameter(
        self, parameter: str, channels: list, is_debug: bool = False
    ) -> list:
        result = []
        parameters = [
            "VMAX",
            "VMIN",
            "VPP",
            "VTOP",
            "VBASE",
            "VAMP",
            "VAVG",
            "VRMS",
            "OVERshoot",
            "MAREA",
            "MPAREA",
            "PREShoot",
            "PERIOD",
            "FREQUENCY",
            "RTIME",
            "FTIME",
            "PWIDth",
            "NWIDth",
            "PDUTy",
            "NDUTy",
            "TVMAX",
            "TVMIN",
            "PSLEWrate",
            "NSLEWrate",
            "VUPPER",
            "VMID",
            "VLOWER",
            "VARIance",
            "PVRMS",
            "PPULses",
            "NPULses",
            "PEDGes",
            "NEDGes",
        ]
        if parameter in parameters:
            for ch in channels:
                if not is_debug:
                    data = self.device.client.query(
                        f":MEASure:ITEM? {parameter},CHANnel{ch}"
                    )
                else:
                    data = round(random.uniform(0, 100), 2)
                try:
                    data = float(data)
                except:
                    data = "fail"
                result.append(data)
        else:
            for ch in channels:
                result.append("fail")
        return result

    def set_scale(self, scale):  #
        try:
            scale = float(scale)
        except:
            return False

        self.device.client.write(f"TIM:MAIN:SCALe {scale}\r\n")
        is_ok = self.check_parameters(
            command=f"TIM:MAIN:SCALe?\r\n", focus_answer=f"{scale:.7e}" + "\n"
        )
        return is_ok

    def get_scale(self):  #
        scale = self.device.client.query_ascii_values(f"TIM:MAIN:SCALe?\r\n")
        return scale[0]

    def set_wave_sourse(self, number_ch) -> bool:  #
        if number_ch < 1 or number_ch > self.channels_number:
            return False
        self.device.client.write(f":WAV:SOUR CHANnel{number_ch}\r\n")  ##set wave sourse
        is_ok = self.check_parameters(
            command=f":WAV:SOUR?\r\n", focus_answer=f"CHAN{number_ch}\r\n"
        )
        return is_ok

    def run(self):
        self.device.client.write(f":RUN\r\n")

    def stop(self):
        self.device.client.write(f":STOP\r\n")

    def clear(self):
        self.device.client.write(f":CLE\r\n")

    def single(self):
        self.device.client.write(f":SING\r\n")

    def get_status(self) -> str:
        return self.device.client.query(f":TRIG:STAT?\r\n")

    def set_wave_form_mode(self, mode="RAW") -> bool:  #
        self.device.client.write(f":WAV:MODE {mode}\r\n")
        is_ok = self.check_parameters(
            command=f":WAV:MODE?\r\n", focus_answer=mode + "\n"
        )
        return is_ok

    def set_wave_format(self, format="ASC") -> bool:  #
        self.device.client.write(f":WAV:FORM {format}\r\n")
        is_ok = self.check_parameters(
            command=f":WAV:FORM?\r\n", focus_answer=format + "\n"
        )
        return is_ok

    def set_BW_limit(self, ch_number, bw_limit) -> bool:  #
        self.device.client.write(f":CHANnel{ch_number}:BWLimit {bw_limit}\r\n")
        is_ok = self.check_parameters(
            command=f":CHANnel{ch_number}:BWLimit?\r\n", focus_answer=bw_limit + "\n"
        )
        return is_ok

    def set_probe(self, ch_number, probe) -> bool:  #
        try:
            probe = float(probe)
        except:
            return False
        self.device.client.write(f":CHANnel{ch_number}:PROBe {probe}\r\n")
        is_ok = self.check_parameters(
            command=f":CHANnel{ch_number}:PROBe?\r\n",
            focus_answer=self.format_scientific(probe) + "\n",
        )
        return is_ok

    def set_ch_scale(self, ch_number, scale) -> bool:  #
        try:
            scale = float(scale)
        except:
            return False
        self.device.client.write(f":CHANnel{ch_number}:SCALe {scale}\r\n")
        is_ok = self.check_parameters(
            command=f":CHANnel{ch_number}:SCALe?\r\n",
            focus_answer=self.format_scientific(scale) + "\n",
        )
        return is_ok

    def set_invert(self, ch_number, invert) -> bool:  #
        if invert == "OFF":
            invert = 0
        if invert == "ON":
            invert = 0

        self.device.client.write(f":CHANnel{ch_number}:INVert {invert}\r\n")
        is_ok = self.check_parameters(
            command=f":CHANnel{ch_number}:INVert?\r\n", focus_answer=str(invert) + "\n"
        )
        return is_ok

    def set_meas_sourse(self, number_ch) -> bool:  #
        if number_ch < 1 or number_ch > self.channels_number:
            return False
        self.device.client.write(
            f":MEAS:SOUR CHANnel{number_ch}\r\n"
        )  ##set wave sourse
        is_ok = self.check_parameters(
            command=f":MEAS:SOUR?\r\n", focus_answer=f"CHAN{number_ch}\n"
        )
        return is_ok

    def on_off_channel(self, number_ch, is_enable=False):  #
        if number_ch < 1 or number_ch > self.channels_number:
            return False
        if is_enable:
            self.device.client.write(
                f":CHANnel{number_ch}:DISP {1}\r\n"
            )  ##set wave sourse
            is_ok = self.check_parameters(
                command=f":CHANnel{number_ch}:DISP?\r\n", focus_answer=f"{1}\n"
            )
        else:
            self.device.client.write(
                f":CHANnel{number_ch}:DISP {0}\r\n"
            )  ##set wave sourse
            is_ok = self.check_parameters(
                command=f":CHANnel{number_ch}:DISP?\r\n", focus_answer=f"{0}\n"
            )
        return is_ok

    def show_graph(self, arr):
        new_data = arr
        fig, ax1 = plt.subplots(figsize=(12, 8))

        cmap = plt.get_cmap("tab20")

        markers = [
            "o",
            "s",
            "^",
            "v",
            "p",
            "*",
            "+",
            "x",
            "D",
            "H",
        ]  # Выбор стилей маркеров

        y = new_data
        x = range(len(y))
        ax1.scatter(x, y, label=f" (Main)", color="green", marker=markers[0], s=10)

        ax1.set_xlabel("Index")
        ax1.set_ylabel("Main Axis")

        plt.title("rtrrtrtrtrt")
        fig.tight_layout()
        fig.legend()
        plt.grid(True)
        plt.show()

def derivative_at_each_point(x, dx):
    derivative = np.zeros_like(x)

    for i in range(1, len(x) - 1):
        derivative[i] = (x[i + 1] - x[i - 1]) / (2 * dx)

    # Вычисление производной на краях массива с использованием односторонних разностей
    derivative[0] = (x[1] - x[0]) / dx
    derivative[-1] = (x[-1] - x[-2]) / dx

    return derivative

def find_sign_change(derivative):
    sign_changes = []
    for i in range(1, len(derivative)):
        if (
            np.sign(derivative[i]) != np.sign(derivative[i - 1])
            and np.sign(derivative[i]) > 0
        ):
            sign_changes.append(i)  # Индекс точки, где происходит смена знака
    return sign_changes

def test():
    x = np.linspace(0, 6 * np.pi, 100)  # Создание массива x от 0 до 2π
    y = np.sin(x)  # Вычисление значений синуса в каждой точке

    # Вычисление производной синуса в каждой точке
    dx = x[1] - x[0]  # Рассчитываем шаг
    dy_dx = derivative_at_each_point(y, dx)

    # Находим точки, где производная меняет знак
    sign_change_indices = find_sign_change(dy_dx)

    # Печатаем точки, где производная меняет знак
    # print("Точки, в которых производная меняет знак:", x[sign_change_indices])

    # Вывод графика функции и ее производной
    plt.figure(figsize=(10, 5))

    # График функции синуса
    plt.subplot(1, 2, 1)
    plt.plot(x, y, label="sin(x)", color="blue")
    plt.title("Функция синуса")
    plt.xlabel("x")
    plt.ylabel("sin(x)")
    plt.grid()
    plt.axhline(0, color="black", lw=0.5, ls="--")
    plt.axvline(0, color="black", lw=0.5, ls="--")
    plt.legend()

    # График производной
    plt.subplot(1, 2, 2)
    plt.plot(x, dy_dx, label="sin'(x)", color="orange")
    plt.title("Производная функции синуса")
    plt.xlabel("x")
    plt.ylabel("sin'(x)")
    plt.grid()
    plt.axhline(0, color="black", lw=0.5, ls="--")
    plt.axvline(0, color="black", lw=0.5, ls="--")
    plt.legend()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":

    import matplotlib.pyplot as plt

    # test()
    res = pyvisa.ResourceManager().list_resources()
    rm = pyvisa.ResourceManager()
    try:
        client = rm.open_resource(res[0])
    except:
        client = "fake"
    osc = oscRigolCommands(client)
    osc.load_commands("hantek.json")
    osc.set_band_width(4, False)
