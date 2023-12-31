from pymeasure.instruments.srs import SR830
from pymeasure.adapters import SerialAdapter

GET_ID = b'*IDN?\r\n'

GET_TIME_CONSTANT = b'OFLT?\r\n'

SET_GARMONIC = b'HARM1\r\n'
SET_FREQUENCY = b'FREQ{}\r\n'
STR_SET_FREQUENCY = "FREQ{}\r\n"

SET_INT_FREQUENCY_SOURCE = b'FMOD1\r\n'

STR_SET_SIN_OUT = "SLVL{}\r\n"

SET_AUTO_GAIN = b'AGAN\r\n'
SET_AUTO_APHS = b'APHS\r\n'

GET_DISPLAY_1 = b'OUTR? 1\r\n' # запрос значения с дисп. 1
GET_DISPLAY_2 = b'OUTR? 2\r\n' # запрос значения с дисп. 2

GET_SERIAL_PULL_STATUS_BYTE = b'*STB?\r\n'

def getTimeConstant(time_code) -> str:
	if time_code == 0:
		return "10 us"
	elif time_code == 1:
		return "30 us"
	elif time_code == 2:
		return "100 us"
	elif time_code == 3:
		return "300 us"
	elif time_code == 4:
		return "1 ms"
	elif time_code == 5:
		return "3 ms"
	elif time_code == 6:
		return "10 ms"
	elif time_code == 7:
		return "30 ms"
	elif time_code == 8:
		return "100 ms"
	elif time_code == 9:
		return "300 ms"
	elif time_code == 10:
		return "1 s"
	elif time_code == 11:
		return "3 s"
	elif time_code == 12:
		return "10 s"
	elif time_code == 13:
		return "30 s"
	elif time_code == 14:
		return "100 s"
	elif time_code == 15:
		return "300 s"
	elif time_code == 16:
		return "1 ks"
	elif time_code == 17:
		return "3 ks"
	elif time_code == 18:
		return "10 ks"
	elif time_code == 19:
		return "30 ks"
	else:
		return "unknown time"


def get_phase():
	b'PHAS?\r\n'
def set_phase(x):
	if x <-360 or x > 730:
		return False
	b'PHAS' + str(x) + b'\r\n'    #-360.00 ≤ x ≤ 729.99
def set_reference_sourse(x):
	if x == "ext":
		b'FMOD 0\r\n'
	else:
		b'FMOD 1\r\n'#внутренний
if __name__ == "__main__":
	device = SR830(SerialAdapter("COM10"))
	device.auto_phase()
	print(device.ask("open 1"))
	print("stop")

'''
b'FMOD \r\n'
b'FREQ \r\n'
b'RSLP \r\n'
b'HARM \r\n'
b'SLVL \r\n'
b'ISRC \r\n'
b'IGND \r\n'
b'ICPL \r\n'
b'ILIN \r\n'
b'SENS \r\n'
b'RMOD \r\n'
b'OFLT \r\n'
b'OFSL \r\n'
b'SYNC \r\n'
b'DDEF \r\n'
b'Aux \r\n' 
b'FPOP \r\n'
b'OEXP \r\n'
b'OAUX \r\n'
b'UXV \r\n'
b'OUTX \r\n'
b'OVRM \r\n'
b'KCLK \r\n'
b'ALRM \r\n'
b'SSET \r\n'
b'RSET \r\n'
b'AGAN \r\n'
b'ARSV \r\n'
b'APHS \r\n'
b'AOFF \r\n'
b'SRAT \r\n'
b'SEND \r\n'
b'TRIG \r\n'
b'TSTR \r\n'
b'STRT \r\n'
b'PAUS \r\n'
b'REST \r\n'
b'OUTP? \r\n'
b'OUTR? \r\n'
b'SNAP? \r\n'
b'OAUX? \r\n'
b'SPTS? \r\n'
b'TRCA? \r\n'
b'TRCB? \r\n'
b'TRCL? \r\n'
b'FAST \r\n'
b'STRD \r\n'
b'*RST \r\n'
b'*IDN? \r\n'
b'LOCL  \r\n'
b'OVRM  \r\n'
b'TRIG \r\n'
b'*CLS \r\n'
b'*ESE  \r\n'
b'*ESE  \r\n'
b'*ESR?  \r\n'
b'*SRE  \r\n'
b'*STB?  \r\n'
b'*PSC  \r\n'
b'*ERRE  \r\n'
b'*ERRS?  \r\n'
b'*LIAE  \r\n'
b'*LIAS?  \r\n'

'''