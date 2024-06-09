import time
import serial
import matplotlib.pyplot as plt
import statistics

if __name__ == "__main__":
    find1 = "x="
    find2 = "y="
    find3 = "z="
    N = 500  # Количество точек для отображения
    M = 50 #количество точек для калибровки
    update_flag = False
    client = serial.Serial("COM6", 9600, timeout=1)

    corr_val = [0,0,0]
    plt.ion()  # Режим интерактивного построения графика
    x = []
    y_values = {find1: [], find2: [], find3: []}
    lines = {}

    fig, ax1 = plt.subplots()
    for find in [find1, find2, find3]:
        if find:
            lines[find], = ax1.plot(x, y_values[find], label=find)

    ax1.legend() 
    ax1.set_xlabel('Время')
    ax1.set_ylabel('uT')


    ax1.grid(True)
    ax1.grid(which='both', color='gray', linestyle='-', linewidth=0.5)
    ax1.minorticks_on()
    ax1.grid(which='minor', color='black', linestyle=':', linewidth=0.5)

    start_time = time.time()

    while True:
        time.sleep(0.01)
        data = client.readline().decode().strip()  
        start_position = []

        if data:

            status = True
            for find in [find1, find2, find3]:
                if find != False:
                    start_pos = data.find(find)
                    if start_pos == -1:
                        status = False
                        break
                    else:
                        start_position.append(start_pos)
            if status:
                    i = 0
                    for find, corr in zip([find1, find2, find3], corr_val):
                        if find != False:
                            start_pos = start_position[i]
                            i+=1
                            for j in range(9):
                                #print(data[start_pos + 2: start_pos + 9-j])
                                #time.sleep(0.5)
                                try:
                                    value = float(data[start_pos + 2: start_pos + 9-j])
                                    break
                                except ValueError:
                                    pass
                            y_values[find].append(value - corr)

                    x.append(time.time() - start_time)


                    if update_flag == True:
                        for find in [find1, find2, find3]:
                            if find:
                                if len(x) > N:
                                    lines[find].set_data(x[-N:], y_values[find][-N:])
                                else:
                                    lines[find].set_data(x, y_values[find])

                        ax1.relim()
                        ax1.autoscale_view()
                        plt.draw()
                        plt.pause(0.01)
                    else:
                        if len(x) == M:
                            corr_val = []
                            update_flag = True
                            corr_val.append(statistics.mean(y_values[find1]))
                            corr_val.append(statistics.mean(y_values[find2]))
                            corr_val.append(statistics.mean(y_values[find3]))
                            y_values = {find1: [], find2: [], find3: []}
                            x = []

