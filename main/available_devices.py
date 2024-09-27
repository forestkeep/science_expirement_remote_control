
from AKIP2404 import akip2404Class
from maisheng_power_class import maishengPowerClass
from mnipi_e7_20_class import mnipiE720Class
from relay_class import relayPr1Class
from rigol_dp832a import rigolDp832aClass
from RIGOL_DS1052E import DS1052E
from RIGOL_DS1104Z import DS1104Z
from sr830_class import sr830Class

dict_device_class = {
                                    "Maisheng": maishengPowerClass, 
                                    "SR830": sr830Class, 
                                    "PR": relayPr1Class, 
                                    "DP832A": rigolDp832aClass, 
                                    "АКИП-2404": akip2404Class, 
                                    "E7-20MNIPI": mnipiE720Class, 
                                    "DS1104Z" : DS1104Z,
                                    "DS1052E" : DS1052E,
                                    }