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

import json
import logging
import random

import numpy as np
import pyvisa

logger = logging.getLogger(__name__)

class oscRigolCommands:
    def __init__(self, device) -> None:
        self.device = device

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
            if ans in focus_answer:
                logger.warning(f"Ответ не полностью совпадает с референсным значениемю. Ответ: {ans} Референсное значение: {focus_answer}")
                return True
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
                    logger.warning("неудачное считывание параметров осциллограммы")
        else:
            status = True
            result = {}
            for num_ch in channels_number:
                frequency = np.random.uniform(
                    0.5, 5.0
                )
                x = np.linspace(0, 2 * np.pi, 3000)
                sine_wave = np.round(
                    np.sin(frequency * x), 2
                )
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
    
    def load_commands(self, json_file: str):
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
                self.data_device = data
                self.channels_number = int(data["number_channels"])
                self.commands = data['commands']
        except Exception as e:
            logger.error(f"Не удалось загрузить команды из {json_file}: {e}")

    def get_data(self, start_point, end_point):
        new_data = []

        self.set_start_point(start_point)
        self.set_end_point(end_point)
        self.device.client.write(":WAV:DATA?\r\n")
         
        status = True
        try:
            data = self.device.client.read_raw()
            data = str(data).split(",")
            new_data = [round(float(data[i]), 2) for i in range(1, len(data) - 1)]
        except pyvisa.errors.VisaIOError as e:
            logger.error(f"Ошибка чтения данных: {e}")
            status = False

        return status, new_data

    def set_start_point(self, point):
        command_template = self.commands["set_start_point"]["command"]
        command = command_template.format(point=point)
        self.device.client.write(command)

    def set_end_point(self, point):
        command_template = self.commands["set_end_point"]["command"]
        command = command_template.format(point=point)
        self.device.client.write(command)

    def get_sample_rate(self):
        command = self.commands["get_sample_rate"]["command"]
        sample_rate = self.device.client.query_ascii_values(command)
        return sample_rate

    def set_band_width(self, number_ch: int, is_enable: bool) -> bool:
        if number_ch < 1 or number_ch > self.channels_number:
            return False

        # Получаем команду из загруженных команд
        command_template = self.commands["set_band_width"]["command"]
        command = command_template.format(number_ch=number_ch, is_enable='20M' if is_enable else 'OFF')
        
        # Отправляем команду на устройство
        self.device.client.write(command)
        
        # Проверяем результат, если указано
        if "check_command" in self.commands["set_band_width"]:
            check_command_template = self.commands["set_band_width"]["check_command"]
            check_command = check_command_template.format(number_ch=number_ch)
            focus_answer = self.commands["set_band_width"]["focus_answer"].format(is_enable='20M' if is_enable else 'OFF')
            
            return self.check_parameters(command=check_command, focus_answer=focus_answer)

        return True

    def set_coupling(self, number_ch: int, coupling="DC") -> bool:
        if number_ch < 1 or number_ch > self.channels_number:
            return False
        
        command_template = self.commands["set_coupling"]["command"]
        command = command_template.format(number_ch=number_ch, coupling=coupling)
        self.device.client.write(command)

        check_command_template = self.commands["set_coupling"]["check_command"]
        check_command = check_command_template.format(number_ch=number_ch)
        focus_answer = self.commands["set_coupling"]["focus_answer"].format(coupling=coupling)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_trigger_mode(self, mode) -> bool:
        command_template = self.commands["set_trigger_mode"]["command"]
        command = command_template.format(mode=mode)
        self.device.client.write(command)

        check_command_template = self.commands["set_trigger_mode"]["check_command"]
        check_command = check_command_template
        focus_answer = self.commands["set_trigger_mode"]["focus_answer"].format(mode=mode)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_trigger_edge_slope(self, slope) -> bool:
        if slope.upper() == "POSITIVE":
            slope = "POS"
        elif slope.upper() == "NEGATIVE":
            slope = "NEG"
        elif slope.upper() == "RFALl":
            slope = "RFAL"
        command_template = self.commands["set_trigger_edge_slope"]["command"]
        command = command_template.format(slope=slope)
        self.device.client.write(command)

        check_command_template = self.commands["set_trigger_edge_slope"]["check_command"]
        check_command = check_command_template
        focus_answer = self.commands["set_trigger_edge_slope"]["focus_answer"].format(slope=slope)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_trigger_sweep(self, sweep) -> bool:
        if sweep.upper() == "NORMAL":
            sweep = "NORM"
        elif sweep.upper() == "SINGLE":
            sweep = "SING"
        elif sweep.upper() == "AUTO":
            sweep = "AUTO"
        command_template = self.commands["set_trigger_sweep"]["command"]
        command = command_template.format(sweep=sweep)
        self.device.client.write(command)

        check_command_template = self.commands["set_trigger_sweep"]["check_command"]
        check_command = check_command_template
        focus_answer = self.commands["set_trigger_sweep"]["focus_answer"].format(sweep=sweep)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_trigger_source(self, number_ch) -> bool:
        try:
            number_ch = int(number_ch)
        except ValueError:
            return False

        if number_ch < 1 or number_ch > self.channels_number:
            return False

        command_template = self.commands["set_trigger_source"]["command"]
        command = command_template.format(number_ch=number_ch)

        self.device.client.write(command)

        check_command_template = self.commands["set_trigger_source"]["check_command"]
        check_command = check_command_template.format(number_ch=number_ch)
        focus_answer = self.commands["set_trigger_source"]["focus_answer"].format(number_ch=number_ch)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_trigger_edge_level(self, level) -> bool:
        try:
            level = float(level)
        except ValueError:
            return False

        command_template = self.commands["set_trigger_edge_level"]["command"]
        command = command_template.format(level=level)

        self.device.client.write(command)

        check_command_template = self.commands["set_trigger_edge_level"]["check_command"]
        check_command = check_command_template.format(level=level)
        level = self.format_scientific(level)
        focus_answer = self.commands["set_trigger_edge_level"]["focus_answer"].format(level=level)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

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
                    command_template = self.commands["get_meas_parameter"]["command"]
                    command = command_template.format(parameter=parameter, channel=ch)
                    data = self.device.client.query(command)
                else:
                    data = round(random.uniform(0, 100), 2)

                try:
                    data = float(data)
                except ValueError:
                    data = "fail"
                result.append(data)
        else:
            for ch in channels:
                result.append("fail")
        
        return result

    def set_scale(self, scale) -> bool:
        try:
            scale = float(scale)
        except ValueError:
            return False

        command_template = self.commands["set_scale"]["command"]
        command = command_template.format(scale=scale)

        self.device.client.write(command)

        if "check_command" in self.commands["set_scale"]:
            check_command_template = self.commands["set_scale"]["check_command"]
            check_command = check_command_template.format(scale=scale)
            focus_answer = self.commands["set_scale"]["focus_answer"].format(scale=f"{scale:.7e}")

            return self.check_parameters(command=check_command, focus_answer=focus_answer)

        return True

    def get_scale(self):
        command_template = self.commands["get_scale"]["command"]
        command = command_template

        scale = self.device.client.query_ascii_values(command)
        return scale[0]

    def set_wave_sourse(self, number_ch) -> bool:
        if number_ch < 1 or number_ch > self.channels_number:
            return False

        command_template = self.commands["set_wave_source"]["command"]
        command = command_template.format(number_ch=number_ch)

        self.device.client.write(command)

        check_command_template = self.commands["set_wave_source"]["check_command"]
        check_command = check_command_template.format(number_ch=number_ch)
        focus_answer = self.commands["set_wave_source"]["focus_answer"].format(number_ch=number_ch)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def run(self):
        command_template = self.commands["run"]["command"]
        command = command_template
        self.device.client.write(command)

    def stop(self):
        command_template = self.commands["stop"]["command"]
        command = command_template
        self.device.client.write(command)

    def clear(self):
        command_template = self.commands["clear"]["command"]
        command = command_template
        self.device.client.write(command)

    def single(self):
        command_template = self.commands["single"]["command"]
        command = command_template
        self.device.client.write(command)

    def get_status(self) -> str:
        '''returning values:TD WAIT AUTO STOP'''
        command_template = self.commands["get_status"]["command"]
        return self.device.client.query(command_template)

    def set_wave_form_mode(self, mode="RAW") -> bool:
        command_template = self.commands["set_wave_form_mode"]["command"]
        command = command_template.format(mode=mode)
        self.device.client.write(command)

        check_command_template = self.commands["set_wave_form_mode"]["check_command"]
        check_command = check_command_template
        focus_answer = self.commands["set_wave_form_mode"]["focus_answer"].format(mode=mode)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_wave_format(self, format="ASC") -> bool:
        command_template = self.commands["set_wave_format"]["command"]
        command = command_template.format(format=format)
        self.device.client.write(command)

        check_command_template = self.commands["set_wave_format"]["check_command"]
        check_command = check_command_template
        focus_answer = self.commands["set_wave_format"]["focus_answer"].format(format=format)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_BW_limit(self, ch_number, bw_limit) -> bool:
        command_template = self.commands["set_bw_limit"]["command"]
        command = command_template.format(ch_number=ch_number, bw_limit=bw_limit)
        self.device.client.write(command)

        check_command_template = self.commands["set_bw_limit"]["check_command"]
        check_command = check_command_template.format(ch_number=ch_number)
        focus_answer = self.commands["set_bw_limit"]["focus_answer"].format(bw_limit=bw_limit)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_probe(self, ch_number, probe) -> bool:
        try:
            probe = float(probe)
        except ValueError:
            return False

        command_template = self.commands["set_probe"]["command"]
        command = command_template.format(ch_number=ch_number, probe=probe)
        self.device.client.write(command)

        check_command_template = self.commands["set_probe"]["check_command"]
        check_command = check_command_template.format(ch_number=ch_number)
        focus_answer = self.commands["set_probe"]["focus_answer"].format(probe=self.format_scientific(probe))

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_ch_scale(self, ch_number, scale) -> bool:
        try:
            scale = float(scale)
        except ValueError:
            return False

        command_template = self.commands["set_ch_scale"]["command"]
        command = command_template.format(ch_number=ch_number, scale=scale)
        self.device.client.write(command)

        check_command_template = self.commands["set_ch_scale"]["check_command"]
        check_command = check_command_template.format(ch_number=ch_number)
        focus_answer = self.commands["set_ch_scale"]["focus_answer"].format(scale=self.format_scientific(scale))

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_invert(self, ch_number, invert) -> bool:
        if invert == "OFF":
            invert = 0
        elif invert == "ON":
            invert = 0
        else:
            raise ValueError(f"invert must be 'OFF' or 'ON', not {invert}")

        command_template = self.commands["set_invert"]["command"]
        command = command_template.format(ch_number=ch_number, invert=invert)
        self.device.client.write(command)

        check_command_template = self.commands["set_invert"]["check_command"]
        check_command = check_command_template.format(ch_number=ch_number)
        focus_answer = self.commands["set_invert"]["focus_answer"].format(invert=invert)

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def set_meas_source(self, number_ch) -> bool:
        if number_ch < 1 or number_ch > self.channels_number:
            return False

        command_template = self.commands["set_meas_source"]["command"]
        command = command_template.format(number_ch=number_ch)
        self.device.client.write(command)

        check_command_template = self.commands["set_meas_source"]["check_command"]
        check_command = check_command_template
        focus_answer = f"CHAN{number_ch}\n"

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

    def on_off_channel(self, number_ch, is_enable=False) -> bool:
        if number_ch < 1 or number_ch > self.channels_number:
            return False

        state = 1 if is_enable else 0
        command_template = self.commands["on_off_channel"]["command"]
        command = command_template.format(number_ch=number_ch, state=state)
        self.device.client.write(command)

        check_command_template = self.commands["on_off_channel"]["check_command"]
        check_command = check_command_template.format(number_ch=number_ch)
        focus_answer = f"{state}\n"

        return self.check_parameters(command=check_command, focus_answer=focus_answer)

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
    import matplotlib.pyplot as plt
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

class R:
    def __init__(self, client):
        self.client = client

if __name__ == "__main__":

    # test()
    device = R
    res = pyvisa.ResourceManager().list_resources()
    rm = pyvisa.ResourceManager()
    client = rm.open_resource(res[0])

    print(client.query(":CHANnel2:BWLimit?"))
