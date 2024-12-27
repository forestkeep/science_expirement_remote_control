import numpy as np

def to_scientific_notation(value):
    return np.format_float_scientific(value, precision=5, unique=True)

# Примеры использования
number1 = 1256.1258  # дробное число
number2 = 0.0025691  # дробное число
number3 = 1256       # целое число

print(to_scientific_notation(number1))  # 1256.126
print(to_scientific_notation(number2))  # 2.569e-03
print(to_scientific_notation(number3))  # 1256.000
    


