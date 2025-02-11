# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

from Devices.AKIP2404 import akip2404Class
from Devices.maisheng_power_class import maishengPowerClass
from Devices.mnipi_e7_20_class import mnipiE720Class
from Devices.relay_class import relayPr1Class
from Devices.rigol_dp832a import rigolDp832aClass
from Devices.RIGOL_DS1052E import DS1052E
from Devices.RIGOL_DS1104Z import DS1104Z
from Devices.sr830_class import sr830Class
from Devices.ATF20B import ATF20B
from Devices.matrixWps300s import matrixWps300s
from Devices.pig_in_a_poke_device import pigInAPoke

dict_device_class = {
                    "Maisheng": maishengPowerClass, 
                    "SR830": sr830Class, 
                    "PR": relayPr1Class, 
                    "DP832A": rigolDp832aClass, 
                    "АКИП-2404": akip2404Class, 
                    "E7-20MNIPI": mnipiE720Class, 
                    "DS1104Z" : DS1104Z,
                    "DS1052E" : DS1052E,
                    #"ATF20B" : ATF20B,
                    "WPS300s" : matrixWps300s,
                    "pig_in_a_poke": pigInAPoke
                    }

device_types = ["power suply", "oscilloscope", "Voltemeter", "signal generator"]

