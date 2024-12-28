
#команды блока питания

voltage_command = f"VOLT {voltage}\n"  # Устанавливает значение напряжения для выбранного канала.
voltage_query_command = "VOLT?\n"  # Запрашивает текущее значение установленного напряжения канала.
current_command = f"CURR {current}\n"  # Устанавливает значение тока для выбранного канала.
current_query_command = "CURR?\n"  # Запрашивает текущее значение измеренного тока канала.
output_on_command = f"OUTP CH{ch_num},ON\n"  # Включает выход для указанного канала.
output_off_command = f"OUTP CH{ch_num},OFF\n"  # Выключает выход для указанного канала.
measure_voltage_command = "MEAS:VOLT?\n"  # Запрашивает измеренное значение напряжения для выбранного канала.
measure_current_command = "MEAS:CURR?\n"  # Запрашивает измеренное значение тока для выбранного канала.
inst_channel_command = f"INST CH{channel}\n"  # Выбирает указанный канал для дальнейших операций.