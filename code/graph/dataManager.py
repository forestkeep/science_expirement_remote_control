# Copyright © 2025 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

from dataclasses import dataclass
from typing import Dict, Any, Optional
from PyQt5.QtCore import pyqtSignal, QObject
import logging
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class measTimeData:
	device : str = ''
	ch : str = ''
	param: str = ''
	par_val: np.array = None
	num_or_time: np.array = None

@dataclass
class sessionMeasData:
	data : dict
	spicified_data : str
	is_running : bool

class relationData:
	def __init__(self, data_x_axis: measTimeData, data_y_axis: measTimeData):
		self.x_name, self.y_name,self.name = self.create_names(data_x_axis.device, data_x_axis.ch, data_x_axis.param, data_y_axis.device, data_y_axis.ch, data_y_axis.param)
		self.data_x_axis = data_x_axis
		self.data_y_axis = data_y_axis

		if data_x_axis.param == "time" or data_x_axis.param == "numbers":
			self.__base_x = data_y_axis.num_or_time
			self.x_result = data_y_axis.num_or_time
			self.y_result = data_y_axis.par_val

		elif data_y_axis.param == "time" or data_y_axis.param == "numbers":
			self.__base_x = data_x_axis.par_val
			self.x_result = data_x_axis.par_val
			self.y_result = data_x_axis.num_or_time

		else:
			self.__base_x = np.unique(np.concatenate((data_x_axis.num_or_time, data_y_axis.num_or_time)))
			self.x_result = np.interp(self.__base_x, data_x_axis.num_or_time, data_x_axis.par_val)
			self.y_result = np.interp(self.__base_x, data_y_axis.num_or_time, data_y_axis.par_val)

	def create_names(self, x_device, x_ch, x_param, y_device, y_ch, y_param):
		x_name = f"{x_device}{x_ch}{x_param}"
		y_name = f"{y_device}{y_ch}{y_param}"
		return x_name, y_name, f"{y_name}/{x_name}"
	
