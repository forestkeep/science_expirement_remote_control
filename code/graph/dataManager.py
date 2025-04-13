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
	device : str
	ch : str
	param: str
	par_val: np.array
	num_or_time: np.array

@dataclass
class sessionMeasData:
	data : dict

class relationData:
	def __init__(self, data_x_axis: measTimeData, data_y_axis: measTimeData):
		self.name = self.create_name(data_x_axis.device, data_x_axis.ch, data_x_axis.param, data_y_axis.device, data_y_axis.ch, data_y_axis.param)
		self.data_x_axis = data_x_axis
		self.data_y_axis = data_y_axis
		if data_x_axis.param == "time":
			self.__base_x = data_y_axis.num_or_time
			self.x_result = data_y_axis.num_or_time
			self.y_result = data_y_axis.par_val

		elif data_y_axis.param == "time":
			self.__base_x = data_x_axis.par_val
			self.x_result = data_x_axis.par_val
			self.y_result = data_x_axis.num_or_time

		else:
			self.__base_x = np.unique(np.concatenate((data_x_axis.num_or_time, data_y_axis.num_or_time)))
			self.x_result = np.interp(self.__base_x, data_x_axis.num_or_time, data_x_axis.par_val)
			self.y_result = np.interp(self.__base_x, data_y_axis.num_or_time, data_y_axis.par_val)

	def create_name(self, x_device, x_ch, x_param, y_device, y_ch, y_param):
		if x_device:
			x_device+="-"
		if x_ch:
			x_ch+="-"
		if y_device:
			y_device+="-"
		if y_ch:
			y_ch+="-"
		return f"{y_device}{y_ch}{y_param}/{x_device}{x_ch}{x_param}"

