# adapters.py
from typing import Dict, List, Any
from datetime import datetime
import numpy as np

from .models import ProjectFile, Session, SessionParameters, FieldSettings, DataManager, GraphFieldSettings, OscilloscopeFieldSettings
from .models import Plot, OscillogramData, ParameterData, StyleSettings, Statistics, HistoryEntry, CurveTreeItemData, LegendNameData, GraphData, LinearData
from .utils import extract_plot_widget_settings
import pyqtgraph as pg
import logging

# adapters.py
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from .models import (
	ProjectFile, Session, SessionParameters, FieldSettings,
	GraphFieldSettings, OscilloscopeFieldSettings, DataManager,
	OscillogramData, ParameterData, Plot, StyleSettings,
	Statistics, HistoryEntry
)
from ..dataManager import graphDataManager, relationData, measTimeData
from ..curve_data import linearData	

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
		field_settings.graph_field = GraphFieldSettings(**graph_settings)
		field_settings.oscilloscope_field = OscilloscopeFieldSettings(**oscilloscope_settings)
		field_settings.is_second_axis_enabled = is_second_axis_enabled
		field_settings.is_multiple_selection_enabled = is_multiple_selection_enabled
		
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
		style_settings = StyleSettings(
			color=core_plot.saved_pen.get('color', '#FF0000') if core_plot.saved_pen else '#FF0000',
			line_width=core_plot.saved_pen.get('width', 1.0) if core_plot.saved_pen else 1.0,
			line_style="solid"  # Значение по умолчанию, так как в исходном коде не указано
		)
		
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
			saved_pen_info=f"color:{core_plot.saved_pen['color']},width:{core_plot.saved_pen['width']}" if core_plot.saved_pen else "color:#FF0000,width:1.0",
			is_draw=core_plot.is_draw,
			current_highlight=core_plot.current_highlight,
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
			current_highlight=core_plot.current_highlight,
			name=core_plot.curve_name if hasattr(core_plot, 'curve_name') else "",
			x_name= core_plot.rel_data.x_name,
			y_name= core_plot.rel_data.y_name,
			axis = core_plot.number_axis
		)
	
