import time, test_rigol
import pyvisa
import numpy as np
import matplotlib.pyplot as plt

class oscRigolCommands:
        def __init__(self, device) -> None:
            self.device = device

        def test(self):
            scale = 0.0005
            self.set_scale(scale=scale)

            _, result = self.get_raw_wave_data( channels_number=[1,2], timeout=3 )
            if result != {}:

                test_rigol.test_calc( arr1 = result['1'], arr2 = result['2'], increment = scale )
                
                for key in result.keys():
                    self.show_graph( result[key] )
                    integral = self.calc_integral( result[key], step=self.calculate_step_time() )
                    print(f"ch {key} {integral=}")

        def get_raw_wave_data(self, channels_number: list, timeout = 3) -> dict:
            ''' 1. Делаем одиночный захват осциллограммы
                2. поочередно считываем данные на переданных каналах
            возвращаем статус + словарь, где ключи - это номера каналов, а значения списки данных'''
            status = True
            self.set_wave_form_mode(mode = "RAW")
            self.set_wave_format(format="ASC")
            points = self.calculate_num_points()
            result = {}
            self.run()
            self.single()
            time_stamp = time.time()
            while self.get_status() != 'STOP\n':
                if time.time() - time_stamp > timeout:
                    print(f"Timeout!!")
                    self.stop()
                    self.run()
                    return False, result

            for num_ch in channels_number:
                self.set_wave_sourse(num_ch)
                status_local , arr = self.get_all_data_sourse(points)
                if status_local:
                    result[num_ch] = arr
                else:
                    status = False
                    print("неудачное считывание")

            return status, result

        def calculate_step_time(self) -> float:
            '''return step beetwen points'''
            sample_rate = self.device.client.query_ascii_values(f'ACQ:SRATe?\n')
            return 1/sample_rate[0]
        
        def calc_integral(self, arr, step):
            return np.sum((arr[:-1] + arr[1:])*step/2)
        
        def set_band_width(self, number_ch: int, is_enable: bool) -> bool: #
            if number_ch < 1 or number_ch > 4:
                return False
            if is_enable:
                self.device.client.write(f":CHANnel{number_ch}:BWLimit 20M")
                is_ok = self.check_parameters(command=f":CHANnel{number_ch}:BWLimit?", focus_answer='20M\n')
            else:
                self.device.client.write(f":CHANnel{number_ch}:BWLimit OFF")
                is_ok = self.check_parameters(command=f":CHANnel{number_ch}:BWLimit?", focus_answer='OFF\n')
            return is_ok
        
        def set_coupling(self, number_ch: int, coupling = "DC") -> bool:#
            if number_ch < 1 or number_ch > 4:
                return False
            self.device.client.write(f":CHANnel{number_ch}:COUPling {coupling}")
            is_ok = self.check_parameters(command=f":CHANnel{number_ch}:COUPling?", focus_answer=f'{coupling}\n')
            return is_ok
        
        def set_trigger_sourse(self, number_ch) -> bool:#
            if number_ch < 1 or number_ch > 4:
                return False
            self.device.client.write(f":TRIGger:EDGe:SOURce CHANnel{number_ch}")
            is_ok = self.check_parameters(command=f":TRIGger:EDGe:SOURce?", focus_answer=f"CHAN{number_ch}\n")
            return is_ok

        def check_parameters(self, command, focus_answer) -> bool: #
            ans = self.device.client.query(command)

            if isinstance(focus_answer, (int, float)):#если число, то и ответ нужно преобразовать в число
                ans = float(ans)

            print(f"{command=} {ans=} {focus_answer=} {ans==focus_answer}")
            if ans == focus_answer:
                
                return True
            else:
                return False

        def get_all_data_sourse(self, max_points_on_screen) -> list:
            new_data = []
            state = True
            balance = max_points_on_screen
            step_point = 100000
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
                
                balance-=step_point
                start=end+1
                if step_point > balance:
                    step_point = balance
                end+=step_point
 
            new_data = np.asarray(new_data)
            return state, new_data

        def get_data(self, start_point, end_point):
            new_data = []
            print(f"{start_point=} {end_point=}")

            self.device.client.write(f':WAV:STARt {start_point}\n' )
            self.device.client.write(f':WAV:STOP {end_point}\n' )
            self.device.client.write(f':WAV:DATA?\n' )
            status = True
            try:
                data = self.device.client.read_raw()
                data = str(data)
                data = data.split(',')
                for i in range(1, len(data) -1, 1):
                    new_data.append(round(float(data[i]), 2))
            except pyvisa.errors.VisaIOError:
                status = False
                print("таймаут")

            print(f"{len(new_data)}")
            return status, new_data
        
        def calculate_num_points(self):
            scale = self.device.client.query_ascii_values(f'TIM:MAIN:SCALe?\n')
            print(f"{scale=}")

            sample_rate = self.device.client.query_ascii_values(f'ACQ:SRATe?\n')
            print(f"{sample_rate=}")

            max_points_on_screen = sample_rate[0] * scale[0] * 12#12 - это чсло клеток по горизонтальной оси
            print(f"{max_points_on_screen=}")
            return max_points_on_screen
        
        def set_scale(self, scale):#

            self.device.client.write(f'TIM:MAIN:SCALe {scale}\n')
            is_ok = self.check_parameters(command=f'TIM:MAIN:SCALe?\n',  focus_answer=scale)
            return is_ok
        
        def set_wave_sourse(self, number_ch)-> bool:#
            if number_ch < 1 or number_ch > 4:
                return False
            self.device.client.write(f':WAV:SOUR CHANnel{number_ch}\n' )##set wave sourse
            is_ok = self.check_parameters(command=f':WAV:SOUR?\n', focus_answer=f"CHAN{number_ch}\n")
            return is_ok

        def run(self):
            self.device.client.write(f':RUN\n' )

        def stop(self):
            self.device.client.write(f':STOP\n' )

        def clear(self):
            self.device.client.write(f':CLE\n' )

        def single(self):
            self.device.client.write(f':SING\n' )

        def get_status(self) -> str:
            return self.device.client.query(f':TRIG:STAT?\n' )

        def set_wave_form_mode(self, mode = "RAW")-> bool:#
            self.device.client.write(f':WAV:MODE {mode}\n' )
            is_ok =  self.check_parameters(command=f':WAV:MODE?\n', focus_answer=mode+"\n")
            return is_ok
        
        def set_wave_format(self, format = "ASC" ) -> bool:#
            self.device.client.write(f':WAV:FORM {format}\n' )
            is_ok =  self.check_parameters(command=f':WAV:FORM?\n', focus_answer=format+"\n")
            return is_ok
        
        def set_meas_sourse(self, number_ch)-> bool:#
            if number_ch < 1 or number_ch > 4:
                return False
            self.device.client.write(f':MEAS:SOUR CHANnel{number_ch}\n' )##set wave sourse
            is_ok = self.check_parameters(command=f':MEAS:SOUR?\n', focus_answer=f"CHAN{number_ch}\n")
            return is_ok
        
        def on_off_channel(self, number_ch, is_enable = False):#
            if number_ch < 1 or number_ch > 4:
                return False
            if is_enable:
                self.device.client.write(f':CHANnel{number_ch}:DISP {1}\n' )##set wave sourse
                is_ok = self.check_parameters(command=f':CHANnel{number_ch}:DISP?\n', focus_answer=f"{1}\n")
            else:
                self.device.client.write(f':CHANnel{number_ch}:DISP {0}\n' )##set wave sourse
                is_ok = self.check_parameters(command=f':CHANnel{number_ch}:DISP?\n', focus_answer=f"{0}\n")
            return is_ok
        

        def get_meas_parameter(self, parameter:str, channels:list) -> list:
            result = []
            parameters = [
                            "VMAX", "VMIN", "VPP",
                            "VTOP", "VBASE", "VAMP", "VAVG", "VRMS", "OVERshoot", "MAREA", "MPAREA", "PREShoot", "PERIOD",
                            "FREQUENCY", "RTIME", "FTIME", "PWIDth", "NWIDth", "PDUTy", "NDUTy", "TVMAX", "TVMIN",
                            "PSLEWrate", "NSLEWrate", "VUPPER", "VMID", "VLOWER", "VARIance", "PVRMS", "PPULses",
                            "NPULses", "PEDGes", "NEDGes"
                        ]
            if parameter in parameters:
                self.device.client.write(f':STOP\n' )
                for ch in channels:
                    data = self.device.client.query(f":MEASure:ITEM? {parameter},CHANnel{ch}")
                    try:
                        data = float(data)
                    except:
                        data = 'fail'
                    result.append(data)
                self.device.client.write(f':RUN\n' )
            else:
                for ch in channels:
                    result.append('fail')
            return result
        
        def show_graph(self, arr):
            new_data = arr
            fig, ax1 = plt.subplots(figsize=(12, 8))

            cmap = plt.get_cmap('tab20')

            markers = ['o', 's', '^', 'v', 'p', '*', '+', 'x', 'D', 'H']  # Выбор стилей маркеров


            y = new_data
            x = range(len(y))
            ax1.scatter(x, y, label=f' (Main)', color='green', marker=markers[0], s=10)


            ax1.set_xlabel('Index')
            ax1.set_ylabel('Main Axis')

            plt.title("rtrrtrtrtrt")
            fig.tight_layout()
            fig.legend()
            plt.grid(True)
            plt.show()