class graphDataManager( QObject ):
	list_parameters_updated = pyqtSignal(dict)
	val_parameters_added = pyqtSignal(dict)
	'''
	класс предназначен для управления данными для графиков. он менеджерит поток данных - от эксперимента или импортирует их извне.
	Рассчитывает, отправляет данные в соответсвующий график.
	'''
	def __init__(self, selector=None):
		super().__init__()
		self.selector = selector
		self.__sessions_data = {}
		self.current_id = None
		self.all_parameters = {
			"main": [],
			"osc": []
		}

		self.updated_params = {
			"main": [],
			"osc": []
		}


	def __remove_session(self, session_id: str):
		self.__sessions_data.pop(session_id)

	def change_session(self, session_id: str) -> bool:
		if session_id in self.__sessions_data.keys():
			self.current_id = session_id
			return True	
		return False

	def get_sessions_ids(self):
		return list(self.__sessions_data.keys())
	
	def get_current_session_relation_data(self, keysx: str, keysy1: list, keysy2: list, data_type: str) -> list[relationData]:
		relations_first_axis = []
		relations_second_axis = []
		if data_type not in self.__sessions_data[self.current_id].keys():
			logger.warning(f"Invalid data type {data_type} available types {list(self.__sessions_data[self.current_id].keys())}")
			return [], []
		
		if keysx and keysy1 or keysx and keysy2:
			for key in keysy1:
				buf = relationData(
					self.__sessions_data[self.current_id][data_type].data[keysx],
					self.__sessions_data[self.current_id][data_type].data[key]
				)
				relations_first_axis.append(buf)
			for key in keysy2:
				buf = relationData(
					self.__sessions_data[self.current_id][data_type].data[keysx],
					self.__sessions_data[self.current_id][data_type].data[key]
				)
				relations_second_axis.append(buf)

		return relations_first_axis, relations_second_axis
	
	def get_current_session_data(self, keysx: str, keysy1: list, keysy2: list, data_type: str) -> tuple[ measTimeData, dict, dict ]:
		returned_x = None
		returned_y1 = {}
		returned_y2 = {}


		returned_x = self.__sessions_data[self.current_id][data_type].data.get(keysx)
		for key in keysy1:
				returned_y1[key] = self.__sessions_data[self.current_id][data_type].data[key]
		for key in keysy2:
				returned_y2[key] = self.__sessions_data[self.current_id][data_type].data[key]

		return returned_x, returned_y1, returned_y2
	
	def get_current_session_id(self):
		return self.current_id
	
	def get_session_name_params(self, session_id: str = None):
		if not session_id:
			session_id = self.current_id
		return list(self.__sessions_data[session_id]['osc'].data.keys()) + list( self.__sessions_data[session_id]['main'].data.keys())

	def start_new_session(self, session_id: str, new_data = None):
		if not session_id or not isinstance(session_id, str):
			raise ValueError("Invalid session_id")

		if session_id in self.__sessions_data:
			raise ValueError(f"Session {session_id} already exists")

		previous_id = self.current_id

		try:
			self.__sessions_data[session_id] = {
				"osc": sessionMeasData(data={}), 
				"main": sessionMeasData(data={})
			}
			self.current_id = session_id

			if new_data is not None:
				status = self.add_measurement_data(new_data)
				if not status:
					self.__remove_session(session_id)
					self.change_session(previous_id)
					raise ValueError("Failed to add measurement data")

		except Exception as e:
			if session_id in self.__sessions_data.keys():
				del self.__sessions_data[session_id]
			self.current_id = previous_id
			raise

	def add_measurement_data(self, new_param: Dict[str, Any]) -> bool:
		"""
		Добавление измерительных данных с учетом различной глубины вложенности.
		
		:param new_param: Словарь с измерительными данными
		"""

		status = True
		depth = get_dict_depth(new_param)
		
		depth_handlers = {
			3: self._handle_three_level_data,
			2: self._handle_two_level_data,
			1: self._handle_one_level_data
		}
		
		handler = depth_handlers.get(depth)
		if handler:
			status = handler(new_param)
		else:
			logger.warning(f"Слишком глубокая структура данных {new_param=} не знаем, как с ней работать")
			status = False

		return status

	def _handle_three_level_data(self, data: Dict[str, Dict[str, dict[str, Any]]]) -> bool:
		for device, channels in data.items():
			for channel, values in channels.items():
				for param, value in values.items():
					ans = self._add_new_data(device=device, channel=channel, param=param, value=value)
					if not ans:
						return False
		return True

	def _handle_two_level_data(self, data: Dict[str, Dict[str, Any]])  -> bool:
		for channel, values in data.items():
			for param, value in values.items():
				ans = self._add_new_data(device=None, channel=channel, param=param, value=value)
				if not ans:
					return False
		return True

	def _handle_one_level_data(self, data: Dict[str, any])  -> bool:
		for param, value in data.items():
			ans = self._add_new_data(device=None, channel=None, param=param, value=value)
			if not ans:
				return False
		return True

	def _add_new_data(self, device: Optional[str], channel: Optional[str], param: str, value: list):
		self.updated_params = {
			"main": [],
			"osc": []
		}

		if device is None:
			device = ""
		else:
			device+="-"
		if channel is None:
			channel = ""
		else:
			channel+="-"
		key = f"{device}{channel}{param}"

		val_list = np.array(value[0])
		time_list = (np.array([i for i in range(len(val_list))]) if len(value) == 1 else np.array(value[1]))
		if len(val_list) != len(time_list):
			logger.warning(f"Длины списков параметра и времени не равны {device=} {channel=} {param=}")
			return False

		if "wavech" in param:
			existing_data = self.__sessions_data[self.current_id]['osc'].data.get(key)
			focus = self.__sessions_data[self.current_id]['osc'].data
			key_type = "osc"
		else:
			existing_data = self.__sessions_data[self.current_id]["main"].data.get(key)
			focus = self.__sessions_data[self.current_id]["main"].data
			key_type = "main"

		if existing_data is None:
			new_data = measTimeData(device=device, ch=channel, param=param, 
								par_val=val_list, num_or_time=time_list)
			focus[key] = new_data
			self.all_parameters[key_type].append(key)
			self.list_parameters_updated.emit(self.all_parameters)
		else:
			if len(existing_data.par_val) < len(value):
				existing_data.par_val = val_list
				existing_data.num_or_time = time_list
				self.updated_params[key_type].append(existing_data)
				self.val_parameters_added.emit(self.updated_params)

		return True

def get_dict_depth(d):
	if not isinstance(d, dict)  or not d:
		return 0
	return 1 + max(get_dict_depth(value) for value in d.values())

def new_param_get(parameters):
	print(parameters)

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