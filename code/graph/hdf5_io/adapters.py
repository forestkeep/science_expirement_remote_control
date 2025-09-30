# adapters.py
from typing import Dict, List, Any
from datetime import datetime
import numpy as np

from .models import ProjectFile, Session, SessionParameters, FieldSettings, DataManager, GraphFieldSettings, OscilloscopeFieldSettings
from .models import Plot, OscillogramData, ParameterData, GraphStyle, Statistics, HistoryEntry, CurveTreeItemData, LegendNameData, GraphData, LinearData
from .utils import extract_plot_widget_settings, string_to_qfont, string_to_color
import pyqtgraph as pg
import logging
from PyQt5 import QtWidgets, QtCore, QtGui

# adapters.py
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from .models import (
	ProjectFile, Session, SessionParameters, FieldSettings,
	GraphFieldSettings, OscilloscopeFieldSettings, DataManager,
	OscillogramData, ParameterData, Plot, GraphStyle,
	Statistics, HistoryEntry
)
from ..dataManager import graphDataManager, relationData, measTimeData
from ..curve_data import linearData, LineStyle
from ..customPlotWidget import PatchedPlotWidget, axisController, axisSettings, axisStyle


logger = logging.getLogger(__name__)

class ProjectToHDF5Adapter:
	"""Адаптер для преобразования объектов ядра в модели HDF5."""
	
	def convert_project(self, core_project) -> ProjectFile:
		"""
		Преобразует объект проекта ядра в ProjectFile.
		
		Args:
			core_project: Объект проекта из ядра приложения
			
		Returns:
			ProjectFile: Модель проекта для HDF5
		"""
		# Анализируем структуру core_project и преобразуем в ProjectFile
		project_file = ProjectFile(
			name=None,
			description=None,
			version="1.0",
			creation_date=datetime.now()
		)
		
		# Преобразуем сессии
		for session_id, core_session in core_project.graph_sessions.items():
			session = self.convert_session(core_session)
			project_file.sessions[session_id] = session
			
		return project_file
	
	def convert_session(self, core_session) -> Session: #core_session: GraphSession
		"""
		Преобразует объект сессии ядра в Session.
		
		Args:
			core_session: Объект сессии из ядра приложения
			
		Returns:
			Session: Модель сессии для HDF5
		"""
		# Преобразуем менеджер данных
		data_manager = self._convert_data_manager(core_session.data_manager)

		# Преобразуем параметры сессии
		parameters = SessionParameters(
			name=core_session.session_name,
			description=core_session.description,
			experiment_date=None,
			operator=None,
			comment=None
		)

		graph_settings = extract_plot_widget_settings(core_session.graph_main.graphView)
		oscilloscope_settings = extract_plot_widget_settings(core_session.graph_wave.graphView)
		is_second_axis_enabled = core_session.select_win.second_check_box.isChecked()
		is_multiple_selection_enabled = core_session.select_win.check_miltiple.isChecked()
		
		field_settings = FieldSettings(name="test")
		field_settings.graph_field = graph_settings
		field_settings.oscilloscope_field =oscilloscope_settings
		field_settings.graph_field.is_second_axis_enabled = is_second_axis_enabled
		field_settings.graph_field.is_multiple_selection_enabled = is_multiple_selection_enabled
		
		#=============================================
		# Преобразуем графики
		
		plots = {}
		
		for plot_name, core_plot in core_session.graph_main.stack_curve.items():
			plot = self.convert_plot(core_plot)
			plots[plot_name.replace('\\', '_').replace('/', '_')] = plot
		
		
		#======================================================
		# Создаем модель сессии
		return Session(
			name=core_session.session_name,
			description="testing",
			parameters=parameters,
			field_settings=field_settings,
			data_manager=data_manager,
			plots=plots
		)
	def _convert_data_manager(self, core_manager: graphDataManager) -> DataManager:
		"""Преобразует данные измерений и осциллограмм"""

		# Получаем все данные из ядра
		core_data = core_manager.get_all_data()
		session_name = core_manager.get_name()

		data_manager = DataManager(name=session_name)
		
		# Обрабатываем осциллограммы
		osc_data = core_data.get('osc', {}).data
		for key, mtd in osc_data.items():
			oscillogram = OscillogramData(
				name=key,
				device=mtd.device,
				channel=mtd.ch,
				parameter=mtd.param,
				time_values=np.array(mtd.num_or_time),
				data_values=np.array(mtd.par_val)
			)
			data_manager.oscillogram_data[key] = oscillogram
		
		# Обрабатываем параметры
		main_data = core_data.get('main', {}).data
		for key, mtd in main_data.items():
			parameter_data = ParameterData(
				name=key,
				device=mtd.device,
				channel=mtd.ch,
				parameter=mtd.param,
				time_values=np.array(mtd.num_or_time),
				data_values=np.array(mtd.par_val)
			)
			data_manager.parameter_data[key] = parameter_data
		
		return data_manager
	
	def convert_plot(self, core_plot) -> Plot:
		"""
		Преобразует объект графика ядра в Plot.
		"""
		# Создаем объекты для вложенных данных
		style_settings = self.from_graph_item( graph_item = core_plot)
		
		# Создаем статистику на основе параметров tree_item
		stats = Statistics(
			mean=core_plot.tree_item.parameters.get('mean', 0.0),
			median=core_plot.tree_item.parameters.get('median', 0.0),
			std_dev=core_plot.tree_item.parameters.get('std', 0.0)
		)
		
		# Создаем данные для CurveTreeItem
		tree_item_data = CurveTreeItemData(
			parameters=core_plot.tree_item.parameters.copy(),
			font_info=f"Italic,{core_plot.tree_item.font.pointSize()}" if hasattr(core_plot.tree_item, 'font') else "Italic,10",
			color_info=core_plot.tree_item.foreground(1).color().name() if core_plot.tree_item.foreground(1) else "#ff30ea",
			col_font_info=f"{core_plot.tree_item.col_font.pointSize()}" if hasattr(core_plot.tree_item, 'col_font') else "15"
		)
		
		# Создаем объект GraphData
		graph_data = GraphData(
			raw_data_x=core_plot.raw_data_x,
			raw_data_y=core_plot.raw_data_y,
			filtered_x_data=core_plot.filtered_x_data,
			filtered_y_data=core_plot.filtered_y_data,
			device=core_plot.device,
			channel=core_plot.ch,
			x_name= core_plot.rel_data.x_name,
			y_name= core_plot.rel_data.y_name,
			curve_name=core_plot.curve_name,
			number=core_plot.number,
			number_axis=core_plot.number_axis,
			is_draw=core_plot.is_draw,
			is_curve_selected=core_plot.is_curve_selected,
			tree_item_data=tree_item_data,
		)
		
		# Создаем объект LinearData
		linear_data = LinearData(
			**graph_data.__dict__,  # Копируем все поля из GraphData
			tip=core_plot.tree_item.parameters.get('tip', 'linear'),
		)
		
		# Создаем и возвращаем объект Plot
		return Plot(
			status="active",  # Значение по умолчанию
			style=style_settings,
			statistics=stats,
			history=[],  # Пустая история, так как в исходном коде не видно механизма заполнения
			linear_data=linear_data,
			plot_obj_info="PlotObject",  # Заглушка для несериализуемого объекта
			parent_graph_field_info="ViewBox",  # Заглушка для несериализуемого объекта
			legend_field_info="LegendItem",  # Заглушка для несериализуемого объекта
			is_draw=core_plot.is_draw,
			is_curve_selected=core_plot.is_curve_selected,
			name=core_plot.curve_name if hasattr(core_plot, 'curve_name') else "",
			x_name= core_plot.rel_data.x_name,
			y_name= core_plot.rel_data.y_name,
			axis = core_plot.number_axis
		)
	
	def from_graph_item(self,graph_item) -> GraphStyle:
		"""Создает GraphStyle из графического элемента"""
		style_graph = graph_item.saved_style
		
		styles = {
			"Solid": 1, #QtCore.Qt.SolidLine,
			"Dash": 2, #QtCore.Qt.DashLine,
			"Dot": 3, #QtCore.Qt.DotLine,
			"DashDot": 4, #QtCore.Qt.DashDotLine
		}

		# Обратный словарь для преобразования QtStyle в строку
		rev_styles = {v: k for k, v in styles.items()}

		return GraphStyle(
			color=style_graph.color,
			line_style=rev_styles[style_graph.line_style],
			line_width=style_graph.line_width,
			symbol=style_graph.symbol,
			symbol_size=style_graph.symbol_size,
			symbol_color=style_graph.symbol_color,
			fill_color=style_graph.fill_color
		)
	