class graphDataManager( QObject ):
	list_parameters_updated = pyqtSignal(dict)
	val_parameters_added = pyqtSignal(dict)
	stop_current_session = pyqtSignal()
	'''
	класс предназначен для управления данными для графиков. он менеджерит поток данных - от эксперимента или импортирует их извне.
	Рассчитывает, отправляет данные в соответсвующий график.
	'''
	def __init__(self):
		super().__init__()
		self.__sessions_data = {}
		self.name = None
		self.current_spicified_data = None#это поле показывает, по какому критерию наборы данных зависят друг от друга, либо временные метки, либо порядковый номер, в случае импорта из таблиц
		self.all_parameters = {
			"main": [],
			"osc": []
		}

		self.updated_params = {
			"main": [],
			"osc": []
		}

	def get_relation_data(self, keysx: str, keysy1: list, keysy2: list, data_type: str) -> list[relationData]:
		relations_first_axis = []
		relations_second_axis = []
		if data_type not in self.__sessions_data.keys():
			logger.warning(f"Invalid data type {data_type} available types {list(self.__sessions_data[self.name].keys())}")
			return [], []
		
		if keysx and keysy1 or keysx and keysy2:
			for key in keysy1:
				buf = relationData(
					self.__sessions_data[data_type].data[keysx],
					self.__sessions_data[data_type].data[key]
				)
				relations_first_axis.append(buf)
			for key in keysy2:
				buf = relationData(
					self.__sessions_data[data_type].data[keysx],
					self.__sessions_data[data_type].data[key]
				)
				relations_second_axis.append(buf)

		return relations_first_axis, relations_second_axis
	
	def get_session_data(self, keysx: str, keysy1: list, keysy2: list, data_type: str) -> tuple[ measTimeData, dict, dict ]:
		returned_x = None
		returned_y1 = {}
		returned_y2 = {}

		returned_x = self.__sessions_data[data_type].data.get(keysx)
		for key in keysy1:
				returned_y1[key] = self.__sessions_data[data_type].data[key]
		for key in keysy2:
				returned_y2[key] = self.__sessions_data[data_type].data[key]

		return returned_x, returned_y1, returned_y2
	
	def get_name(self):
		return self.name
	
	def get_name_params(self):
		return list(self.__sessions_data['osc'].data.keys()) + list( self.__sessions_data['main'].data.keys())

	def start_new_session(self, session_id: int, use_timestamps: bool = False, is_experiment_running: bool = False, new_data = None):
		if not session_id or not isinstance(session_id, int):
			raise ValueError("Invalid session_id")

		if use_timestamps:
			specified_data = "time"
		else:
			specified_data = "numbers"

		try:
			self.__sessions_data = {
				"osc": sessionMeasData(data={}, spicified_data=specified_data, is_running=is_experiment_running), 
				"main": sessionMeasData(data={}, spicified_data=specified_data, is_running=is_experiment_running)
			}
			self.name = session_id

			if new_data is not None:
				status = self.add_measurement_data(new_data)
				if not status:
					raise ValueError("Failed to add measurement data")

		except Exception as e:
			self.current_spicified_data = self.__sessions_data['osc'].spicified_data
			raise

		self.current_spicified_data = self.__sessions_data['osc'].spicified_data

		if use_timestamps:
			spicified_data = {	
							"time":[[],[]]	
					 		}
		else:
			spicified_data = {	
							"numbers":[[],[]]	
					 		}

		self.add_measurement_data(spicified_data)

	def is_session_running(self, session_id: str = None):
		if not session_id:
			session_id = self.name
		return self.__sessions_data['osc'].is_running
	
	def stop_session_running(self, session_id: str = None):
		if not session_id:
			session_id = self.name
		self.__sessions_data['osc'].is_running = False
		self.stop_current_session.emit()

	def add_measurement_data(self, new_param: Dict[str, Any]) -> bool:
		"""
		Добавление измерительных данных с учетом различной глубины вложенности.
		
		:param new_param: Словарь с измерительными данными
		"""

		key = self.current_spicified_data
		self.updated_params = {
			"main": {key: measTimeData(param=key)},
			"osc": {key: measTimeData(param=key)}
		}

		status = True
		depth = get_dict_depth(new_param)

		depth_handlers = {
			3: self._handle_three_level_data,
			2: self._handle_two_level_data,
			1: self._handle_one_level_data
		}
		
		handler = depth_handlers.get(depth)

		is_new_param_added = False
		is_old_param_udated = False

		if handler:
			status, is_new_param_added, is_old_param_udated = handler(new_param)
		else:
			logger.warning(f"Слишком глубокая структура данных {new_param=} не знаем, как с ней работать")
			status = False

		if is_new_param_added:
			self.list_parameters_updated.emit(self.all_parameters)

		if is_old_param_udated:
			self.val_parameters_added.emit(self.updated_params)

		return status
	
	def _handle_three_level_data(self, data: Dict[str, Dict[str, dict[str, Any]]]) -> tuple[bool, bool, bool]:
		is_new_param_added = False
		is_old_param_udated = False
		for device, channels in data.items():
			for channel, values in channels.items():
				for param, value in values.items():
					ans, is_added, is_udated = self._add_new_data(device=device, channel=channel, param=param, value=value)

					if is_added and not is_new_param_added:
						is_new_param_added = True
					if is_udated and not is_old_param_udated:
						is_old_param_udated = True
					if not ans:
						return False, is_new_param_added, is_old_param_udated
					
		return True, is_new_param_added, is_old_param_udated

	def _handle_two_level_data(self, data: Dict[str, Dict[str, Any]])  -> bool:
		is_new_param_added = False
		is_old_param_udated = False
		for channel, values in data.items():
			for param, value in values.items():
				ans, is_added, is_udated = self._add_new_data(device=None, channel=channel, param=param, value=value)

				if is_added and not is_new_param_added:
					is_new_param_added = True
				if is_udated and not is_old_param_udated:
					is_old_param_udated = True
				if not ans:
					return False, is_new_param_added, is_old_param_udated
				
		return True, is_new_param_added, is_old_param_udated

	def _handle_one_level_data(self, data: Dict[str, any])  -> bool:
		is_new_param_added = False
		is_old_param_udated = False
		for param, value in data.items():
			ans, is_added, is_udated = self._add_new_data(device=None, channel=None, param=param, value=value)

			if is_added and not is_new_param_added:
				is_new_param_added = True
			if is_udated and not is_old_param_udated:
				is_old_param_udated = True
			if not ans:
				return False, is_new_param_added, is_old_param_udated
			
		return True, is_new_param_added, is_old_param_udated

	def _add_new_data(self, device: Optional[str], channel: Optional[str], param: str, value: list) -> tuple[bool, bool, bool]:
		is_new_param_added = False
		is_old_param_udated = False
		if device is None:
			device = ""
		else:
			device+="-"
		if channel is None:
			channel = ""
		else:
			channel+="-"
		key = f"{device}{channel}{param}"

		if "wavech" not in param:
			val_list = value[0] #[ [[osc1], [osc2]], [time1, time2]]
		else:
			val_list = value[0] #[ [val1, val2], [time1, time2]]

		time_list = ([i for i in range(len(val_list))] if len(value) == 1 else value[1])
		if len(val_list) != len(time_list):
			logger.warning(f"Длины списков параметра и времени не равны {device=} {channel=} {param=} {value=}")
			print(len(val_list), len(time_list))
			return False, is_new_param_added, is_old_param_udated
		
		if "wavech" in param:
			existing_data = self.__sessions_data['osc'].data.get(key)
			focus = self.__sessions_data['osc'].data
			key_type = "osc"
		else:
			existing_data = self.__sessions_data["main"].data.get(key)
			focus = self.__sessions_data["main"].data
			key_type = "main"

		if existing_data is None:
			new_data = measTimeData(device=device, ch=channel, param=param, 
								par_val=val_list, num_or_time=time_list)
			focus[key] = new_data
			self.all_parameters[key_type].append(key)
			is_new_param_added = True
		else:
			existing_data.par_val.extend(val_list)
			existing_data.num_or_time.extend(time_list)
			self.updated_params[key_type][key] = existing_data
			is_old_param_udated = True

		return True, is_new_param_added, is_old_param_udated
	
	def decode_add_exp_parameters(self, entry, time):
			data = {}
			try:
				device, channel = entry[0].split()
			except:
				device, channel = "unknown_dev_1", "unknown_ch-1"
			parameter_pairs = entry[1:]
			status = True

			if not parameter_pairs:
				return False

			if "pig_in_a_poke" in device:
				new_pairs = []
				for index, pair in enumerate(parameter_pairs):
					new_pairs.append(pair)
				parameter_pairs = new_pairs

			data[device] = {}
			data[device][channel] = {}

			for parameter_pair in parameter_pairs:
				try:
					name, value = parameter_pair[0].split("=")
				except:
					logger.warning(f"ошибка при декодировании параметра {parameter_pair}")
					continue

				if "wavech" in name:  # oscilloscope wave
					value = value.split("|")
					buf = []
					for val in value:
						try:
							buf.append(float(val))
						except ValueError:
							logger.warning(f"не удалось преобразовать в число: {device=} {channel=} {name=} {val=}")
							continue
					value = list(buf)

				else:
					try:
						value = float(value)
					except ValueError:
						logger.debug(f"не удалось преобразовать в число: {device=} {channel=} {name=} {value=}")
						continue

				if name not in data[device][channel]:
					data[device][channel][name] = [[], []]
				data[device][channel][name][0].append(value)
				data[device][channel][name][1].append(time)

			print(data)

			return self.add_measurement_data(data)
			

def get_dict_depth(d):
	if not isinstance(d, dict)  or not d:
		return 0
	return 1 + max(get_dict_depth(value) for value in d.values())

if __name__ == "__main__":

	nested_dict = {
		'dev1': {
			'ch1': {
				'c': [[],[]]
			},
			'ch2': {}
		},
		'dev3': {
			'ch1': {
				'wavech': [[],[]]
			},
			'ch2': {}
		},
		'dev2': {'ch1': {
				'c': [[],[]]
			},
			'ch2': {}}
	}


	my_class = graphDataManager()
	my_class.start_new_session("1")
	my_class.list_parameters_updated.connect(print)
	my_class.add_measurement_data(nested_dict)
	#print(my_class.get_session_name_params())