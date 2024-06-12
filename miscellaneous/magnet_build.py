import serial
import time
import matplotlib.pyplot as plt
import statistics

if __name__ == "__main__":
    find1 = "x="
    find2 = "y="
    N = 1500  # Количество точек для отображения
    M = 50 #количество точек для калибровки
    update_flag = False
    client = serial.Serial("COM6", 9600, timeout=1)

    plt.ion()
    x = []
    y_values = {find2: []}
    lines = {}

    corr_x_val, corr_y_val = 0,0

    fig, ax1 = plt.subplots()
    for find in [find2]:
        if find:
            lines[find], = ax1.plot(x, y_values[find], 'o', label=find)

    ax1.legend()
    ax1.set_xlabel('uT')
    ax1.set_ylabel('uT')

    ax1.grid(True)
    ax1.grid(which='both', color='gray', linestyle='-', linewidth=0.8)
    ax1.minorticks_on()
    ax1.grid(which='minor', color='black', linestyle=':', linewidth=0.8)

    start_time = time.time()

    while True:
        data = client.readline().decode().strip()
        start_position = []

        if data:
            status = True
            for find in [find1, find2]:
                if find != False:
                    start_pos = data.find(find)
                    if start_pos == -1:
                        status = False
                        break
                    else:
                        start_position.append(start_pos)
            if status:
                for j in range(9):
                    try:
                        x_value = float(data[start_position[0] + 2: start_position[0] + 9-j])
                        y_value = float(data[start_position[1] + 2: start_position[1] + 9-j])
                        break
                    except ValueError:
                        pass

                x.append(x_value - corr_x_val)
                y_values[find2].append(y_value - corr_y_val)
                if update_flag == True:
                    if len(x) > N:
                        x = x[-N:]
                        y_values[find2] = y_values[find2][-N:]
                    else:
                        pass

                    lines[find2].set_data(x, y_values[find2])

                    ax1.relim()
                    ax1.autoscale_view()

                    plt.draw()
                    plt.pause(0.005)
                else:
                    if len(x) == M:
                        update_flag = True
                        corr_x_val = statistics.mean(x)
                        corr_y_val = statistics.mean(y_values[find2])
                        print(corr_x_val, corr_y_val)
                        x = []
                        y_values = {find2: []}