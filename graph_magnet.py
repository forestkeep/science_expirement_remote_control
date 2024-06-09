import time
import serial
import matplotlib.pyplot as plt


if __name__ == "__main__":

    plt.ion()  # Режим интерактивного построения графика
    x = []
    y1 = []
    y2 = []
    y3 = []

    fig, ax = plt.subplots()
    line1, = ax.plot(x, y1, label='График 1')
    line2, = ax.plot(x, y2, label='График 2')
    line3, = ax.plot(x, y3, label='График 3')

    client = serial.Serial("COM12", 9600, timeout=1)
    while True:
        data = client.readline().decode().strip()  # Читаем один байт данных
        x_start = data.find("x=")
        y_start = data.find("y=")
        z_start = data.find("z=")
        strip = ""
        if x_start:
            strip += data[x_start+2:x_start+6]

        if x_start and y_start and z_start:

            try:
                value1 = float(data[x_start+2:x_start+6])
                value2 = float(data[y_start+2:y_start+6])
                value3 = float(data[z_start+2:z_start+6])
                x.append(len(x) + 1)
                y1.append(value1)
                y2.append(value2)
                y3.append(value3)
            except:
                pass

            line1.set_data(x, y1)
            line2.set_data(x, y2)
            line3.set_data(x, y3)

            ax.relim()
            ax.autoscale_view()

            plt.draw()
            plt.pause(0.01)
