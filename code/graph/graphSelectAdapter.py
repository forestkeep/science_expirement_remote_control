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
from graph.curve_data import linearData
from graph.dataManager import relationData
from PyQt5.QtWidgets import QApplication
import logging
logger = logging.getLogger(__name__)

class graphSelectAdapter:
	def __init__(self, graph, selector, data_manager, tree_class, type_data, main_class):
		self.graph = graph
		self.selector = selector
		self.data_manager = data_manager
		self.tree_class = tree_class
		self.type_data = type_data
		self.main_class = main_class

		self.selector.parameters_updated.connect(self.parameters_choised)
		self.selector.multiple_checked.connect(self.multiple_changed)
		self.selector.state_second_axis_changed.connect(self.state_second_axis_changed)
		self.selector.numPointsChanged.connect(self.numPointsChanged)
		self.selector.showingAllPoints.connect(self.showingAllPoints)
		self.data_manager.list_parameters_updated.connect(self.update_params)
		self.data_manager.val_parameters_added.connect(self.data_updated)
		self.data_manager.stop_current_session.connect(self.stop_session)

		self.tree_class.curve_deleted.connect(self.destroy_curve)
		self.tree_class.curve_shown.connect(self.show_curve)
		self.tree_class.curve_hide.connect(self.hide_curve)
		self.tree_class.curve_reset.connect(self.reset_filters)
		self.tree_class.curve_created.connect(self.curve_created)

	def hide_curve(self, curve_data_obj: linearData):
		first_parameters = []
		second_parameters = []
		y_name = curve_data_obj.rel_data.y_name
		if y_name == "gen":
			curve_data_obj.delete_curve_from_graph()
		else:
			if curve_data_obj.number_axis == 2:
				second_parameters = [y_name]
			if curve_data_obj.number_axis == 1:
				first_parameters = [y_name]

			logger.debug(f"hide_curve {first_parameters=} {second_parameters=}")

			self.selector.clear_selections("", first_parameters, second_parameters)

	def stop_session(self):
		self.graph.stop_session()
		self.selector.stop_session()

	def destroy_curve(self, curve_data_obj: linearData):
		#self.hide_curve(curve_data_obj)
		self.graph.destroy_curve(curve_data_obj)

	def show_curve(self, curve_data_obj: linearData):
		#возможны два случая, когда кривая сгенерирована из сырых данных и когда кривая посчитана по формуле. Когда кривая посчитана по формуле, мы просто проверяем пространства и напрямую отображаем ее
		logger.debug(f"show_curve {curve_data_obj.rel_data.y_name=}")
		paramx, paramy1, paramy2 = self.selector.get_parameters()
		if paramx == curve_data_obj.rel_data.x_name:	
			y_name = curve_data_obj.rel_data.y_name
			if y_name == "gen":
				curve_data_obj.place_curve_on_graph(graph_field  = curve_data_obj.parent_graph_field,
                                                    legend_field  = curve_data_obj.legend_field,
                                                    number_axis = curve_data_obj.number_axis
                                                    )
			else:
				self.selector.set_selections("", [y_name], [y_name])
		else:
			self.main_class.show_tooltip(message = QApplication.translate( "GraphWindow", "Кривая принадлежит другому пространству") )

	def reset_filters(self, curve_data_obj: linearData):
		self.graph.reset_filters(curve_data_obj)

	def curve_created(self, data: relationData, formula:str = None, description:str = None):
		status = self.graph.create_and_place_curve(data = data)
		if not status:
			logger.warning(f"Кривая с именем {data.name} уже существует в системе")
		else:
			curve = self.graph.get_curve(data.name)
			if curve:
				blocks = {}
				if formula:
					blocks[QApplication.translate("GraphWindow","Формула")] = formula
				if description:
					blocks[QApplication.translate("GraphWindow","Описание")] = description

				if blocks:
					curve.tree_item.add_new_block( QApplication.translate("GraphWindow","Разное"), blocks)

	def numPointsChanged(self, value):
		self.graph.set_num_points(value)
		
	def showingAllPoints(self, state):
		self.graph.show_all_points(state)

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

		datax = ''
		datay1 = {}
		datay2 = {}

		buf = parameters[self.type_data].get(paramx)
		if buf:
			datax = paramx

		for param in paramy1:
			buf = parameters[self.type_data].get(param)
			if buf:
				datay1[param] = parameters[self.type_data][param]
		for param in paramy2:
			buf = parameters[self.type_data].get(param)
			if buf:
				datay2[param] = parameters[self.type_data][param]

		data_first_axis, data_second_axis = self.data_manager.get_relation_data(datax, datay1, datay2, self.type_data)

		self.graph.update_data(data_first_axis, data_second_axis, is_updated = True)

	def parameters_choised(self, param_x, param_y1, param_y2):
		'''метод вызывается селектором в моменты, когда пользователь выбрал новые параметры'''
		if param_x == "numbers":
			for key in param_y1:
				if key == "numbers":
					param_y1.remove(key)
			for key in param_y2:
				if key == "numbers":
					param_y2.remove(key)
					
		if param_x and (param_y1 or param_y2):
			data_first_axis, data_second_axis = self.data_manager.get_relation_data(param_x, param_y1, param_y2, self.type_data)

			self.graph.update_data(data_first_axis, data_second_axis)