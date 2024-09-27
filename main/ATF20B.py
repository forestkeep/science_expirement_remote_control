import time

import serial


class ATF20B:
    def __init__(self, client) -> None:
        self.client = client

    def set_remote_control(self):
        self.client.write(f"100RS232\r\n")

    def set_local_control(self):
        self.client.write(f"100LOCAL\r\n")

    def set_freq(self, channel, frequency):
        status = True
        if isinstance(channel, str):
            channel = channel.upper()
            if channel != "A" and channel != "B":
                status = False
        else:
            status = False

        if isinstance(frequency, float) or isinstance(frequency, int):
            if frequency < 0 or frequency > 10e6:
                status = False
            else:
                # вычислить юниты в зависимости от частоты
                unit = "MHz"
        else:
            status = False

        if status:
            self.client.write(f"CH{channel}:AFREQ:{frequency}:{unit}\r\n")


if __name__ == "__main__":

    re = "rrererere"
    print(type(re))
    client = serial.Serial("COM5", 9600, timeout=1)
    dev = ATF20B(client)

    dev.set_remote_control()
    time.sleep(3)
    dev.set_freq("A", 1)


"CHA:AFREQ:1.31:MHz"


"""Code Waveform name Code Waveform name Code Waveform name Code Waveform name
00 Sine 08 Up stair 16 Exponent 24 Down stair
01 Square 09 Pos-DC 17 Logarithm 25 Po-bipulse
02 Triangle 10 Neg-DC 18 Half round 26 Ne-bipulse
03 Up ramp 11 All sine 19 Tangent 27 Trapezia
04 Down ramp 12 Half sine 20 Sin (x)/x 28 Cosine
05 Pos-pulse 13 Limit sine 21 Noise 29 Bidir-SCR
06 Neg-pulse 14 Gate sine 22 Duty 10% 30 Cardiogram
07 Tri-pulse 15 Squar-root 23 Duty 90% 31 Earthquake"""


"""
Remote command 1 Remote command 2 (without digit and unit) Inquiry command
CHA:AFREQ:1.31:MHz CHA:SQUAR CHA:?AFREQ
↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑ ↑
 1 5 2 5 3 5 4 1 5 2 1 6 2
1: Function string 2: Option string 3: Data string 4: Unit string 5 Separate character 6: Question mark
The remote command consists of the function string, the option string, the data string, the unit string, the separate character, and the
question mark. Some commands do not include the data string and the unit string. 
"""

"""The Table of Function Command
Option String Option String
Frequency of Channel A CHA Burst of Channel A ABURST
Frequency of Channel B CHB Burst of Channel B BBURST
Frequency Sweep of Channel A FSWP FSK of Channel A FSK
Amplitude Sweep of Channel A ASWP ASK of Channel A ASK
Frequency Modulation of Channel A FM PSK of Channel A PSK
External Frequency Measurement COUNT TTL TTL
Return to Local LOCAL RS232 control RS232
System SYS
The Table of the Option Command
Option String Option String Option String
CHA Waveform AWAVE Recall Parameter RECAL Hop Amplitude HOPA
CHA Offset AOFFS Measuring Frequency MEASF Hop Frequency HOPF
CHA Frequency AFREQ Software Version VER Hop Phase HOPP
CHA Attenuation AATTE Burst Count NCYCL External Trigger EXTTR
CHA Period APERD Burst Frequency BURSF External Modulation EXT
CHA Duty Cycle ADUTY Single Trigger TRIGG System Reset RESET
CHB Frequency BFREQ Single Burst ONCES Phase PHASE
CHB Harmonic Wave BHARM FM Deviation DEVIA True RMS VRMS
CHB Period BPERD Modulation Waveform MWAVE Language Setup LANG
CHB Duty Cycle BDUTY Modulation Frequency MODUF Carrier Amplitude CARRA
TTL_A Frequency TTLAF Peak-to-peak Value VPP Carrier Frequency CARRF
TTL_A Duty Cycle TTLAD Beep Sound BEEP Gate Time STROBE
TTL_B Frequency TTLBF Interval Time INTVL Stop Amplitude STOPA
TTL_B Duty Cycle TTLBD Interface Address ADDR Stop Frequency STOPF
TTL_A Trigger TTLTR Sweep Mode MODEL Auto Sweep AUTO
Step Amplitude STEPA Start Amplitude STARA Store Parameter STORE
Step Frequency STEPF Start Frequency STARF Output Switch SWITCH
CHB Waveform BWAVE
The Table of Data Command
Data String Data String
Digit 0 1 2 3 4 5 6 7 8 9 Decimal Point .
Negative Sign -
- 28 -
The Table of Unit Command
Unit String Unit String
Frequency MHz, kHz, Hz, mHz, uHz Phase DEG
Peak-to-peak Value Vpp, mVpp Attenuation dB
Time s, ms, us, ns Index No.
Harmonic TIME Percentage %
Burst Count CYCL DC Offset Vdc, mVdc
RMS Vrms, mVrms"""
