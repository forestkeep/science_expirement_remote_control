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

import logging

from PyQt5.QtWidgets import (
	QWidget, QGridLayout, QLabel, QVBoxLayout, QCheckBox, QComboBox,
	QHBoxLayout, QStackedWidget, QSizePolicy, QApplication
)
from PyQt5.QtCore import pyqtSignal, Qt

logger = logging.getLogger(__name__)

class ChannelManager(QWidget):

	channel_toggled = pyqtSignal(str, str, str, bool)
	waveform_changed = pyqtSignal(str, str, int)
	
	def __init__(self, device_name):
		super().__init__()
		self.device_name = device_name
		self.grid_layout = QGridLayout()
		self.main_layout = QVBoxLayout(self)
		self.main_layout.addWidget(QLabel("Выберите каналы:"))
		self.main_layout.addLayout(self.grid_layout)
		
		self.checkbox_dict = {}
		self.waveform_combos = {}
		self.channels = []
		self.column_labels = {}

	def add_channel(self, channel_name, waveforms_count=0):
		if channel_name in self.channels:
			return
		
		self.channels.append(channel_name)
		self._add_channel_ui(channel_name, waveforms_count, len(self.channels) - 1)

	def update_waveforms_count(self, channel_name, new_count):
		if channel_name not in self.waveform_combos:
			raise KeyError(f"Канал '{channel_name}' не найден")
		
		combo = self.waveform_combos[channel_name]
		current_index = combo.currentIndex()
		combo.clear()
		combo.addItems([str(i) for i in range(1, new_count + 1)])
		combo.setCurrentIndex(min(current_index, new_count - 1))

	def _add_channel_ui(self, channel_name, waveforms_count, index):
		column = index // 4
		row = (index % 4) + 1
		
		if row == 1:
			hbox = QHBoxLayout()
			label1 = QLabel()
			label2 = QLabel()
			hbox.addWidget(label1)
			hbox.addWidget(label2)
			self.grid_layout.addLayout(hbox, 0, column)
			self.column_labels[column] = (label1, label2)

		hbox = QHBoxLayout()
		checkbox = QCheckBox(channel_name)
		combo = QComboBox()
		combo.addItems([str(i) for i in range(1, waveforms_count + 1)])
		
		checkbox.stateChanged.connect(
			lambda state, ch=channel_name: self._handle_channel_toggle(state, ch)
		)
		combo.currentIndexChanged.connect(
			lambda idx, ch=channel_name: self._handle_waveform_change(idx, ch)
		)
		
		hbox.addWidget(checkbox)
		hbox.addWidget(combo)
		self.grid_layout.addLayout(hbox, row, column)
		
		self.checkbox_dict[channel_name] = checkbox
		self.waveform_combos[channel_name] = combo

	def _handle_channel_toggle(self, state, channel_name):
		checked = state == Qt.Checked
		try:
			number_osc = int(self.waveform_combos[channel_name].currentText())-1
		except:
			number_osc = ""
		self.channel_toggled.emit(self.device_name, channel_name, str(number_osc), checked)

	def _handle_waveform_change(self, index, channel_name):
		checkbox = self.checkbox_dict.get(channel_name)
		if checkbox and checkbox.isChecked():
			self.waveform_changed.emit(self.device_name, channel_name, index + 1)

	def reset(self):
		while self.grid_layout.count():
			item = self.grid_layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
			elif item.layout():
				self._clear_sublayout(item.layout())
		
		self.checkbox_dict = {}
		self.waveform_combos = {}
		self.channels = []
		self.column_labels = {}

	def _clear_sublayout(self, layout):
		while layout.count():
			item = layout.takeAt(0)
			if item.widget():
				item.widget().deleteLater()
			elif item.layout():
				self._clear_sublayout(item.layout())

class OscilloscopeSelector(QWidget):

	device_selected = pyqtSignal(str)
	channel_selected = pyqtSignal(str, str, str, bool)
	waveform_selected = pyqtSignal(str, str, int)
	
	def __init__(self):
		super().__init__()
		self.devices = {}
		self.main_layout = QVBoxLayout(self)
		self._setup_ui()

	def _setup_ui(self):
		self.horizontal_layout = QHBoxLayout()
		self.device_combo = QComboBox()
		self.default_device_text = "Выберите устройство"
		self.device_combo.addItem(self.default_device_text)
		
		self.stacked_widget = QStackedWidget(self)
		self.device_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		self.device_combo.setMaximumSize(150, 20)
		self.device_combo.currentTextChanged.connect(self._handle_device_change)
		
		device_layout = QVBoxLayout()
		device_layout.addWidget(QLabel("Выберите прибор:"))
		device_layout.addWidget(self.device_combo)
		
		self.horizontal_layout.addLayout(device_layout)
		self.horizontal_layout.addWidget(self.stacked_widget)
		self.main_layout.addLayout(self.horizontal_layout)

	def add_device(self, device_name):
		if device_name in self.devices:
			return
			
		self.devices[device_name] = ChannelManager(device_name)
		self.device_combo.addItem(device_name)
		self.stacked_widget.addWidget(self.devices[device_name])
		
		if self.device_combo.findText(self.default_device_text) != -1:
			self.device_combo.removeItem(0)
		
		manager = self.devices[device_name]
		manager.channel_toggled.connect(self.channel_selected)
		manager.waveform_changed.connect(self.waveform_selected)

	def add_channel(self, device_name, channel_name):
		if device_name in self.devices:
			self.devices[device_name].add_channel(channel_name)

	def update_waveforms_count(self, device_name, channel_name, count):
		if device_name in self.devices:
			self.devices[device_name].update_waveforms_count(channel_name, count)

	def _handle_device_change(self, device_name):
		if device_name in self.devices:
			self.stacked_widget.setCurrentWidget(self.devices[device_name])
			self.device_selected.emit(device_name)

	def clear_layout(self, layout, widget_to_keep):
		for i in reversed(range(layout.count())):
			item = layout.itemAt(i)
			if item:
				widget = item.widget()
				if widget and widget != widget_to_keep:
					layout.removeWidget(widget)
					widget.deleteLater()
				elif item.layout():
					self.clear_layout(item.layout(), widget_to_keep)
					layout.removeItem(item)
					item.layout().deleteLater()


if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)
	selector = OscilloscopeSelector()
	selector.show()
	
	devices = [str(i) for i in range(1, 11)]
	
	for dev in devices:
		selector.add_device(dev)
		channels = [f"Channel {i}" for i in range(1, 11)]
		for ch in channels:
			selector.add_channel(dev, ch)
	
	sys.exit(app.exec_())