def derivative_at_each_point(x, dx):
    derivative = np.zeros_like(x)
    
    for i in range(1, len(x) - 1):
        derivative[i] = (x[i+1] - x[i-1]) / (2 * dx)
    
    # Вычисление производной на краях массива с использованием односторонних разностей
    derivative[0] = (x[1] - x[0]) / dx
    derivative[-1] = (x[-1] - x[-2]) / dx
    
    return derivative


def find_sign_change(derivative):
    sign_changes = []
    for i in range(1, len(derivative)):
        if np.sign(derivative[i]) != np.sign(derivative[i - 1]) and np.sign(derivative[i]) > 0:
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
    print("Точки, в которых производная меняет знак:", x[sign_change_indices])

    # Вывод графика функции и ее производной
    plt.figure(figsize=(10, 5))

    # График функции синуса
    plt.subplot(1, 2, 1)
    plt.plot(x, y, label='sin(x)', color='blue')
    plt.title('Функция синуса')
    plt.xlabel('x')
    plt.ylabel('sin(x)')
    plt.grid()
    plt.axhline(0, color='black', lw=0.5, ls='--')
    plt.axvline(0, color='black', lw=0.5, ls='--')
    plt.legend()

    # График производной
    plt.subplot(1, 2, 2)
    plt.plot(x, dy_dx, label="sin'(x)", color='orange')
    plt.title('Производная функции синуса')
    plt.xlabel('x')
    plt.ylabel("sin'(x)")
    plt.grid()
    plt.axhline(0, color='black', lw=0.5, ls='--')
    plt.axvline(0, color='black', lw=0.5, ls='--')
    plt.legend()

    plt.tight_layout()
    plt.show()