class HDF5ToProjectAdapter:
	"""Адаптер для преобразования HDF5-моделей в данные ядра"""
	
	def convert(self, project: ProjectFile, core_session):
		for session_name, session_model in project.sessions.items():
			self._convert_session(session_model, core_session)

		# Применяем настройки полей, если виджеты предоставлены
		'''
		for session_name, session_model in project.sessions.items():
			if self.graph_widget:
				graph_settings = session_model.field_settings.graph_field.__dict__
				#apply_plot_widget_settings(self.graph_widget, graph_settings)
			
			if self.oscilloscope_widget:
				oscilloscope_settings = session_model.field_settings.oscilloscope_field.__dict__
				#apply_plot_widget_settings(self.oscilloscope_widget, oscilloscope_settings)
		'''

	def _convert_session(self, session: Session, core_session):
		#self.print_information(session)

		session_id = core_session.start_new_session(session_name = session.name)
		if not session_id:
			print(f"Сессия не создана{session.name=}")
			return
		core_manager = core_session.graph_sessions[session_id].data_manager
		self._convert_data_manager(core_manager, session.data_manager)
		core_manager.stop_session_running()

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

			
	def print_information(self, session: Session):
		print("=" * 80)
		print("ИНФОРМАЦИЯ О СЕССИИ")
		print("=" * 80)
		
		# Основная информация о сессии
		print(f"Название: {session.name}")
		print(f"Описание: {session.description}")
		print()
		
		# Параметры сессии
		print("ПАРАМЕТРЫ СЕССИИ:")
		print(f"  Название: {session.parameters.name}")
		print(f"  Описание: {session.parameters.description}")
		if session.parameters.experiment_date:
			print(f"  Дата эксперимента: {session.parameters.experiment_date}")
		print(f"  Оператор: {session.parameters.operator}")
		print(f"  Комментарий: {session.parameters.comment}")
		print()
		
		# Настройки полей
		print("НАСТРОЙКИ ПОЛЕЙ:")
		
		# Настройки поля графиков
		print("  Графическое поле:")
		gf = session.field_settings.graph_field
		print(f"    Заголовок: {gf.title}")
		print(f"    Фон: {gf.background_color}, Передний план: {gf.foreground_color}")
		print(f"    Сетка: {'вкл' if gf.grid_enabled else 'выкл'} ({gf.grid_color}, alpha: {gf.grid_alpha})")
		print(f"    Оси: X={gf.x_label}, Y={gf.y_label}")
		print(f"    Логарифмические оси: X={gf.x_log_mode}, Y={gf.y_log_mode}")
		print(f"    Автодиапазон: X={gf.x_auto_range}, Y={gf.y_auto_range}")
		print(f"    Диапазон: X={gf.x_range}, Y={gf.y_range}")
		print(f"    Легенда: {'вкл' if gf.legend_enabled else 'выкл'}, позиция: {gf.legend_position}")
		print(f"    Сглаживание: {gf.antialiasing}, Мышь: {gf.mouse_enabled}, Меню: {gf.menu_enabled}")
		
		# Настройки поля осциллограмм
		print("  Поле осциллограмм:")
		of = session.field_settings.oscilloscope_field
		print(f"    Заголовок: {of.title}")
		print(f"    Фон: {of.background_color}, Передний план: {of.foreground_color}")
		print(f"    Сетка: {'вкл' if of.grid_enabled else 'выкл'} ({of.grid_color}, alpha: {of.grid_alpha})")
		print(f"    Оси: X={of.x_label}, Y={of.y_label}")
		print(f"    Логарифмические оси: X={of.x_log_mode}, Y={of.y_log_mode}")
		print(f"    Автодиапазон: X={of.x_auto_range}, Y={of.y_auto_range}")
		print(f"    Диапазон: X={of.x_range}, Y={of.y_range}")
		print(f"    Легенда: {'вкл' if of.legend_enabled else 'выкл'}, позиция: {of.legend_position}")
		print(f"    Сглаживание: {of.antialiasing}, Мышь: {of.mouse_enabled}, Меню: {of.menu_enabled}")
		print()
		
		# Менеджер данных
		print("ДАННЫЕ:")
		dm = session.data_manager
		print(f"  Осциллограммы: {len(dm.oscillogram_data)} записей")
		for name, data in dm.oscillogram_data.items():
			print(f"    {name}: устройство={data.device}, канал={data.channel}, "
				f"параметр={data.parameter}, точек={len(data.time_values)}")
		
		print(f"  Параметры: {len(dm.parameter_data)} записей")
		for name, data in dm.parameter_data.items():
			print(f"    {name}: устройство={data.device}, канал={data.channel}, "
				f"параметр={data.parameter}, точек={len(data.time_values)}")
		print()
		
		# Графики
		print("ГРАФИКИ:")
		print(f"  Всего графиков: {len(session.plots)}")
		
		for name, plot in session.plots.items():
			print(f"  График '{name}':")
			print(f"    Статус: {plot.status}")
			print(f"    Отображается: {'да' if plot.is_draw else 'нет'}")
			print(f"    Подсвечен: {'да' if plot.current_highlight else 'нет'}")
			
			# Информация о стиле
			print(f"    Стиль: цвет={plot.style.color}, ширина={plot.style.line_width}, "
				f"тип линии={plot.style.line_style}")
			
			# Информация о данных
			ld = plot.linear_data
			print(f"    Данные: устройство={ld.device}, канал={ld.channel}, "
				f"кривая={ld.curve_name}, точек={len(ld.raw_data_x)}")
			print(f"    Фильтрованные данные: точек={len(ld.filtered_x_data)}")
			
			# Информация о статистике
			stats = plot.statistics
			print(f"    Статистика: среднее={stats.mean:.4f}, медиана={stats.median:.4f}, "
				f"стандартное отклонение={stats.std_dev:.4f}")
			print(f"               минимум X={stats.min_x:.4f}, максимум X={stats.max_x:.4f}")
			print(f"               минимум Y={stats.min_y:.4f}, максимум Y={stats.max_y:.4f}")
			
			# История изменений
			print(f"    История: {len(plot.history)} записей")
			for i, entry in enumerate(plot.history[:3]):  # Показываем только первые 3 записи
				print(f"      {i+1}. {entry.timestamp}: {entry.action}")
			if len(plot.history) > 3:
				print(f"      ... и еще {len(plot.history) - 3} записей")
			
			print()
		
		print("=" * 80)
		print("КОНЕЦ ИНФОРМАЦИИ О СЕССИИ")
		print("=" * 80)

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
		
		# Создаем перо из StyleSettings
		pen_info = self._create_pen_from_style(plot_model.style)
		new_data.saved_pen = pen_info
		
		# Создаем графический объект
		graph = pg.PlotDataItem(
			new_data.filtered_x_data,
			new_data.filtered_y_data,
			pen=pen_info,
			name=plot_model.linear_data.curve_name or f"Restored {plot_model.name}",
			symbolPen=pen_info,
			symbolBrush=plot_model.style.color,
			symbol='o'
		)
		graph.setClipToView(True)
		graph.setDownsampling(auto=True, method='peak')
		
		# Устанавливаем графический объект
		new_data.set_plot_obj(plot_obj=graph, pen=pen_info)
		
		# Восстанавливаем состояние
		new_data.is_draw = plot_model.linear_data.is_draw
		new_data.current_highlight = plot_model.linear_data.current_highlight
		
		return new_data
	
	def _create_pen_from_style(self, style: StyleSettings) -> Dict[str, Any]:
		"""Создает параметры пера из StyleSettings"""
		return {
			"color": style.color,
			"width": style.line_width,
		}


