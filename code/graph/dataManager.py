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
	def __init__(self, data1: measTimeData, data2: measTimeData):
		self.data1 = data1
		self.data2 = data2
		self.__base_x = np.unique(np.concatenate((data1.num_or_time, data2.num_or_time)))
		self.x_result = np.interp(self.__base_x, data1.num_or_time, data1.par_val)
		self.y_result = np.interp(self.__base_x, data2.num_or_time, data2.par_val)

class graphDataManager:
	'''
	класс предназначен для управления данными для графиков. он менеджерит поток данных - от эксперимента или импортирует их извне.
	Рассчитывает, отправляет данные в соответсвующий график.
	'''
	def __init__(self, selector=None):
		self.selector = selector
		self.__sessions_data = {}
		self.current_id = None

	def add_selector(self, selector):
		self.selector = selector
		self.selector.parameters_updated.connect(self.parameters_choised)

	def parameters_choised(self, param_x: str, param_y1: list, param_y2: list):
		print(param_x, param_y1, param_y2)

	def __remove_session(self, session_id: str):
		self.__sessions_data.pop(session_id)

	def change_session(self, session_id: str) -> bool:
		if session_id in self.__sessions_data.keys():
			self.current_id = session_id
			return True	
		return False

	def get_sessions_ids(self):
		return list(self.__sessions_data.keys())
	
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
		
		key = f"{device}-{channel}-{param}"

		val_list = np.array(value[0])
		time_list = (np.array([i for i in range(len(val_list))]) if len(value) == 1 else np.array(value[1]))
		if len(val_list) != len(time_list):
			logger.warning(f"Длины списков параметра и времени не равны {device=} {channel=} {param=}")
			return False

		if "wavech" in param:
			existing_data = self.__sessions_data[self.current_id]['osc'].data.get(key)
			focus = self.__sessions_data[self.current_id]['osc'].data
		else:
			existing_data = self.__sessions_data[self.current_id]["main"].data.get(key)
			focus = self.__sessions_data[self.current_id]["main"].data
		if existing_data is None:
			new_data = measTimeData(device=device, ch=channel, param=param, 
								par_val=val_list, num_or_time=time_list)
			focus[key] = new_data
		else:
			if len(existing_data.par_val) < len(value):
				existing_data.par_val = val_list
				existing_data.num_or_time = time_list

		return True

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
	my_class.add_measurement_data(nested_dict)
	print(my_class.get_session_name_params())