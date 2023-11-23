import minimalmodbus
import serial
from PyQt5 import QtWidgets
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
# ============================================


def Aplication():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("maisheng")
    window.setGeometry(500, 500, 200, 200)

    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    Aplication()
# ============================================

# port name, slave address (in decimal)
instrument = minimalmodbus.Instrument('COM4', 1)


instrument.serial.port                     # this is the serial port name
instrument.serial.baudrate = 9600         # Baud
instrument.serial.bytesize = 8
instrument.serial.parity = serial.PARITY_NONE
instrument.serial.stopbits = 1
instrument.serial.timeout = 0.05          # seconds

instrument.address                         # this is the slave address number
instrument.mode = minimalmodbus.MODE_RTU   # rtu or ascii mode
instrument.clear_buffers_before_each_transaction = True
print(instrument)
## Read temperature (PV = ProcessValue) ##
# Registernumber, number of decimals
temperature = instrument.read_register(43, 10)
# print(temperature)

## Change temperature setpoint (SP) ##
NEW_TEMPERATURE = 95
# Registernumber, value, number of decimals for s
# instrument.write_register(24, NEW_TEMPERATURE, 1)


print("test")
print("yes")


instrument.serial.close()
