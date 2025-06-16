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
try:
	from curve_data import linearData
	from dataManager import relationData
except:
	from graph.curve_data import linearData
	from graph.dataManager import relationData
from PyQt5.QtWidgets import QApplication
import logging
logger = logging.getLogger(__name__)

class waveSelectAdapter:
	def __init__(self, graph, selector, data_manager, type_data, main_class):
		self.graph = graph
		self.selector = selector
		self.data_manager = data_manager
		self.type_data = type_data
		self.main_class = main_class
				
		self.current_device = None
		self.active_channels = []

		self.selector.device_selected.connect(self._handle_device_selected)
		self.selector.channel_selected.connect(self._handle_channel_selected)
		self.selector.waveform_selected.connect(self._handle_waveform_selected)
	
		self.data_manager.list_parameters_updated.connect(self.update_params)
		self.data_manager.val_parameters_added.connect(self.data_added)

	def _handle_device_selected(self, device_name: str = None):
		if device_name != self.current_device:
			self.current_device = device_name
		
	def _handle_channel_selected(self, device_name: str, channel_name: str, checked: bool):
		if self.current_device == device_name:
			if checked:
				self.active_channels.append(channel_name)
			else:
				self.active_channels.remove(channel_name)

	def _handle_waveform_selected(self, device_name: str = None, channel_name: str = None, waveform_name: str = None):
		if device_name == self.current_device:
			if channel_name in self.active_channels:
				'''запросить у менеджера данных параметры по этой кривой'''
				list_data = self.data_manager.get_filtered_data(self.type_data, device=device_name, channel=channel_name)
				step_data = self.data_manager.get_filtered_data('main', device=device_name, channel=channel_name, param='step')

				#в эксперименте мы ожидаем, что в списке будет всего один элемент с заданным прибором и каналом
				if len(list_data) == 1 and len(step_data) == 1:
					data = list_data[0]
					index = int(waveform_name)-1
					self.graph.set_data(data, step_data[0], index)

				else:
					logger.warning(f'ошибка в получении списка данных по прибору {device_name} и каналу {channel_name}, ожидается только один набор осциллограмм')

	def update_params(self, parameters):
		'''
			этот метод вызывается менеджером данных в момент, когда набор данных изменился. Были импортированы новые.
		'''
		list_parameters = parameters[self.type_data]
		logger.warning(list_parameters)
		#обновились какие-то параметры, нам нуэно запросить эти данные, выудить оттуда список каналов и количество осциллограмм
		for param in list_parameters:
			meastimedata, _, _ = self.data_manager.get_session_data( param, [], [], self.type_data)
			device = meastimedata.device
			channel = meastimedata.ch
			num_wave = len(meastimedata.par_val)
			self.selector.add_device(device)
			self.selector.add_channel(device, channel)
			self.selector.update_waveforms_count(device, channel, num_wave)

	def data_added(self, parameters):
		'''вызывается контроллером данных в момент, когда какие-то из ранее добавленных данных были обновлены.
		  Например, поступило новое значение'''
		list_parameters = parameters[self.type_data]
		for param in list_parameters.keys():
			if 'wavech' in param:
				meastimedata = list_parameters[param]
				device = meastimedata.device
				channel = meastimedata.ch
				num_wave = len(meastimedata.par_val)
				#self.selector.add_device(device)
				#self.selector.add_channel(device, channel)
				self.selector.update_waveforms_count(device, channel, num_wave)
				