class HDF5ToProjectAdapter:
	"""Адаптер для преобразования HDF5-моделей в данные ядра"""
	
	def convert(self, project: ProjectFile, core_session):
		project.sessions = {k: project.sessions[k] for k in sorted(project.sessions.keys(), key=lambda x: int(x))}
		for session_name, session_model in project.sessions.items():
			self._convert_session(session_model, core_session)


	def _convert_session(self, session: Session, core_session):

		session_id = core_session.start_new_session(session_name = session.name)
		if not session_id:
			return
		core_manager = core_session.graph_sessions[session_id].data_manager
		self._convert_data_manager(core_manager, session.data_manager)
		core_manager.stop_session_running()

		core_session.graph_sessions[session_id].select_win.set_second_check_box(state = session.field_settings.graph_field.is_second_axis_enabled)
		core_session.graph_sessions[session_id].select_win.set_multiple_mode(state = session.field_settings.graph_field.is_multiple_selection_enabled)

		selection_x_param = None
		selection_y_first_params = []
		selection_y_second_params = []

		for plot in session.plots.values():
			axis = plot.axis
			if axis not in [1, 2]:
				logger.warning(f"Unknown axis {axis} plot{plot.name}")
				continue
			curve_obj = self.restore_curve_from_model(plot_model=plot)
			core_session.graph_sessions[session_id].graph_main.add_curve(curve_obj, type_axis="left" if axis == 1 else "right")

			if plot.is_draw:
				if not selection_x_param:
					selection_x_param = plot.x_name
				else:
					logger.warning(f"Duplicate selection parameter {plot.x_name}")

				if axis == 1:
					selection_y_first_params.append(plot.y_name)
				elif axis == 2:
					selection_y_second_params.append(plot.y_name)
				else:
					logger.warning(f"Unknown axis {axis} plot{plot.name}")
			else:
				curve_obj.delete_curve_from_graph()

		core_session.graph_sessions[session_id].select_controller.set_selections(x_param = selection_x_param, y_first_params = selection_y_first_params, y_second_params = selection_y_second_params)
		
		graphView = core_session.graph_sessions[session_id].graph_main.graphView

		self.apply_graph_settings(graphView, session.field_settings)

	def apply_graph_settings(self, graph_widget: PatchedPlotWidget, settings: FieldSettings) -> None:
		"""
		Применяет настройки к графику.
		
		Args:
			graph_widget: Объект графика PatchedPlotWidget
			settings: Настройки графика FieldSettings
		"""
		graph_settings = settings.graph_field
		
		# Основные настройки графика
		graph_widget.setTitle(graph_settings.title)
		graph_widget.setCustomBackgroundColor(color = QtGui.QColor(graph_settings.background_color))
		
		# Сетка
		graph_widget.toggleGrid(graph_settings.grid_enabled)
		if hasattr(graph_widget, 'set_grid_color'):
			graph_widget.set_grid_color(graph_settings.grid_color)
		
		# Общий стиль осей
		common_style = axisStyle(
			text_font=string_to_qfont(graph_settings.common_axis_style.text_font),
			
			tick_font=string_to_qfont(graph_settings.common_axis_style.tick_font),
			color=string_to_color(graph_settings.common_axis_style.color)
		)
		graph_widget.common_style = common_style
		
		# Настройки отдельных осей
		for axis_name, axis_settings in graph_settings.axes.items():
			if axis_name in graph_widget.axises:
				axis_controller = graph_widget.axises[axis_name]
				
				# Базовые настройки
				axis_controller.settings.label = axis_settings.label
				axis_controller.settings.is_visible = axis_settings.is_visible
				axis_controller.settings.is_inverted = axis_settings.is_inverted
				
				# Видимость оси
				if axis_settings.is_visible:
					axis_controller.show()
				else:
					axis_controller.hide()
				
				# Инвертирование
				if axis_name == 'bottom':
					graph_widget.invert_x_axis(axis_settings.is_inverted)
				elif axis_name in ['left', 'right']:
					if axis_name == 'left':
						graph_widget.invert_y_axis(axis_settings.is_inverted)
					else:
						graph_widget.invert_y2_axis(axis_settings.is_inverted)
				
				# Стиль оси
				custom_style = axisStyle(
						text_font=string_to_qfont(axis_settings.custom_style.text_font),
						tick_font=string_to_qfont(axis_settings.custom_style.tick_font),
						color=string_to_color(axis_settings.custom_style.color)
					)
				if axis_settings.is_style_customized:
					axis_controller.set_custom_style(custom_style)
				else:
					axis_controller.set_common_style(common_style)
				
				# Логарифмический режим и диапазон
				if hasattr(axis_controller, 'setLogMode'):
					axis_controller.setLogMode(axis_settings.log_mode)
				
				if not axis_settings.auto_range and axis_settings.range:
					axis_controller.setRange(*axis_settings.range)
		
		# Легенда
		if hasattr(graph_widget, 'legend'):
			graph_widget.legend.setVisible(graph_settings.legend_enabled)
			graph_widget.legend2.setVisible(graph_settings.legend_enabled)
			
			# Цвет текста легенды
			if hasattr(graph_widget, 'set_legend_color'):
				graph_widget.set_legend_color(graph_settings.legend_text_color)
		
		# Антиалиасинг
		graph_widget.setAntialiasing(graph_settings.antialiasing)


	def prepare_data_dict(self, data_items):
			# Создаем словари для каждого уровня вложенности
			level_3 = {}
			level_2 = {}
			level_1 = {}
			
			for item in data_items:
				# Формируем структуру данных [values, times]
				data_pairs = [item.data_values, item.time_values]
				
				# Распределяем по уровням в зависимости от заполненности полей
				if item.device:
					if item.device not in level_3:
						level_3[item.device] = {}
					if item.channel:
						if item.channel not in level_3[item.device]:
							level_3[item.device][item.channel] = {}
						level_3[item.device][item.channel][item.parameter] = data_pairs
					else:
						level_2[item.device] = {item.parameter: data_pairs}
				elif item.channel:
					if item.channel not in level_2:
						level_2[item.channel] = {}
					level_2[item.channel][item.parameter] = data_pairs
				else:
					level_1[item.parameter] = data_pairs
					
			return level_3, level_2, level_1

	def _convert_data_manager(self, core_manager: graphDataManager, model: DataManager):
		"""Преобразует данные измерений и осциллограмм"""

		osc_data = list(model.oscillogram_data.values())
		if osc_data:
			osc_l3, osc_l2, osc_l1 = self.prepare_data_dict(osc_data)
			for data_dict in [osc_l3, osc_l2, osc_l1]:
				if data_dict:
					core_manager.add_measurement_data(data_dict, "osc")

		# Обрабатываем параметры
		param_data = list(model.parameter_data.values())
		if param_data:
			param_l3, param_l2, param_l1 = self.prepare_data_dict(param_data)
			for data_dict in [param_l3, param_l2, param_l1]:
				if data_dict:
					core_manager.add_measurement_data(data_dict)

	def restore_curve_from_model(self, plot_model: Plot) -> linearData:
		"""Восстанавливает кривую из модели Plot"""
		# Создаем корректные measTimeData для relationData
		# Для оси X
		x_meas = measTimeData(
			device=plot_model.linear_data.device,
			ch=plot_model.linear_data.channel,
			param=plot_model.x_name,
			par_val=plot_model.linear_data.raw_data_x,
			num_or_time=np.arange(len(plot_model.linear_data.raw_data_x))
		)
		
		# Для оси Y
		y_meas = measTimeData(
			device=plot_model.linear_data.device,
			ch=plot_model.linear_data.channel,
			param=plot_model.y_name,
			par_val=plot_model.linear_data.raw_data_y,
			num_or_time=np.arange(len(plot_model.linear_data.raw_data_y))
		)
		
		# Создаем relationData с корректными данными
		rel_data = relationData(x_meas, y_meas)
		
		# Создаем базовый объект linearData
		new_data = linearData(data=rel_data)
		new_data.tree_item.change_name(plot_model.linear_data.curve_name)
		
		# Восстанавливаем основные атрибуты
		new_data.device = plot_model.linear_data.device
		new_data.channel = plot_model.linear_data.channel
		new_data.curve_name = plot_model.linear_data.curve_name
		new_data.number = plot_model.linear_data.number
		new_data.number_axis = plot_model.linear_data.number_axis
		
		# Восстанавливаем данные (уже установлены через relationData, но на всякий случай дублируем)
		new_data.raw_data_x = plot_model.linear_data.raw_data_x
		new_data.raw_data_y = plot_model.linear_data.raw_data_y
		new_data.filtered_x_data = plot_model.linear_data.filtered_x_data
		new_data.filtered_y_data = plot_model.linear_data.filtered_y_data
		
		
		# Создаем графический объект
		graph = pg.PlotDataItem(
			new_data.filtered_x_data,
			new_data.filtered_y_data,
			name=plot_model.linear_data.curve_name or f"Restored {plot_model.name}",
			symbolBrush=plot_model.style.color,
			symbol='o'
		)
		graph.setClipToView(True)
		graph.setDownsampling(auto=True, method='peak')

		line_style = self.transform_line_style(plot_model.style)
		
		# Устанавливаем графический объект
		new_data.set_plot_obj(plot_obj=graph, style=line_style)
		
		# Восстанавливаем состояние
		new_data.is_draw = plot_model.linear_data.is_draw
		new_data.is_curve_selected = plot_model.linear_data.is_curve_selected
		
		return new_data
	
	def transform_line_style(self, style: GraphStyle) -> LineStyle:
		# Создаем перо
		styles = {
			"Solid": QtCore.Qt.SolidLine,
			"Dash": QtCore.Qt.DashLine,
			"Dot": QtCore.Qt.DotLine,
			"DashDot": QtCore.Qt.DashDotLine
		}

		return LineStyle(
			color=style.color,
			line_style=styles[style.line_style],
			line_width=style.line_width,
			symbol=style.symbol,
			symbol_size=style.symbol_size,
			symbol_color=style.symbol_color,
			fill_color=style.fill_color
		)
	



