import time
import pyvisa
import numpy as np
import matplotlib.pyplot as plt

class A:
        def __init__(self, client) -> None:
            self.client = client

        def test(self):
            _, result = self.get_raw_wave_data(channels_number=[1], timeout=3)
            if result != {}:
                for key in result.keys():
                    self.show_graph(result[key])

                return result

        def get_raw_wave_data(self, channels_number: list, timeout = 3) -> dict:
            ''' 1. Делаем одиночный захват осциллогрраммы
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
                    print(f"Не дождались остановки по триггеру, останавливаем сами")
                    self.stop()

            for num_ch in channels_number:
                self.set_wave_sourse(num_ch)
                status , arr = self.get_all_data_sourse(points)
                if status:
                    result[num_ch] = arr
                else:
                    print("неудачное считывание")

            return status, result

        def calculate_step_time(self) -> float:
            '''return step beetwen points'''
            sample_rate = self.client.query_ascii_values(f'ACQ:SRATe?\n')
            return 1/sample_rate[0]
        
        def calc_integral(self, arr, step):
            return np.sum((arr[:-1] + arr[1:])*step/2)
        
        def set_band_width(self, number_ch: int, is_enable: bool) -> bool: #
            if number_ch < 1 or number_ch > 4:
                return False
            if is_enable:
                self.client.write(f":CHANnel{number_ch}:BWLimit 20M")
                is_ok = self.check_parameters(command=f":CHANnel{number_ch}:BWLimit?", focus_answer='20M\n')
            else:
                self.client.write(f":CHANnel{number_ch}:BWLimit OFF")
                is_ok = self.check_parameters(command=f":CHANnel{number_ch}:BWLimit?", focus_answer='OFF\n')
            return is_ok
        
        def set_coupling(self, number_ch: int, coupling = "DC") -> bool:#
            if number_ch < 1 or number_ch > 4:
                return False
            self.client.write(f":CHANnel{number_ch}:COUPling {coupling}")
            is_ok = self.check_parameters(command=f":CHANnel{number_ch}:COUPling?", focus_answer=f'{coupling}\n')
            return is_ok
        
        def set_trigger_sourse(self, number_ch) -> bool:#
            if number_ch < 1 or number_ch > 4:
                return False
            self.client.write(f":TRIGger:EDGe:SOURce CHANnel{number_ch}")
            is_ok = self.check_parameters(command=f":TRIGger:EDGe:SOURce?", focus_answer=f"CHAN{number_ch}\n")
            return is_ok

        def check_parameters(self, command, focus_answer) -> bool: #
            ans = self.client.query(command)

            if isinstance(focus_answer, (int, float)):#если числоо, то и ответ нужно пеобразовать в число
                ans = float(ans)

            print(f"{command=} {ans=} {ans==focus_answer}")
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
        
        def calculate_num_points(self):
            scale = self.client.query_ascii_values(f'TIM:MAIN:SCALe?\n')
            print(f"{scale=}")

            sample_rate = self.client.query_ascii_values(f'ACQ:SRATe?\n')
            print(f"{sample_rate=}")

            max_points_on_screen = sample_rate[0] * scale[0] * 12#12 - это чсло клеток по горизонтальной оси
            print(f"{max_points_on_screen=}")
            return max_points_on_screen
        
        def set_scale(self, scale):#
            self.client.write(f'TIM:MAIN:SCALe {scale}\n')
            is_ok = self.check_parameters(command=f'TIM:MAIN:SCALe?\n',  focus_answer=scale)
            return is_ok
        
        def set_wave_sourse(self, number_ch)-> bool:#
            if number_ch < 1 or number_ch > 4:
                return False
            self.client.write(f':WAV:SOUR CHANnel{number_ch}\n' )##set wave sourse
            is_ok = self.check_parameters(command=f':WAV:SOUR?\n', focus_answer=f"CHAN{number_ch}\n")
            return is_ok

        def run(self):
            self.client.write(f':RUN\n' )

        def stop(self):
            self.client.write(f':STOP\n' )

        def clear(self):
            self.client.write(f':CLE\n' )

        def single(self):
            self.client.write(f':SING\n' )

        def get_status(self) -> str:
            return self.client.query(f':TRIG:STAT?\n' )

        def set_wave_form_mode(self, mode = "RAW")-> bool:#
            client.write(f':WAV:MODE {mode}\n' )
            is_ok =  self.check_parameters(command=f':WAV:MODE?\n', focus_answer=mode+"\n")
            return is_ok
        
        def set_wave_format(self, format = "ASC" ) -> bool:#
            client.write(f':WAV:FORM {format}\n' )
            is_ok =  self.check_parameters(command=f':WAV:FORM?\n', focus_answer=format+"\n")
            return is_ok
        
        def set_meas_sourse(self, number_ch)-> bool:#
            if number_ch < 1 or number_ch > 4:
                return False
            self.client.write(f':MEAS:SOUR CHANnel{number_ch}\n' )##set wave sourse
            is_ok = self.check_parameters(command=f':MEAS:SOUR?\n', focus_answer=f"CHAN{number_ch}\n")
            return is_ok
        
        def on_off_channel(self, number_ch, is_enable = False):#
            if number_ch < 1 or number_ch > 4:
                return False
            if is_enable:
                self.client.write(f':CHANnel{number_ch}:DISP {1}\n' )##set wave sourse
                is_ok = self.check_parameters(command=f':CHANnel{number_ch}:DISP?\n', focus_answer=f"{1}\n")
            else:
                self.client.write(f':CHANnel{number_ch}:DISP {0}\n' )##set wave sourse
                is_ok = self.check_parameters(command=f':CHANnel{number_ch}:DISP?\n', focus_answer=f"{0}\n")
            return is_ok
        
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

            plt.title("Наша осциллограмма")
            fig.tight_layout()
            fig.legend()
            plt.grid(True)
            plt.show()

if __name__ == "__main__":

    res = pyvisa.ResourceManager().list_resources()
    rm = pyvisa.ResourceManager()

    print(f"Обнаруженные интерфейсы:")
    for i in range( 0, len( res), 1):
        print(f"{i+1}: {res[i]}")
    number = input("Введите номер интерфейса.. ")
    number = int(number)
    number-=1

    client = rm.open_resource(res[number])
    osc = A(client)

    print(f"Запрашиваем информацию об устройстве командой *IDN?..")
    print("Ответ устройства:")
    data = client.query(f'*IDN?\n')
    print(data)

    input()

    scale = 0.0005
    print(f"Устанавливаем величину scale равной 500 мкс командой TIM:MAIN:SCALe {scale}..")
    client.write(f'TIM:MAIN:SCALe {scale}')

    input()

    print(f"Проверяем, чему равна величина scale после установки командой 'TIM:MAIN:SCALe?' ")
    scale = client.query_ascii_values(f'TIM:MAIN:SCALe?\n')
    print("Ответ устройства:")
    print(f"{scale=}")

    input()

    print(f"запросим у осциллографа информацию о количестве снимаемых точек за секунду(sample rate). Делаем это командой 'ACQ:SRATe?'..")
    sample_rate = client.query_ascii_values(f'ACQ:SRATe?\n')
    print("Ответ устройства:")
    print(f"{sample_rate=}")

    input()
    max_points_on_screen = sample_rate[0] * scale[0] * 12
    print(f'''Посчитаем, сколько всего точек вмещается на экран осциллографа на данный момент.
           Для этого величину sample_rate умножаем на scale и на число клеток на экране(12)
          {sample_rate} * {scale} * 12 = {max_points_on_screen}''')

    input()


    print(f'''Теперь давайте попросим осциллограф передать нам данные осциллограммы с первого канала. Для этого необходимо произвести ряд действий:
          - Произвести запуск командой :RUN
          - Установить режим присылаемых данных командой :WAV:MODE RAW
          - Установить формат присылаемых данных командой :WAV:FORM ASC
          - Далее попробовать произвести остановку по захвату триггером сигнала, подождать 3 секунды и, если не получилось, остановить принудительно. Команды :SING , :STOP
          - Установим канал, осциллограмму которого хотим получить :WAV:SOUR CHANnel1
          - Затем вычислим количество точек, которые необходимо принять. Мы это сделали выше.
          - Количество отправляемых осциллографом точек за один раз ограничено, поэтому мы будем весь пакет считывать поочередно. 
          Для этого устанавливается начальный и конечный номер принимаемых точек, производится считывание, запись в память, 
          затем начальный и конечный номера сдвигаются и все действия повторяются до тех пор, пока все точки не будут считаны. 
          Команды :WAV:STARt (номер) :WAV:STOP (номер) :WAV:DATA?
          
          Если в процессе считывания что-то пойдет не так. выведем диагностические сообщения. Нажмите любую клавишу для запуска вышеописанной процедуры''')
    
    input()
    
    result_array = osc.test()

    





 