def get_meas_parameter_test(client, parameter:str, channels:list) -> list:
            result = []
            parameters = [
                            "VMAX", "VMIN", "VPP",
                            "VTOP", "VBASE", "VAMP", "VAVG", "VRMS", "OVERshoot", "MAREA", "MPAREA", "PREShoot", "PERIOD",
                            "FREQUENCY", "RTIME", "FTIME", "PWIDth", "NWIDth", "PDUTy", "NDUTy", "TVMAX", "TVMIN",
                            "PSLEWrate", "NSLEWrate", "VUPPER", "VMID", "VLOWER", "VARIance", "PVRMS", "PPULses",
                            "NPULses", "PEDGes", "NEDGes"
                        ]
            if parameter in parameters:
                client.write(f':STOP\n' )
                for ch in channels:
                    data = client.query(f":MEASure:ITEM? {parameter},CHANnel{ch}")
                    try:
                        data = float(data)
                    except:
                        data = 'fail'
                    result.append(data)
                client.write(f':RUN\n' )
            else:
                for ch in channels:
                    result.append('fail')
            return result
def add(param):
    param.append(12)

if __name__ == "__main__":
    param = [1]
    add(param=param)
    print(param)

    #test()
    res = pyvisa.ResourceManager().list_resources()
    print(res)
    rm = pyvisa.ResourceManager()

    client = rm.open_resource(res[0])
    #client.write(":MEASure:AMSource CHANnel1,CHANnel2,CHANnel4")
    #client.write(":MEASure:ADISplay ON")
    parameters = [
    "VMAX", "VMIN", "VPP",
    "VTOP", "VBASE", "VAMP", "VAVG", "VRMS", "OVERshoot", "MAREA", "MPAREA", "PREShoot", "PERIOD",
    "FREQUENCY", "RTIME", "FTIME", "PWIDth", "NWIDth", "PDUTy", "NDUTy", "TVMAX", "TVMIN",
    "PSLEWrate", "NSLEWrate", "VUPPER", "VMID", "VLOWER", "VARIance", "PVRMS", "PPULses",
    "NPULses", "PEDGes", "NEDGes"
]
    for i in parameters:
        time.sleep(0.5)
        print(i)
        print(get_meas_parameter_test(client=client, parameter=i, channels=[1,2,3,4]))

    #osc = oscRigolCommands(client)
    #osc.test()
    if False:
        data = client.query(f'*IDN?\n')
        print(data)


        scale = 0.0002

        client.write(f'TIM:MAIN:SCALe {scale}\n')

        scale = client.query_ascii_values(f'TIM:MAIN:SCALe?\n')
        print(f"{scale=}")

        sample_rate = client.query_ascii_values(f'ACQ:SRATe?\n')
        print(f"{sample_rate=}")

        max_points_on_screen = sample_rate[0] * scale[0] * 12#12 - это чсло клеток по горизонтальной оси
        print(f"{max_points_on_screen=}")
        input()

        ax = client.query_ascii_values(f'CURSor:MANual:AXValue? \n')
        print(f"{ax=}")

        bx = client.query_ascii_values(f'CURSor:MANual:BXValue? \n')
        print(f"{bx=}")

        ay = client.query_ascii_values(f'CURSor:MANual:AYValue? \n')
        print(f"{ay=}")

        by = client.query_ascii_values(f'CURSor:MANual:BYValue? \n')
        print(f"{by=}")


        meas_sourse = client.query(f'MEAS:SOUR? \n')
        print(f"{meas_sourse=}")

        run =client.write(f':RUN\n' )
        client.write(f'ACQ:MDEPth AUTO \n')
        time.sleep(2)
        stop = client.write(f':STOP\n' )

        client.write(f':WAV:SOUR CHANnel2\n' )##set wave sourse
        wave_sourse = client.query(f':WAV:SOUR?\n' )##get waveform sourse
        print(f"{wave_sourse=}")

        
        client.write(f':WAV:SOUR CHAN1\n' )##set wave sourse
        wave_sourse = client.query(f':WAV:SOUR?\n' )##get waveform sourse
        print(f"{wave_sourse=}")

        client.write(f'ACQ:MDEPth? \n')
        '''
        1 канал - макс глубина 12000000
        2 канала - макс глбина 6000000
        3 или 4 канала макс глубина на канал 3000000
        '''
        memory_dept = client.read_raw()
        try:
            memory_dept = int(memory_dept.decode(), 10)
        except:
            pass
        print(f"{memory_dept=}")

        client.write(f':WAV:MODE RAW\n' )##set wave mode raw
        wave_mode = client.query(f':WAV:MODE?\n' )##get waveform sourse
        print(f"{wave_mode=}")

        client.write(f':WAV:FORM ASCii\n' )##set wave format ascii
        wave_form = client.query(f':WAV:FORM?\n' )##get waveform format
        print(f"{wave_form=}")



        new_data = []

        client.write(f':WAV:MODE MAX\n' )##set wave mode raw
        client.write(f':WAV:FORM ASCii\n' )##set wave format ascii
        step_point = 100000
        start = 1 
        end = step_point
        N = int(max_points_on_screen/step_point)+1
        if N == 0:
            N = 1
        print(f'{N=}')
        for i in range(N):
            data = get_data(start, end)
            for data in data:
                new_data.append(data)
            start+=step_point
            end+=step_point 

        new_data = numpy.asarray(new_data)

        fig, ax1 = plt.subplots(figsize=(12, 8))

        cmap = plt.get_cmap('tab20')

        markers = ['o', 's', '^', 'v', 'p', '*', '+', 'x', 'D', 'H']  # Выбор стилей маркеров


        y = new_data
        x = range(len(y))
        ax1.scatter(x, y, label=f' (Main)', color='green', marker=markers[0], s=10)


        ax1.set_xlabel('Index')
        ax1.set_ylabel('Main Axis')

        plt.title("rtrrtrtrtrt")
        fig.tight_layout()
        fig.legend()
        plt.grid(True)
        plt.show()







    #MAX,VMIN,VPP,VTOP,VBASe,VAMP,VAVG,VRMS,OVERshoot,PREShoot,MARea,MP ARea,PERiod,FREQuency,RTIMe,FTIMe,PWIDth,NWIDth,PDUTy,NDUTy,RDELay,FDE Lay,RPHase,FPHase,TVMAX,TVMIN,PSLEWrate,NSLEWrate,VUPper, VMID,VLOWer,VARIance,PVRMS,PPULses,NPULses,PEDGes,NEDGes>
    





 