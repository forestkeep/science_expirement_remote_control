
import time
import pyvisa
import numpy
import matplotlib.pyplot as plt

class A:
        def __init__(self, client) -> None:
            self.client = client
            self.test()
            
        def test(self):
            self.set_band_width(1, True)

        def set_band_width(self, number_ch: int, is_enable: bool) -> bool:#
            if is_enable:
                self.client.write(f":CHANnel{number_ch}:BWLimit 1")
                is_ok = self.check_parameters(command=f":CHANnel{number_ch}:BWLimit?", focus_answer="1")
            else:
                self.client.write(f":CHANnel{number_ch}:BWLimit 0")
                is_ok = self.check_parameters(command=f":CHANnel{number_ch}:BWLimit?", focus_answer="0")
            return is_ok
        
        def set_coupling(self, number_ch: int, coupling = "DC") -> bool:#
            self.client.write(f":CHANnel{number_ch}:COUPling {coupling}")
            is_ok = self.check_parameters(command=f":CHANnel{number_ch}:COUPling?", focus_answer=coupling)
            return is_ok
        
        def set_trigger_sourse(self, number_ch) -> bool:#
            self.client.write(f":TRIGger:EDGe:SOURce CHANnel{number_ch}")
            is_ok = self.check_parameters(command=f":TRIGger:EDGe:SOURce?", focus_answer=f"CHANnel{number_ch}")
            return is_ok

        def check_parameters(self, command, focus_answer) -> bool:#
            ans = self.client.query(command)
            print(f"{command=} {ans=}")
            if ans == focus_answer:
                return True
            else:
                return False

        def get_all_data(self, max_points_on_screen) -> list:
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
 
            new_data = numpy.asarray(new_data)
            return state, new_data

        def get_data(self, start_point, end_point):
            new_data = []

            self.client.write(f':WAV:STARt {start_point}\n' )
            self.client.write(f':WAV:STOP {end_point}\n' )
            self.client.write(f':WAV:DATA?\n' )
            status = True
            try:
                data = self.client.read_raw()
                data = str(data)
                data = data.split(',')
                for i in range(1, len(data) -1, 1):
                    new_data.append(round(float(data[i]), 2))
            except pyvisa.errors.VisaIOError:
                status = False
                print("таймаут")

            print(f"{len(new_data)}")
            return status, new_data
        
        def calculate_num_points(self):#
            scale = self.client.query_ascii_values(f'TIM:SCALe?\n')
            print(f"{scale=}")

            sample_rate = self.client.query_ascii_values(f'ACQ:SRATe?\n')
            print(f"{sample_rate=}")

            max_points_on_screen = sample_rate[0] * scale[0] * 12#12 - это чсло клеток по горизонтальной оси
            print(f"{max_points_on_screen=}")
            return max_points_on_screen
        
        def set_scale(self, scale):#
            self.client.write(f'TIM:SCALe {scale}\n')
            is_ok = self.check_parameters(command=f'TIM:SCALe?\n',  focus_answer=scale)
            return is_ok
        
        def set_wave_sourse(self, number_ch)-> bool:
            self.client.write(f':WAV:SOUR CHANnel{number_ch}\n' )##set wave sourse
            is_ok = self.check_parameters(command=f':WAV:SOUR?\n', focus_answer=f"CHAN{number_ch}")
            return is_ok

        def run(self):
            self.client.write(f':RUN\n' )

        def stop(self):
            self.client.write(f':STOP\n' )

        def set_wave_form_mode(self, mode = "RAW")-> bool:
            client.write(f':WAV:MODE {mode}\n' )
            is_ok =  self.check_parameters(command=f':WAV:MODE?\n', focus_answer=mode)
            return is_ok
        
        def set_wave_format(self, format = "ASCii" ) -> bool:
            client.write(f':WAV:FORM {format}\n' )
            is_ok =  self.check_parameters(command=f':WAV:FORM?\n', focus_answer=format)
            return is_ok
          

if __name__ == "__main__":


    res = pyvisa.ResourceManager().list_resources()
    rm = pyvisa.ResourceManager()

    print(res)
    print("Введите индекс ресурса")

    #idx = int(input())
    client = rm.open_resource(res[0])
    osc = A(client)
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
    
'''
'WAVeform:DATA:ALL?'
Описание возвращаемых значений с осциллографа
Первый вызов команды
Диапазон	             Длина (цифры)	Описание
data[0]-data[1]	            2 цифры	    Номер команды (#9)
data[2]-data[10]	        9 цифр	    Длина текущего пакета в байтах
data[11]-data[19]	        9 цифр	    Общая длина данных в байтах
data[20]-data[28]	        9 цифр	    Длина загруженных данных в байтах
data[29]	                1 цифра	    Текущий статус выполнения
data[30]	                1 цифра	    Статус триггера
data[31-34]	                4 цифры	    Смещение канала 1
data[35-38]	                4 цифры	    Смещение канала 2
data[39-42]	                4 цифры	    Смещение канала 3
data[43-46]	                4 цифры	    Смещение канала 4
data[47]-data[53]	        7 цифр	    Напряжение канала 1
data[54]-data[60]	        7 цифр	    Напряжение канала 2
data[61]-data[67]	        7 цифр	    Напряжение канала 3
data[68]-data[74]	        7 цифр	    Напряжение канала 4
data[75]-data[78]	        4 цифры	    Включение каналов (1-4)
data[79]-data[87]	        9 цифр	    Частота дискретизации
data[88]-data[93]	        6 цифр	    Коэффициент дискретизации
data[94]-data[102]	        9 цифр	    Время срабатывания дисплея текущего кадра
data[103]-data[111]	        9 цифр	    Начальная точка времени захвата текущего кадра
data[112]-data[127]	        16 цифр	    Зарезервированные биты
Второй вызов команды до считывания данных
Диапазон	            Длина (цифры)	Описание
data[0]-data[1]	            2 цифры	    Номер команды (#9)
data[2]-data[10]	        9 цифр	    Длина текущего пакета в байтах
data[11]-data[19]	        9 цифр	    Общая длина данных в байтах
data[20]-data[28]	        9 цифр	    Длина загруженных данных в байтах
data[29]-data[x]	переменная	Данные формы, соответствующие текущему заголовку данных

'''