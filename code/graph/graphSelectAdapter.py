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


class graphSelectAdapter:
	def __init__(self, graph, selector, data_manager, type_data):
		self.graph = graph
		self.selector = selector
		self.data_manager = data_manager
		self.type_data = type_data


		self.selector.parameters_updated.connect(self.parameters_choised)
		self.selector.multiple_checked.connect(self.multiple_changed)
		self.selector.state_second_axis_changed.connect(self.state_second_axis_changed)
		self.data_manager.list_parameters_updated.connect(self.update_params)
		self.data_manager.val_parameters_added.connect(self.data_updated)

	def state_second_axis_changed(self, state):
		self.graph.set_second_axis( state )
	def multiple_changed(self, state):
		self.graph.set_multiple_mode( state )

	def update_params(self, parameters):
		'''
			этот метод вызывается менеджером данных в момент, когда набор данных изменился. Были импортированы новые, или дополнены старые.
		'''
		list_parameters = parameters[self.type_data]

		self.selector.add_parameters(list_parameters)

	def data_updated(self, parameters):
		'''вызывается контроллером данных в момент, когда какие-то из ранее добавленных данных были обновлены.
		  Например, поступило новое значение'''
		paramx, paramy1, paramy2 = self.selector.get_parameters()

		datax = {}
		datay1 = {}
		datay2 = {}
		for param in paramx:
			buf = parameters[self.type_data].get(param)
			if buf:
				datax[param] = parameters[self.type_data][param]
		for param in paramy1:
			buf = parameters[self.type_data].get(param)
			if buf:
				datay1[param] = parameters[self.type_data][param]
		for param in paramy2:
			buf = parameters[self.type_data].get(param)
			if buf:
				datay2[param] = parameters[self.type_data][param]

		self.graph.update_data(datax, datay1, datay2)

	def parameters_choised(self, param_x, param_y1, param_y2):
		'''метод вызывается селектором в моменты, когда пользователь выбрал новые параметры'''

		data_first_axis, data_second_axis = self.data_manager.get_current_session_relation_data(param_x, param_y1, param_y2, self.type_data)

		print(f"data choised: {data_first_axis=}, {data_second_axis=}")
		self.graph.set_data(data_first_axis, data_second_axis)