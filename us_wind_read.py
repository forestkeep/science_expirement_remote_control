import time
import serial
import matplotlib.pyplot as plt
import math

def calculation_wind_parameters(TOF1, TOF2, TOF3, TOF4):

    distance_nord_south = 175
    distance_west_east = 175 

    tof_vy = float(TOF2) - float(TOF1)
    tof_vx = float(TOF4) - float(TOF3)
    tof_vy = tof_vy * distance_nord_south * 16000000 / float(TOF1) / float(TOF2) / 1000
    tof_vx = tof_vx * distance_west_east * 16000000 / float(TOF3) / float(TOF4) / 1000

    direction_val = math.degrees(math.atan2(tof_vx, tof_vy))
    direction_val = direction_val + 360 if direction_val < 0 else direction_val

    corr_coefX = 1 # коэффициенты поправки на акустическую тень
    corr_coefY = 1

    direction_val = direction_val + 360 if direction_val < 0 else direction_val

    speed_val = math.sqrt((corr_coefY * corr_coefY * tof_vy * tof_vy) + (corr_coefX * corr_coefX * tof_vx * tof_vx))

    return tof_vy, tof_vx, speed_val, direction_val



if __name__ == "__main__":
    number_meas = 1000000
    client = serial.Serial("COM11", 115200, timeout=1)
    file_name = "115deg.txt"
    start_time = time.time()
    
    find1 = "t1="
    find2 = "t2="
    find3 = "t3="
    find4 = "t4="

    client.write(bytes("open 1\n", "ascii"))
    time.sleep(1)
    client.write(bytes("db " + str(number_meas) + " 0 0\n", "ascii"))
    #time.sleep(1)
    #client.write(bytes("spd 34000 0 0\n", "ascii"))

    plt.ion()  
    x = []
    y_values = {find1: [], find2: [], find3: [], find4: []}
    lines = {}

    fig, ax1 = plt.subplots()
    for find in [find1, find2, find3, find4]:
        if find:
            lines[find], = ax1.plot(x, y_values[find], label=find)

    ax1.legend() 
    ax1.set_xlabel('Время')
    ax1.set_ylabel('count')
#

    ax1.grid(True)
    ax1.grid(which='both', color='gray', linestyle='-', linewidth=0.5)
    ax1.minorticks_on()
    ax1.grid(which='minor', color='black', linestyle=':', linewidth=0.5)

    start_time = time.time()

    while True:
        file = open(file_name, 'a')
        time.sleep(0.01)
        data = client.readline().decode().strip()  
        start_position = []
        #print(data)

        if data:
            #file.close()
            print(data)

            status = True
            for find in [find1, find2, find3, find4]:
                if find != False:
                    start_pos = data.find(find)
                    if start_pos == -1:
                        status = False
                        break
                    else:
                        start_position.append(start_pos)
            if status:
                    i = 0
                    k = 0
                    value = []
                    for find in [find1, find2, find3, find4]:
                        if find != False:
                            start_pos = start_position[i]
                            i+=1
                            for j in range(9):
                                #print(data[start_pos + 2: start_pos + 9-j])
                                #time.sleep(0.5)
                                try:
                                    value.append(float(data[start_pos + 3: start_pos + 9-j]))
                                    break
                                except ValueError:
                                    pass
                            y_values[find].append(value[k])
                            k+=1
                        

                    x.append(time.time() - start_time)


                    VY = value[1] - value[0]
                    VX = value[3] - value[2]
                    tof_vy, tof_vx, speed_val, direction_val = calculation_wind_parameters(value[0], value[1], value[2], value[3])
                    data = f"{value[0]}\t{value[1]}\t{value[2]}\t{value[3]}\t{round(tof_vy,2)}\t{round(tof_vx,2)}\t{round(speed_val,2)}\t{round(direction_val,2)}\t{round(time.time() - start_time, 2)}"
                    file.write(data + "\n")

                    N = 300
                    for find in [find1, find2, find3, find4]:
                        if find:
                            if len(x) > N:
                                lines[find].set_data(x[-N:], y_values[find][-N:])
                            else:
                                lines[find].set_data(x, y_values[find])

                    ax1.relim()
                    ax1.autoscale_view()


                    plt.draw()
                    plt.pause(0.01)