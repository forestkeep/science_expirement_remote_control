import time
import serial
import matplotlib.pyplot as plt

if __name__ == "__main__":
    find1 = "x="
    find2 = "y="
    find3 = "z="


    number_meas = 1000000
    client = serial.Serial("COM6", 9600, timeout=1)

    client.write(bytes("open 1\n", "ascii"))
    time.sleep(1)
    client.write(bytes("db " + str(number_meas) + " 0 0\n", "ascii"))
    time.sleep(1)
    client.write(bytes("spd 34000 0 0\n", "ascii"))

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
    ax1.set_ylabel('count')


    ax1.grid(True)
    ax1.grid(which='both', color='gray', linestyle='-', linewidth=0.5)
    ax1.minorticks_on()
    ax1.grid(which='minor', color='black', linestyle=':', linewidth=0.5)

    start_time = time.time()

    while True:
        #file = open("test343434343.txt", 'a')
        time.sleep(0.01)
        data = client.readline().decode().strip()  
        start_position = []
        #print(data)

        
        if data:
            #file.write(data + "\n")
            #file.close()


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
                    for find in [find1, find2, find3]:
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
                            y_values[find].append(value)

                    x.append(time.time() - start_time)

                    N = 1000
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

