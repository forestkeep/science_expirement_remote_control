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

import copy
import logging
import time
import re

from PyQt5.QtWidgets import QApplication, QFileDialog

from Devices.Classes import (base_ch, base_device, ch_response_to_step,
							 not_ready_style_border, ready_style_border,
							 which_part_in_ch)
from Devices.interfase.pig_in_a_poke_window import pigInAPokeWindow

logger = logging.getLogger(__name__)

class chMeasPigPoke(base_ch):
	def __init__(self, number, device_class_name, message_broker) -> None:
		super().__init__(number, ch_type="meas", device_class_name=device_class_name, message_broker=message_broker)
		self.base_duration_step = 10
		self.dict_buf_parameters["commands"] = []
		self.dict_buf_parameters["commands_file"] = ''
		self.dict_buf_parameters["timeout_connect"] = 1000
		self.dict_buf_parameters["is_not_command"] = False
		self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)

class pigInAPoke(base_device):

	def __init__(self, name, installation_class) -> None:
		super().__init__(name, "serial", installation_class)
		self.part_ch = (
			which_part_in_ch.only_meas
		)  # указываем, из каких частей состоиит канал в данном приборе

		self.ch1_meas = chMeasPigPoke(1, self.name, self.message_broker)
		self.channels = self.create_channel_array()
		self.setting_window = pigInAPokeWindow()
		self.base_settings_window()

		# =======================прием сигналов от окна==================
		self.setting_window.download_button.clicked.connect(
			lambda: self._download_commands()
		)
		self.setting_window.command_text.textChanged.connect( lambda: self._is_correct_parameters() )
		self.setting_window.timeout_line.textChanged.connect( lambda: self._is_correct_parameters() )
		self.setting_window.check_not_command.stateChanged.connect( lambda: self._is_correct_parameters() )
		self.setting_window.num_act_label.setParent(None)
		self.setting_window.num_act_enter.setParent(None)

	@base_device.base_show_window
	def show_setting_window(self, number_of_channel):
		self.switch_channel(number=number_of_channel)
		# запрещаем исполнение функций во время инициализации
		self.key_to_signal_func = False

		# ============установка текущих параметров=======================
		if self.active_channel_meas.dict_buf_parameters["commands_file"]:
			self.setting_window.downloaded_file_lable.setText(
				str(self.active_channel_meas.dict_buf_parameters["commands_file"])
			)
		text = "\n".join(self.active_channel_meas.dict_buf_parameters["commands"])
		self.setting_window.command_text.setText(text)
		self.setting_window.timeout_line.setText(str(self.active_channel_meas.dict_buf_parameters["timeout_connect"]))

		self.setting_window.check_not_command.setChecked( self.active_channel_meas.dict_buf_parameters["is_not_command"] )

		self.key_to_signal_func = True

		self._action_when_select_trigger()
		self._is_correct_parameters()
		self.setting_window.show()

	@base_device.base_is_correct_parameters
	def _is_correct_parameters(self):
		status1 = True
		status2 = True
		if self.key_to_signal_func:
			text_timeout = self.setting_window.timeout_line.text()

			try:
				text_time = float(text_timeout)
				self.setting_window.timeout_line.setStyleSheet(ready_style_border)
			except:
				status1 = False
				self.setting_window.timeout_line.setStyleSheet(not_ready_style_border)

			text = self.setting_window.command_text.toPlainText()

			if re.fullmatch(r'[\s]*', text) and not self.setting_window.check_not_command.isChecked():
				self.setting_window.command_text.setStyleSheet(not_ready_style_border)
				status2 = False
			else:
				self.setting_window.command_text.setStyleSheet(ready_style_border)
				
		return status1 and status2
	
	def check_connect(self) -> bool:
		response = "not defined check connect"
		return response

	@base_device.base_add_parameters_from_window
	def add_parameters_from_window(self):  # менять для каждого прибора

		if self.key_to_signal_func:
			text = self.setting_window.command_text.toPlainText()
			text = text.split("\n")
			commands = []
			for command in text:
					commands.append(command)

			self.active_channel_meas.dict_buf_parameters["commands"] = commands
			self.active_channel_meas.dict_buf_parameters["commands_file"] = (
				self.setting_window.downloaded_file_lable.text()
			)

			self.active_channel_meas.dict_buf_parameters["is_not_command"] = self.setting_window.check_not_command.isChecked()


			try:
				timeoutcon = float(self.setting_window.timeout_line.text())
			except:
				timeoutcon = 1000
			self.active_channel_meas.dict_buf_parameters["timeout_connect"] = timeoutcon

	def send_signal_ok(
		self,
	):
		"вызывается только после закрытия окна настроек"
		self.add_parameters_from_window()
		# те же самые настройки, ничего не делаем
		
		self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
		self.active_channel_meas.dict_settable_parameters = copy.deepcopy(self.active_channel_meas.dict_buf_parameters)
		is_parameters_correct = True

		if self.dict_buf_parameters["COM"] == QApplication.translate("Device","Нет подключенных портов") :
			is_parameters_correct = False
		self.timer_for_scan_com_port.stop()

		if is_parameters_correct:
			is_parameters_correct = self._is_correct_parameters()

		self.installation_class.message_from_device_settings(
			name_device=self.name,
			num_channel=self.active_channel_meas.number,
			status_parameters=is_parameters_correct,
			list_parameters_device=self.dict_settable_parameters,
			list_parameters_meas=self.active_channel_meas.dict_settable_parameters,
		)

	def _download_commands(self):
		options = QFileDialog.Options()
		options |= QFileDialog.DontUseNativeDialog
		fileName, ans = QFileDialog.getOpenFileName(
			self.setting_window,
			"Load File",
			"",
			"text(*.txt)",
			options=options,
		)
		if ans == "text(*.txt)":
			self.setting_window.downloaded_file_lable.setText(fileName)
			with open(fileName) as file:
				self.setting_window.command_text.setText(file.read())

		self._is_correct_parameters()
				
	# действия перед стартом эксперимента, включить, настроить, подготовить и т.д.
	def action_before_experiment(self, number_of_channel) -> bool:

		self.switch_channel(number_of_channel)
		return True

	def action_end_experiment( self, ch ) -> bool:
		"""выключение прибора"""
		self.switch_channel(ch_name=ch.get_name())
		status = True
		return status

	def do_meas( self, ch ):
		"""выполнить команды"""
		start_time = time.perf_counter()
		parameters = [self.name + " " + str(ch.get_name())]
		if ch.get_type() == "meas":

			is_correct = True
			timeout = ch.dict_settable_parameters["timeout_connect"]
			if ch.dict_settable_parameters["is_not_command"]:
				answer = self.client.query("", timeout)
				
				if answer:
						val = [f"{''}raw=" + str(answer)]
						parameters.append(val)
						number_pattern = r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
						numbers = re.findall(number_pattern, str(answer))
						for index,nm in enumerate(numbers):
							try:
								nm = float(nm)
							except:
								logger.info(f"не удалось преобразовать {nm} в float при ответе pig_in_a_poke_device")
							val = [f"{''}{index}=" + str(nm)]
							parameters.append(val)

			else:
				for command in ch.dict_settable_parameters["commands"]:
					answer = self.client.query(command, timeout, "\n")
					if answer:
						val = [f"{command}raw=" + str(answer)]
						parameters.append(val)
						number_pattern = r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
						numbers = re.findall(number_pattern, str(answer))
						logger
						for index,nm in enumerate(numbers):
							try:
								nm = float(nm)
							except:
								logger.info(f"не удалось преобразовать {nm} в float при ответе pig_in_a_poke_device")
							val = [f"{command}{index}=" + str(nm)]
							parameters.append(val)
					else:
						val = [f"{command}=" + "fail"]
						parameters.append(val)

			if is_correct:
				ans = ch_response_to_step.Step_done
			else:
				ans = ch_response_to_step.Step_fail

			return ans, parameters, time.perf_counter() - start_time

		return ch_response_to_step.Incorrect_ch, parameters, time.perf_counter() - start_time

	def set_test_mode( self ):
		"""переводит прибор в режим теста, выдаются сырые данные от функций передачи и приема"""
		self.is_test = True

	def reset_test_mode( self ):
		self.is_test = False
