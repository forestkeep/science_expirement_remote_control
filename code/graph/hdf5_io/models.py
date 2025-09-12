# models.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime

# Базовый класс для всех моделей с общими полями
@dataclass
class BaseModel:
	name: str = ""
	description: Optional[str] = None

#--------------------------модели кривых и их представлений-------------------------------
# Модели для графиков

@dataclass
class GraphStyle(BaseModel):
    color: str = "#ffffff"
    line_style: QtCore.Qt.PenStyle = QtCore.Qt.SolidLine
    line_width: int = 1
    symbol: Optional[str] = None
    symbol_size: int = 1
    symbol_color: str = "#ffffff"
    fill_color: str = "#ffffff"

@dataclass
class Statistics(BaseModel):
	mean: float = 0.0
	median: float = 0.0
	std_dev: float = 0.0
	mode: float = 0.0
	count: int = 0
	min_x: float = 0.0
	max_x: float = 0.0
	min_y: float = 0.0
	max_y: float = 0.0

@dataclass
class HistoryEntry(BaseModel):
	timestamp: datetime = field(default_factory=datetime.now)
	action: str = ""
	parameters: Dict[str, Any] = field(default_factory=dict)


# Модель для параметров CurveTreeItem
@dataclass
class CurveTreeItemData(BaseModel):
	parameters: Dict[str, Any] = field(default_factory=dict)
	# Несериализуемые объекты заменены на текстовые представления
	font_info: str = "Italic,10"
	color_info: str = "#ff30ea"
	col_font_info: str = "15"

# Модель для legendName
@dataclass
class LegendNameData(BaseModel):
	full_name: str = ""
	short_name: str = ""
	custom_name: str = ""
	current_name: str = ""

# Модель для graphData
@dataclass
class GraphData(BaseModel):
	raw_data_x: np.ndarray = field(default_factory=lambda: np.empty(0))
	raw_data_y: np.ndarray = field(default_factory=lambda: np.empty(0))
	filtered_x_data: np.ndarray = field(default_factory=lambda: np.empty(0))
	filtered_y_data: np.ndarray = field(default_factory=lambda: np.empty(0))
	
	device: Optional[str] = None
	channel: Optional[str] = None
	x_name : Optional[str] = None
	y_name : Optional[str] = None
	curve_name: Optional[str] = None
	number: Optional[int] = None
	number_axis: Optional[int] = None
	
	is_draw: bool = False
	is_curve_selected: bool = False
	
	# Ссылка на tree_item как на данные
	tree_item_data: CurveTreeItemData = field(default_factory=CurveTreeItemData)

# Модель для linearData
@dataclass
class LinearData(GraphData):
	# Дополнительные поля specific to linearData
	tip: str = "linear"

# Обновленная модель Plot
@dataclass
class Plot(BaseModel):

	# Статус и стиль
	status: str = "active"
	style: GraphStyle = field(default_factory=GraphStyle)
	statistics: Statistics = field(default_factory=Statistics)
	history: List[HistoryEntry] = field(default_factory=list)
	
	# Данные из linearData
	linear_data: LinearData = field(default_factory=LinearData)
	
	# Несериализуемые объекты (заменены на текстовые представления)
	plot_obj_info: str = "PlotObject"
	parent_graph_field_info: str = "ViewBox"
	legend_field_info: str = "LegendItem"

	axis : int = 1
	
	# Параметры отображения
	is_draw: bool = False
	is_curve_selected: bool = False

	# Оси

	x_name: str = ""
	y_name: str = ""



#------------------------------------------------------------------------------------------



# Модели для настроек полей
@dataclass
class GraphFieldSettings(BaseModel):
	# Основные настройки графика
	title: str = ""
	background_color: str = "#FFFFFF"
	foreground_color: str = "#000000"
	grid_enabled: bool = True
	grid_color: str = "#CCCCCC"
	grid_alpha: float = 0.5
	
	# Настройки осей
	x_label: str = "X Axis"
	y_label: str = "Y Axis"
	x_log_mode: bool = False
	y_log_mode: bool = False
	x_auto_range: bool = True
	y_auto_range: bool = True
	x_range: Optional[Tuple[float, float]] = None
	y_range: Optional[Tuple[float, float]] = None
	
	# Настройки легенды
	legend_enabled: bool = True
	legend_position: str = "top right"  # или "top left", "bottom right", "bottom left"
	
	# Дополнительные настройки
	antialiasing: bool = True
	mouse_enabled: bool = True
	menu_enabled: bool = True

@dataclass
class OscilloscopeFieldSettings(BaseModel):
	# Основные настройки графика
	title: str = ""
	background_color: str = "#FFFFFF"
	foreground_color: str = "#000000"
	grid_enabled: bool = True
	grid_color: str = "#CCCCCC"
	grid_alpha: float = 0.5
	
	# Настройки осей
	x_label: str = "X Axis"
	y_label: str = "Y Axis"
	x_log_mode: bool = False
	y_log_mode: bool = False
	x_auto_range: bool = True
	y_auto_range: bool = True
	x_range: Optional[Tuple[float, float]] = None
	y_range: Optional[Tuple[float, float]] = None
	
	# Настройки легенды
	legend_enabled: bool = True
	legend_position: str = "top right"  # или "top left", "bottom right", "bottom left"
	
	# Дополнительные настройки
	antialiasing: bool = True
	mouse_enabled: bool = True
	menu_enabled: bool = True

@dataclass
class FieldSettings(BaseModel):
	graph_field: GraphFieldSettings = field(default_factory=GraphFieldSettings)
	oscilloscope_field: OscilloscopeFieldSettings = field(default_factory=OscilloscopeFieldSettings)
	is_second_axis_enabled: bool = False
	is_multiple_selection_enabled: bool = False

# Модели для данных
@dataclass
class OscillogramData(BaseModel):
	device: str = ""
	channel: str = ""
	parameter: str = ""
	time_values: np.ndarray = field(default_factory=lambda: np.empty(0))
	data_values: np.ndarray = field(default_factory=lambda: np.empty(0))

@dataclass
class ParameterData(BaseModel):
	device: str = ""
	channel: str = ""
	parameter: str = ""
	time_values: np.ndarray = field(default_factory=lambda: np.empty(0))
	data_values: np.ndarray = field(default_factory=lambda: np.empty(0))

@dataclass
class DataManager(BaseModel):
	oscillogram_data: Dict[str, OscillogramData] = field(default_factory=dict)
	parameter_data: Dict[str, ParameterData] = field(default_factory=dict)


# Модели для сессии
@dataclass
class SessionParameters(BaseModel):
	# Пример:
	experiment_date: Optional[datetime] = None
	operator: str = ""
	comment: str = ""
	# Добавьте другие необходимые параметры

@dataclass
class Session(BaseModel):
	parameters: SessionParameters = field(default_factory=SessionParameters)
	field_settings: FieldSettings = field(default_factory=FieldSettings)
	data_manager: DataManager = field(default_factory=DataManager)
	plots: Dict[str, Plot] = field(default_factory=dict)

# Модель файла верхнего уровня
@dataclass
class ProjectFile(BaseModel):
	version: str = "1.0"
	creation_date: datetime = field(default_factory=datetime.now)
	sessions: Dict[str, Session] = field(default_factory=dict)