from __future__ import annotations
import logging
from typing import Any,Dict,List,Optional
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtGui import QColor
from common.color_picker import pick_color
from PyQt5.QtWidgets import(QApplication,QCheckBox,QComboBox,QDoubleSpinBox,QFormLayout,QGroupBox,QHBoxLayout,QLabel,QLineEdit,QPushButton,QScrollArea,QSpinBox,QVBoxLayout,QWidget,QSizePolicy,QTableWidget,QTableWidgetItem,QHeaderView,QToolButton,)
from..import ensure_tools_registered
from..models import ParamDescriptor,ParamType,tr_analysis
from..registry import AnalysisToolRegistry
from..presets import AnalysisPresetStore
logger=logging.getLogger(__name__)
_TR=lambda s:QApplication.translate("GraphWindow",s)
_PARAM_PREFIX_BY_TOOL={"search.peaks":"analysis.param.search.peaks","search.valleys":"analysis.param.search.valleys","fit.linear":"analysis.param.fit.linear","fit.polynomial":"analysis.param.fit.polynomial","fit.gaussian":"analysis.param.fit.gaussian","fit.lorentz":"analysis.param.fit.lorentz","diff.derivative":"analysis.param.diff","diff.integral":"analysis.param.diff","spectral.fft":"analysis.param.spectral.fft","spectral.autocorr":"analysis.param.spectral.autocorr","uncertainty.estimate":"analysis.param.uncertainty",}
class AnalysisTab(QWidget):
	def __init__(self,session,parent=None)->None:
		super().__init__(parent)
		self.session=session
		self.controller=session.analysis_controller
		self.registry=AnalysisToolRegistry.instance()
		self.presets=AnalysisPresetStore.instance()
		self.curves:List[Any]=[]
		self._param_widgets:Dict[str,QWidget]={}
		self._suppress=False
		self._suppress_unc=False
		self._last_results_signature=None
		self._collapsed_artifacts:set=set()
		self._collapsed_uncertainties:set=set()
		self._unc_live_debounce=QTimer(self)
		self._unc_live_debounce.setSingleShot(True)
		self._unc_live_debounce.setInterval(150)
		self._unc_live_debounce.timeout.connect(self._apply_uncertainty_live)
		self._build_ui()
		self.controller.tool_activated.connect(self._on_tool_activated)
		self.controller.tool_deactivated.connect(self._on_tool_deactivated)
		self.controller.artifacts_changed.connect(self._reload_artifacts)
		self.controller.tool_apply_failed.connect(self._on_tool_apply_failed)
		self.controller.tool_apply_partial.connect(self._on_tool_apply_partial)
	def _build_ui(self)->None:
		outer=QVBoxLayout(self)
		outer.setContentsMargins(0,0,0,0)
		scroll=QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		content=QWidget()
		content.setMinimumWidth(0)
		layout=QVBoxLayout(content)
		layout.setContentsMargins(4,4,4,4)
		layout.setSpacing(6)
		ensure_tools_registered()
		self.registry=AnalysisToolRegistry.instance()
		self.applied_group=QGroupBox(_TR("Применённые инструменты"))
		applied_outer=QVBoxLayout(self.applied_group)
		applied_outer.setContentsMargins(4,4,4,4)
		presets_row=QHBoxLayout()
		self.presets_combo=QComboBox()
		self.presets_combo.setMinimumWidth(0)
		self.presets_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
		self.presets_combo.setMinimumContentsLength(10)
		self.presets_combo.addItem(_TR("— пресеты —"),None)
		self._reload_presets_combo()
		self.btn_apply_preset=QPushButton(_TR("Применить"))
		self.btn_apply_preset.clicked.connect(self._apply_selected_preset)
		presets_row.addWidget(self.presets_combo,1)
		presets_row.addWidget(self.btn_apply_preset)
		applied_outer.addLayout(presets_row)
		self.btn_save_preset=QPushButton(_TR("Сохранить как пресет"))
		self.btn_save_preset.clicked.connect(self._save_preset)
		applied_outer.addWidget(self.btn_save_preset)
		self.applied_results_layout=QVBoxLayout()
		self.applied_results_layout.setContentsMargins(0,0,0,0)
		self.applied_empty_label=QLabel(_TR("Результаты отсутствуют"))
		self.applied_results_layout.addWidget(self.applied_empty_label)
		applied_outer.addLayout(self.applied_results_layout)
		layout.addWidget(self.applied_group)
		add_group=QGroupBox(_TR("Добавить новый"))
		add_layout=QVBoxLayout(add_group)
		add_layout.setContentsMargins(4,4,4,4)
		self.tool_combo=QComboBox()
		self.tool_combo.setMinimumWidth(0)
		self.tool_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
		self.tool_combo.setMinimumContentsLength(10)
		self.tool_combo.addItem(_TR("— выберите инструмент —"),None)
		_ORDER=["fit.linear","fit.polynomial","fit.gaussian","fit.lorentz","search.peaks","search.valleys","diff.derivative","diff.integral","spectral.fft","spectral.autocorr","uncertainty.estimate",]
		tools_by_id={d.tool_id:d for d in self.registry.list_all()}
		for tid in _ORDER:
			desc=tools_by_id.get(tid)
			if desc is None:
				continue
			self._add_tool_item(desc)
		for tid,desc in tools_by_id.items():
			if tid in _ORDER:
				continue
			self._add_tool_item(desc)
		self.tool_combo.currentIndexChanged.connect(self._on_tool_selected)
		add_layout.addWidget(self.tool_combo)
		layout.addWidget(add_group)
		self.active_group=QGroupBox(_TR("Активный инструмент"))
		active_layout=QVBoxLayout(self.active_group)
		active_layout.setContentsMargins(4,4,4,4)
		self.active_title=QLabel("")
		self.active_title.setWordWrap(True)
		active_layout.addWidget(self.active_title)
		self.params_form=QFormLayout()
		self.params_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
		self.params_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
		self.params_form.setLabelAlignment(Qt.AlignLeft)
		self.params_form.setFormAlignment(Qt.AlignLeft|Qt.AlignTop)
		self.params_form.setContentsMargins(0,4,0,4)
		self.params_form.setHorizontalSpacing(6)
		self.params_form.setVerticalSpacing(4)
		params_widget=QWidget()
		params_widget.setMinimumWidth(0)
		params_widget.setLayout(self.params_form)
		active_layout.addWidget(params_widget)
		self.unc_style_group=self._build_uncertainty_group()
		self.unc_style_group.setVisible(False)
		active_layout.addWidget(self.unc_style_group)
		buttons_row=QHBoxLayout()
		self.btn_apply_active=QPushButton(_TR("Применить"))
		self.btn_apply_active.setToolTip(_TR("Применить выбранный инструмент к выделенным кривым"))
		self.btn_apply_active.clicked.connect(self._apply_active_tool)
		buttons_row.addWidget(self.btn_apply_active)
		active_layout.addLayout(buttons_row)
		self.active_group.setVisible(False)
		layout.addWidget(self.active_group)
		layout.addStretch()
		scroll.setWidget(content)
		outer.addWidget(scroll)
	def _on_tool_selected(self,index:int)->None:
		tool_id=self.tool_combo.itemData(index)
		if not tool_id:
			return
		tip=self.tool_combo.itemData(index,Qt.ToolTipRole) or ""
		self.tool_combo.setToolTip(tip)
		self.controller.cancel_preview()
		self.controller.activate_tool(tool_id)
	def _param_changed(self,name:str,value:Any)->None:
		if self._suppress:
			return
		self.controller.set_preview_params({name:value})
		active=self.controller.get_active_tool()
		if active is not None and active.tool_id=="uncertainty.estimate":
			self._unc_live_debounce.start()
	def _apply_active_tool(self)->None:
		if self.controller.get_active_tool() is None:
			return
		self.controller.apply()
	def _apply_uncertainty_live(self)->None:
		active=self.controller.get_active_tool()
		if active is None or active.tool_id!="uncertainty.estimate":
			return
		try:
			self.controller.apply_uncertainty_live()
		except Exception:
			logger.exception("apply_uncertainty_live failed")
	def _show_notification(self,message:str,persistent:bool=False)->None:
		session=getattr(self,"session",None)
		if session is not None and hasattr(session,"show_tooltip"):
			try:
				session.show_tooltip(message,show_while_not_click=persistent,timeout=8000)
				return
			except Exception:
				logger.exception("_show_notification: show_tooltip failed")
		try:
			ctrl=getattr(session,"session_controller",None)if session is not None else None
			sb=getattr(ctrl,"status_bar",None)if ctrl is not None else None
			if sb is not None:
				sb.set_status(message,5000)
		except Exception:
			pass
	def _common_failure_reason(self,failures:Dict[str,str])->str:
		reasons=[str(v) for v in failures.values()if v]
		if not reasons:
			return _TR("нет данных для отображения")
		uniq=set(reasons)
		if len(uniq)==1:
			return reasons[0]
		return _TR("см. лог для подробностей")
	def _on_tool_apply_failed(self,tool_id:str,failures:dict)->None:
		failures=dict(failures or {})
		n=len(failures)
		title=self._resolve_tool_title(tool_id)if tool_id else _TR("Инструмент")
		reason=self._common_failure_reason(failures)
		if n==1:
			msg=f"{title}: {_TR('не применён')}. {reason}"
		else:
			msg=f"{title}: {_TR('не применён')} ({n} {_TR('кривых')}). {reason}"
		self._show_notification(msg,persistent=True)
		logger.warning("analysis: %s failed (%d curves): %s",tool_id,n,failures)
	def _on_tool_apply_partial(self,tool_id:str,failures:dict)->None:
		failures=dict(failures or {})
		n=len(failures)
		title=self._resolve_tool_title(tool_id)if tool_id else _TR("Инструмент")
		msg=f"{title}: {_TR('не удалось обработать ')+str(n)+_TR(' кривых')}"
		self._show_notification(msg,persistent=False)
		logger.warning("analysis: %s partial (%d curves failed): %s",tool_id,n,failures)
	def _build_uncertainty_group(self)->QGroupBox:
		g=QGroupBox(_TR("Стиль погрешностей"))
		f=QFormLayout(g)
		self.unc_mode_combo=QComboBox()
		self.unc_mode_combo.addItem(_TR("Полосы (столбики)"),"bars")
		self.unc_mode_combo.addItem(_TR("Только риски"),"caps")
		self.unc_mode_combo.addItem(_TR("Подсветка (заливка)"),"shaded")
		self.unc_mode_combo.addItem(_TR("Огибающие линии"),"line")
		self.unc_mode_combo.currentIndexChanged.connect(self._apply_uncertainty_style_live)
		f.addRow(_TR("Стиль:"),self.unc_mode_combo)
		self.unc_color_btn=QPushButton(_TR("Авто"))
		self.unc_color_btn.clicked.connect(self._choose_unc_color)
		f.addRow(_TR("Цвет:"),self.unc_color_btn)
		self.unc_auto_check=QCheckBox(_TR("Брать цвет кривой"))
		self.unc_auto_check.setChecked(True)
		self.unc_auto_check.stateChanged.connect(self._apply_uncertainty_style_live)
		f.addRow(self.unc_auto_check)
		self.unc_width_spin=QSpinBox()
		self.unc_width_spin.setRange(1,10)
		self.unc_width_spin.setValue(1)
		self.unc_width_spin.setToolTip(_TR("Толщина линий погрешностей, px"))
		self.unc_width_spin.valueChanged.connect(self._apply_uncertainty_style_live)
		f.addRow(_TR("Толщина:"),self.unc_width_spin)
		self.unc_alpha_spin=QSpinBox()
		self.unc_alpha_spin.setRange(0,100)
		self.unc_alpha_spin.setValue(70)
		self.unc_alpha_spin.setSuffix(" %")
		self.unc_alpha_spin.setToolTip(_TR("Плотность (100 % — полностью непрозрачно)"))
		self.unc_alpha_spin.valueChanged.connect(self._apply_uncertainty_style_live)
		f.addRow(_TR("Плотность:"),self.unc_alpha_spin)
		self.unc_cap_spin=QSpinBox()
		self.unc_cap_spin.setRange(0,40)
		self.unc_cap_spin.setValue(6)
		self.unc_cap_spin.setSuffix(" px")
		self.unc_cap_spin.setToolTip(_TR("Длина горизонтальных рисок на концах (0 — без рисок)"))
		self.unc_cap_spin.valueChanged.connect(self._apply_uncertainty_style_live)
		f.addRow(_TR("Длина рисок:"),self.unc_cap_spin)
		return g
	@staticmethod
	def _color_from_btn(btn,fallback:str="#ffffff")->str:
		css=btn.styleSheet() or ""
		for token in css.split(";"):
			token=token.strip()
			if token.startswith("background-color"):
				_,_,val=token.partition(":")
				val=val.strip()
				if val:
					return val
		return fallback
	@staticmethod
	def _set_btn_color(btn,color:str)->None:
		btn.setStyleSheet(f"background-color: {color};")
	def _load_uncertainty_style_for_active(self)->None:
		from graphs.analysis.uncertainty import normalize_uncertainty_style
		active=self.controller.get_active_tool()
		if active is None:
			return
		style:Dict[str,Any]={}
		if active.sources:
			curve=self.session.graph_main.get_curve(active.sources[0].root_name)
			if curve is not None:
				store=getattr(curve,"store",None)
				if store is not None:
					style=dict(getattr(store,"uncertainty_style",{}) or {})
					if not style and getattr(store,"uncertainty_records",None):
						style=dict(store.uncertainty_records[0].style or {})
		style=normalize_uncertainty_style(style)
		self._suppress_unc=True
		try:
			idx=self.unc_mode_combo.findData(style.get("mode","bars"))
			if idx>=0:
				self.unc_mode_combo.setCurrentIndex(idx)
			color=style.get("color","auto")
			auto=( not color) or (color=="auto")
			self.unc_auto_check.setChecked(auto)
			self.unc_color_btn.setEnabled( not auto)
			if auto:
				self.unc_color_btn.setText(_TR("Авто"))
				self._set_btn_color(self.unc_color_btn,"#cccccc")
			else:
				self.unc_color_btn.setText(str(color))
				self._set_btn_color(self.unc_color_btn,str(color))
			self.unc_width_spin.setValue(int(style.get("width",1)))
			self.unc_alpha_spin.setValue(int(round(int(style.get("alpha",180))/255*100)))
			self.unc_cap_spin.setValue(int(style.get("cap_size",6)))
		finally:
			self._suppress_unc=False
	def _apply_uncertainty_style_live(self,*_args)->None:
		if self._suppress_unc:
			return
		active=self.controller.get_active_tool()
		if active is None or active.tool_id!="uncertainty.estimate":
			return
		from graphs.analysis.uncertainty import normalize_uncertainty_style
		auto=self.unc_auto_check.isChecked()
		color="auto"if auto else self._color_from_btn(self.unc_color_btn,"#cccccc")
		alpha=int(round(self.unc_alpha_spin.value()/100.0*255))
		style=normalize_uncertainty_style({"mode":self.unc_mode_combo.currentData() or "bars","color":color,"width":int(self.unc_width_spin.value()),"alpha":alpha,"cap_size":int(self.unc_cap_spin.value()),})
		for snap in active.sources:
			try:
				self.controller.set_uncertainty_style(snap.root_name,style)
			except Exception:
				logger.exception("set_uncertainty_style failed for %s",snap.root_name)
	def _choose_unc_color(self)->None:
		current=self._color_from_btn(self.unc_color_btn,"#cccccc")
		def on_selected(color:QColor)->None:
			name=color.name()
			self._set_btn_color(self.unc_color_btn,name)
			self.unc_color_btn.setText(name)
			if self.unc_auto_check.isChecked():
				self._suppress_unc=True
				try:
					self.unc_auto_check.setChecked(False)
				finally:
					self._suppress_unc=False
			self.unc_color_btn.setEnabled(True)
			self._apply_uncertainty_style_live()
		pick_color(self.unc_color_btn,current,on_selected,self)
	def set_curves(self,curves:List[Any])->None:
		self.curves=[c for c in curves if hasattr(c,"rel_data")]
		self._last_results_signature=None
		self._reload_artifacts()
		if hasattr(self,"scope_label"):
			names=[c.curve_name for c in self.curves]
			self.scope_label.setText(", ".join(names)if names else"—")
	@staticmethod
	def _params_signature(params)->str:
		try:
			return repr(sorted((str(k),str(v))for k,v in (params or {}).items()))
		except Exception:
			return ""
	def _reload_artifacts(self)->None:
		artifacts=[]
		uncertainty_entries=[]
		for curve in self.curves:
			root=curve.rel_data.root_name
			artifacts.extend(self.controller.get_artifacts_for_curve(root))
			store=getattr(curve,"store",None)
			if store is not None:
				for rec in getattr(store,"uncertainty_records",[]) or []:
					uncertainty_entries.append((curve,rec))
		sig=(tuple(c.rel_data.root_name for c in self.curves),tuple((a.id,bool(a.visibility),int(a.order_index),self._params_signature(a.params)) for a in artifacts),tuple((c.rel_data.root_name,r.id,r.id in (getattr(c.store,"active_uncertainty_ids",set()) or set())) for c,r in uncertainty_entries),)
		if sig==self._last_results_signature:
			return
		self._last_results_signature=sig
		while self.applied_results_layout.count():
			item=self.applied_results_layout.takeAt(0)
			w=item.widget()
			if w is not None:
				w.deleteLater()
		total=len(artifacts)+len(uncertainty_entries)
		if total==0:
			self.applied_results_layout.addWidget(QLabel(_TR("Результаты отсутствуют")))
		else:
			for art in artifacts:
				self.applied_results_layout.addWidget(self._build_artifact_row(art))
			for curve,rec in uncertainty_entries:
				self.applied_results_layout.addWidget(self._build_uncertainty_row(curve,rec))
	def _reload_presets_combo(self)->None:
		self.presets_combo.blockSignals(True)
		try:
			current=self.presets_combo.currentData()
			self.presets_combo.clear()
			self.presets_combo.addItem(_TR("— пресеты —"),None)
			for p in self.presets.all():
				self.presets_combo.addItem(p.name or "(без имени)",p.id)
			if current:
				idx=self.presets_combo.findData(current)
				if idx>=0:
					self.presets_combo.setCurrentIndex(idx)
		finally:
			self.presets_combo.blockSignals(False)
	def _apply_selected_preset(self)->None:
		preset_id=self.presets_combo.currentData()
		if not preset_id:
			return
		preset=self.presets.get(preset_id)
		if preset is None:
			return
		n=self.controller.apply_preset(preset,sources=None)
		if n==0:
			from PyQt5.QtWidgets import QMessageBox
			QMessageBox.information(self,_TR("Применить пресет"),_TR("Не удалось применить пресет: нет выделенных кривых."),)
		else:
			self._reload_artifacts()
	def _save_preset(self)->None:
		artifacts:List[Dict[str,Any]]=[]
		seen=set()
		for curve in self.curves:
			root=curve.rel_data.root_name
			for art in self.controller.get_artifacts_for_curve(root):
				key=(art.tool_id,tuple(sorted((art.params or {}).items())))
				if key in seen:
					continue
				seen.add(key)
				artifacts.append({"tool_id":art.tool_id,"params":dict(art.params or {}),})
		if not artifacts:
			from PyQt5.QtWidgets import QMessageBox
			QMessageBox.information(self,_TR("Сохранить пресет"),_TR("Нет применённых инструментов для сохранения."),)
			return
		from PyQt5.QtWidgets import QInputDialog
		name,ok=QInputDialog.getText(self,_TR("Сохранить пресет"),_TR("Имя пресета:"))
		if not ok or not name.strip():
			return
		self.presets.register(name.strip(),artifacts)
		self._reload_presets_combo()
	def _make_copy_button(self,on_click)->QPushButton:
		btn=QPushButton("📋")
		btn.setFixedWidth(28)
		btn.setToolTip(_TR("Скопировать в буфер обмена"))
		btn.setCursor(Qt.PointingHandCursor)
		btn.clicked.connect(on_click)
		return btn
	def _flash_copy_button(self,button:QPushButton)->None:
		if button is None:
			return
		original=button.text()
		button.setText("✓")
		button.setToolTip(_TR("Скопировано"))
		QTimer.singleShot(1200,lambda b=button,o=original:b.setText(o))
	def _copy_text(self,text:str,button:Optional[QPushButton]=None)->None:
		QApplication.clipboard().setText(text)
		self._flash_copy_button(button)
	def _format_artifact_text(self,artifact)->str:
		lines:List[str]=[]
		lines.append(self._resolve_tool_title(artifact.tool_id))
		desc=getattr(artifact,"description","")
		if desc:
			lines.append(desc)
		lines.append("")
		params=dict(artifact.params or {})
		if params:
			lines.append(_TR("Параметры инструмента:"))
			for k,v in params.items():
				lines.append(f"{self._param_title(artifact.tool_id,str(k))}\t{self._format_value(v)}")
			lines.append("")
		payload=getattr(artifact,"payload",None)
		kind=getattr(payload,"kind",None)
		if kind=="annotation":
			points=list(getattr(payload,"points",[]) or [])
			if points:
				lines.append(_TR("Найденные точки:"))
				lines.append("\t".join([_TR("№"),"X","Y",_TR("Индекс"),_TR("Значимость"),_TR("Полуширина (FWHM)")]))
				for i,pt in enumerate(points):
					idx=pt.get("index")
					lines.append("\t".join([str(i+1),self._format_value(pt.get("x")),self._format_value(pt.get("y")),str(int(idx))if idx is not None else"—",self._format_value(pt.get("prominence")),self._format_value(pt.get("width")),]))
			else:
				lines.append(_TR("Точки не найдены"))
		elif kind in ("overlay","attached","domain"):
			metrics=self._read_payload_metrics(payload)
			if not metrics:
				metrics=dict(getattr(artifact,"extras",{}).get("metrics") or {})
			if metrics:
				lines.append(_TR("Метрики качества аппроксимации:"))
				metric_rows=[("n",_TR("Точек (n)")),("dof",_TR("Степеней свободы (dof)")),("n_params",_TR("Параметров модели (k)")),("r2","R²"),("adj_r2",_TR("Скорр. R²")),("rmse","RMSE"),("std_err",_TR("Ст. ошибка остатков")),("chi2_red","χ²_red"),("sse","SSE"),("sst","SST"),]
				for key,title in metric_rows:
					if key in metrics and metrics[key]is not None:
						lines.append(f"{title}\t{self._format_metric_value(metrics[key])}")
				coeffs=dict(metrics.get("params") or {})
				if coeffs:
					lines.append("")
					lines.append(_TR("Коэффициенты аппроксимации:"))
					names=list(metrics.get("param_names") or coeffs.keys())
					for k in names:
						lines.append(f"{k}\t{self._format_metric_value(coeffs.get(k))}")
				lines.append("")
			xs=getattr(payload,"x",[]) or []
			lines.append(_TR("Наборов данных: ")+f"{len(xs)}")
		return "\n".join(lines)
	def _format_uncertainty_text(self,record)->str:
		lines:List[str]=[]
		method=str(getattr(record,"method","std"))
		method_label=tr_analysis(f"analysis.param.uncertainty.method.{method}",method,)
		lines.append(f"{_TR('Погрешности точек')} ({method_label})")
		lines.append("")
		params=dict(getattr(record,"params",{}) or {})
		params["method"]=method
		if params:
			lines.append(_TR("Параметры инструмента:"))
			for k,v in params.items():
				if k=="method":
					title=_TR("Метод")
					value=method_label
				else:
					title=self._param_title("uncertainty.estimate",str(k))
					value=self._format_value(v)
				lines.append(f"{title}\t{value}")
		yerr=getattr(record,"y_err",None)
		if yerr is not None:
			try:
				lines.append("")
				lines.append(_TR("Точек с погрешностью: ")+f"{len(yerr)}")
			except TypeError:
				pass
		return "\n".join(lines)
	def _build_uncertainty_row(self,curve,record)->QWidget:
		wrapper=QWidget()
		vl=QVBoxLayout(wrapper)
		vl.setContentsMargins(0,0,0,0)
		vl.setSpacing(0)
		header=QWidget()
		hl=QHBoxLayout(header)
		hl.setContentsMargins(4,2,4,2)
		key=str(getattr(record,"id",""))
		expanded=key not in self._collapsed_uncertainties
		toggle=QToolButton()
		toggle.setCheckable(True)
		toggle.setChecked(expanded)
		toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
		toggle.setAutoRaise(True)
		toggle.setFixedSize(18,18)
		hl.addWidget(toggle)
		method_label=tr_analysis(f"analysis.param.uncertainty.method.{record.method}",str(record.method),)
		cb=QCheckBox(f"{_TR('Погрешности точек')} ({method_label})")
		active_ids=getattr(curve.store,"active_uncertainty_ids",set()) or set()
		cb.setChecked(record.id in active_ids)
		cb.stateChanged.connect(lambda st,rn=curve.rel_data.root_name,rid=record.id:self.controller.set_uncertainty_visible(rn,rid,st!=0))
		hl.addWidget(cb,1)
		copy_btn=QPushButton("📋")
		copy_btn.setFixedWidth(28)
		copy_btn.setToolTip(_TR("Скопировать в буфер обмена"))
		copy_btn.setCursor(Qt.PointingHandCursor)
		copy_btn.clicked.connect(lambda _c=False,r=record,b=copy_btn:self._copy_text(self._format_uncertainty_text(r),b))
		hl.addWidget(copy_btn)
		del_btn=QPushButton("×")
		del_btn.setFixedWidth(24)
		del_btn.clicked.connect(lambda _,rn=curve.rel_data.root_name,rid=record.id:self.controller.remove_uncertainty(rn,rid))
		hl.addWidget(del_btn)
		vl.addWidget(header)
		details=self._build_uncertainty_details(record)
		details.setVisible(expanded)
		vl.addWidget(details)
		def _on_toggle(checked:bool)->None:
			details.setVisible(bool(checked))
			toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
			if checked:
				self._collapsed_uncertainties.discard(key)
			else:
				self._collapsed_uncertainties.add(key)
		toggle.toggled.connect(_on_toggle)
		return wrapper
	def _build_uncertainty_details(self,record)->QWidget:
		w=QWidget()
		vl=QVBoxLayout(w)
		vl.setContentsMargins(22,2,4,6)
		vl.setSpacing(4)
		params=dict(getattr(record,"params",{}) or {})
		method=str(getattr(record,"method","std"))
		params["method"]=method
		params_label=QLabel(_TR("Параметры инструмента:"))
		params_label.setStyleSheet("color: #aaa; font-size: 11px;")
		vl.addWidget(params_label)
		table=QTableWidget()
		table.setColumnCount(2)
		table.setHorizontalHeaderLabels([_TR("Параметр"),_TR("Значение")])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		table.verticalHeader().setVisible(False)
		table.setEditTriggers(QTableWidget.NoEditTriggers)
		table.setSelectionMode(QTableWidget.NoSelection)
		table.setRowCount(len(params))
		for i,(k,v) in enumerate(params.items()):
			if k=="method":
				title=_TR("Метод")
				value=tr_analysis(f"analysis.param.uncertainty.method.{v}",str(v),)
			else:
				title=self._param_title("uncertainty.estimate",str(k))
				value=self._format_value(v)
			table.setItem(i,0,QTableWidgetItem(title))
			table.setItem(i,1,QTableWidgetItem(value))
		table.resizeRowsToContents()
		row_h=table.verticalHeader().defaultSectionSize() if table.rowCount() else 20
		table.setMaximumHeight(min(260, max(60, table.rowCount()*max(20,row_h)+28)))
		vl.addWidget(table)
		yerr=getattr(record,"y_err",None)
		if yerr is not None:
			try:
				n=len(yerr)
				info=QLabel(_TR("Точек с погрешностью: ")+f"{n}")
				info.setStyleSheet("color: #888; font-size: 11px;")
				vl.addWidget(info)
			except TypeError:
				pass
		return w
	def _build_artifact_row(self,artifact)->QWidget:
		wrapper=QWidget()
		vl=QVBoxLayout(wrapper)
		vl.setContentsMargins(0,0,0,0)
		vl.setSpacing(0)
		header=QWidget()
		hl=QHBoxLayout(header)
		hl.setContentsMargins(4,2,4,2)
		expanded=artifact.id not in self._collapsed_artifacts
		toggle=QToolButton()
		toggle.setCheckable(True)
		toggle.setChecked(expanded)
		toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
		toggle.setAutoRaise(True)
		toggle.setFixedSize(18,18)
		hl.addWidget(toggle)
		cb=QCheckBox(self._resolve_tool_title(artifact.tool_id))
		cb.setChecked(artifact.visibility)
		cb.stateChanged.connect(lambda st,aid=artifact.id:self.controller.set_artifact_visibility(aid,st!=0))
		hl.addWidget(cb,1)
		copy_btn=QPushButton("📋")
		copy_btn.setFixedWidth(28)
		copy_btn.setToolTip(_TR("Скопировать в буфер обмена"))
		copy_btn.setCursor(Qt.PointingHandCursor)
		copy_btn.clicked.connect(lambda _c=False,a=artifact,b=copy_btn:self._copy_text(self._format_artifact_text(a),b))
		hl.addWidget(copy_btn)
		del_btn=QPushButton("×")
		del_btn.setFixedWidth(24)
		del_btn.clicked.connect(lambda _,aid=artifact.id:self.controller.remove_artifact(aid))
		hl.addWidget(del_btn)
		vl.addWidget(header)
		details=self._build_artifact_details(artifact)
		details.setVisible(expanded)
		vl.addWidget(details)
		def _on_toggle(checked:bool)->None:
			details.setVisible(bool(checked))
			toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
			if checked:
				self._collapsed_artifacts.discard(artifact.id)
			else:
				self._collapsed_artifacts.add(artifact.id)
		toggle.toggled.connect(_on_toggle)
		return wrapper
	def _build_artifact_details(self,artifact)->QWidget:
		w=QWidget()
		vl=QVBoxLayout(w)
		vl.setContentsMargins(22,2,4,6)
		vl.setSpacing(4)
		desc=getattr(artifact,"description","")
		if desc:
			desc_label=QLabel(desc)
			desc_label.setStyleSheet("color: #ccc; font-size: 11px;")
			desc_label.setWordWrap(True)
			vl.addWidget(desc_label)
		params=dict(artifact.params or {})
		if params:
			params_label=QLabel(_TR("Параметры инструмента:"))
			params_label.setStyleSheet("color: #aaa; font-size: 11px;")
			vl.addWidget(params_label)
			table=QTableWidget()
			table.setColumnCount(2)
			table.setHorizontalHeaderLabels([_TR("Параметр"),_TR("Значение")])
			table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
			table.verticalHeader().setVisible(False)
			table.setEditTriggers(QTableWidget.NoEditTriggers)
			table.setSelectionMode(QTableWidget.NoSelection)
			table.setRowCount(len(params))
			for i,(k,v) in enumerate(params.items()):
				title=self._param_title(artifact.tool_id,str(k))
				table.setItem(i,0,QTableWidgetItem(title))
				table.setItem(i,1,QTableWidgetItem(self._format_value(v)))
			table.resizeRowsToContents()
			row_h=table.verticalHeader().defaultSectionSize() if table.rowCount() else 20
			table.setMaximumHeight(min(260, max(60, table.rowCount()*max(20,row_h)+28)))
			vl.addWidget(table)
		payload=getattr(artifact,"payload",None)
		kind=getattr(payload,"kind",None)
		if kind=="annotation":
			points=list(getattr(payload,"points",[]) or [])
			if points:
				peaks_label=QLabel(_TR("Найденные точки:")+f" {len(points)}")
				peaks_label.setStyleSheet("color: #aaa; font-size: 11px;")
				vl.addWidget(peaks_label)
				vl.addWidget(self._build_peaks_table(points))
			else:
				empty=QLabel(_TR("Точки не найдены"))
				empty.setStyleSheet("color: #888; font-size: 11px;")
				vl.addWidget(empty)
		elif kind in ("overlay","attached","domain"):
			metrics=self._read_payload_metrics(payload)
			if not metrics:
				metrics=dict(getattr(artifact,"extras",{}).get("metrics") or {})
			if metrics:
				metrics_label=QLabel(_TR("Метрики качества аппроксимации:"))
				metrics_label.setStyleSheet("color: #aaa; font-size: 11px;")
				vl.addWidget(metrics_label)
				vl.addWidget(self._build_metrics_table(metrics))
				coeffs=dict(metrics.get("params") or {})
				if coeffs:
					names=list(metrics.get("param_names") or coeffs.keys())
					coeffs_label=QLabel(_TR("Коэффициенты аппроксимации:"))
					coeffs_label.setStyleSheet("color: #aaa; font-size: 11px;")
					vl.addWidget(coeffs_label)
					vl.addWidget(self._build_coeff_table(coeffs,names))
			xs=getattr(payload,"x",[]) or []
			info=QLabel(_TR("Наборов данных: ")+f"{len(xs)}")
			info.setStyleSheet("color: #888; font-size: 11px;")
			vl.addWidget(info)
		return w
	@staticmethod
	def _read_payload_metrics(payload)->dict:
		kind=getattr(payload,"kind",None)
		raw=None
		if kind=="overlay":
			sh=getattr(payload,"style_hint",{}) or {}
			raw=sh.get("metrics")
		elif kind in ("attached","domain"):
			ex=getattr(payload,"extras",{}) or {}
			raw=ex.get("metrics")
		if isinstance(raw,dict):
			return raw
		if isinstance(raw,str):
			try:
				import json
				parsed=json.loads(raw)
				if isinstance(parsed,dict):
					return parsed
			except Exception:
				pass
		return {}
	def _build_metrics_table(self,metrics:dict)->QTableWidget:
		rows=[("n",_TR("Точек (n)")),("dof",_TR("Степеней свободы (dof)")),("n_params",_TR("Параметров модели (k)")),("r2","R²"),("adj_r2",_TR("Скорр. R²")),("rmse","RMSE"),("std_err",_TR("Ст. ошибка остатков")),("chi2_red","χ²_red"),("sse","SSE"),("sst","SST"),]
		visible=[(k,t) for k,t in rows if k in metrics and metrics[k]is not None]
		table=QTableWidget()
		table.setColumnCount(2)
		table.setHorizontalHeaderLabels([_TR("Метрика"),_TR("Значение")])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		table.verticalHeader().setVisible(False)
		table.setEditTriggers(QTableWidget.NoEditTriggers)
		table.setSelectionMode(QTableWidget.NoSelection)
		table.setRowCount(len(visible))
		for i,(k,title) in enumerate(visible):
			table.setItem(i,0,QTableWidgetItem(title))
			table.setItem(i,1,QTableWidgetItem(self._format_metric_value(metrics[k])))
		table.resizeRowsToContents()
		row_h=table.verticalHeader().defaultSectionSize() if table.rowCount() else 20
		table.setMaximumHeight(min(280, max(70, table.rowCount()*max(20,row_h)+28)))
		return table
	def _build_coeff_table(self,coeffs:dict,names:list)->QTableWidget:
		order=list(names)if names else list(coeffs.keys())
		table=QTableWidget()
		table.setColumnCount(2)
		table.setHorizontalHeaderLabels([_TR("Параметр"),_TR("Значение")])
		table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		table.verticalHeader().setVisible(False)
		table.setEditTriggers(QTableWidget.NoEditTriggers)
		table.setSelectionMode(QTableWidget.NoSelection)
		table.setRowCount(len(order))
		for i,k in enumerate(order):
			table.setItem(i,0,QTableWidgetItem(str(k)))
			table.setItem(i,1,QTableWidgetItem(self._format_metric_value(coeffs.get(k))))
		table.resizeRowsToContents()
		row_h=table.verticalHeader().defaultSectionSize() if table.rowCount() else 20
		table.setMaximumHeight(min(220, max(60, table.rowCount()*max(20,row_h)+28)))
		return table
	@staticmethod
	def _format_metric_value(v)->str:
		if v is None:
			return "—"
		if isinstance(v,bool):
			return _TR("да") if v else _TR("нет")
		if isinstance(v,int):
			return str(v)
		try:
			fv=float(v)
		except(TypeError,ValueError):
			return str(v)
		if not (fv==fv):
			return "—"
		if fv==0:
			return "0"
		if 1e-3<=abs(fv)<1e5:
			return f"{fv:.6g}"
		return f"{fv:.3e}"
	def _build_peaks_table(self,points:list)->QTableWidget:
		table=QTableWidget()
		table.setColumnCount(6)
		table.setHorizontalHeaderLabels([_TR("№"),"X","Y",_TR("Индекс"),_TR("Значимость"),_TR("Полуширина (FWHM)")])
		header=table.horizontalHeader()
		header.setSectionResizeMode(QHeaderView.ResizeToContents)
		header.setSectionResizeMode(1,QHeaderView.Stretch)
		header.setSectionResizeMode(2,QHeaderView.Stretch)
		table.verticalHeader().setVisible(False)
		table.setEditTriggers(QTableWidget.NoEditTriggers)
		table.setSelectionBehavior(QTableWidget.SelectRows)
		table.setRowCount(len(points))
		for i,pt in enumerate(points):
			table.setItem(i,0,QTableWidgetItem(str(i+1)))
			table.setItem(i,1,QTableWidgetItem(self._format_value(pt.get("x"))))
			table.setItem(i,2,QTableWidgetItem(self._format_value(pt.get("y"))))
			idx=pt.get("index")
			table.setItem(i,3,QTableWidgetItem(str(int(idx)) if idx is not None else "—"))
			table.setItem(i,4,QTableWidgetItem(self._format_value(pt.get("prominence"))))
			table.setItem(i,5,QTableWidgetItem(self._format_value(pt.get("width"))))
		table.resizeRowsToContents()
		row_h=table.verticalHeader().defaultSectionSize() if table.rowCount() else 20
		table.setMaximumHeight(min(280, max(70, table.rowCount()*max(20,row_h)+28)))
		return table
	def _param_title(self,tool_id:str,key:str)->str:
		prefix=_PARAM_PREFIX_BY_TOOL.get(tool_id)
		if not prefix:
			return str(key)
		full_key=f"{prefix}.{key}"
		title=tr_analysis(full_key)
		if title==full_key:
			return str(key)
		return title
	@staticmethod
	def _format_value(v)->str:
		if v is None:
			return "—"
		if isinstance(v,bool):
			return _TR("да") if v else _TR("нет")
		if isinstance(v,(int,float)):
			if isinstance(v,int):
				return str(v)
			if v!=v:
				return "—"
			return f"{v:.6g}"
		try:
			import numpy as np
			if isinstance(v,np.floating):
				if not np.isfinite(v):
					return "—"
				return f"{float(v):.6g}"
			if isinstance(v,np.integer):
				return str(int(v))
			if isinstance(v,np.bool_):
				return _TR("да") if bool(v) else _TR("нет")
		except ImportError:
			pass
		if isinstance(v,(list,tuple)):
			return f"[{len(v)}]"
		if isinstance(v,dict):
			return f"{{{len(v)}}}"
		return str(v)
	def _on_tool_activated(self,tool_id:str)->None:
		desc=self.registry.get(tool_id)
		if desc is None:
			return
		self.active_title.setText(self._resolve_title(desc))
		self._rebuild_params(desc)
		self.active_group.setVisible(True)
		is_unc=(tool_id=="uncertainty.estimate")
		self.unc_style_group.setVisible(is_unc)
		if is_unc:
			self._load_uncertainty_style_for_active()
	def _on_tool_deactivated(self)->None:
		self.active_group.setVisible(False)
		self._param_widgets.clear()
		self._clear_params_form()
		self.unc_style_group.setVisible(False)
		self._unc_live_debounce.stop()
	def _rebuild_params(self,desc)->None:
		self._clear_params_form()
		self._param_widgets.clear()
		for param in desc.param_schema:
			w=self._build_param_widget(param)
			if w is not None:
				self._param_widgets[param.name]=w
				title=tr_analysis(param.title_key)
				self.params_form.addRow(title,w)
				if param.tooltip_key:
					tip=tr_analysis(param.tooltip_key)
					if tip:
						w.setToolTip(tip)
	def _clear_params_form(self)->None:
		while self.params_form.count():
			item=self.params_form.takeAt(0)
			if item is None:
				break
			w=item.widget()
			if w is not None:
				w.setParent(None)
				w.deleteLater()
			sub=item.layout()
			if sub is not None:
				while sub.count():
					sub_item=sub.takeAt(0)
					sw=sub_item.widget()
					if sw is not None:
						sw.setParent(None)
						sw.deleteLater()
	def _build_param_widget(self,param:ParamDescriptor)->Optional[QWidget]:
		if param.type==ParamType.INT:
			w=QSpinBox()
			w.setMinimumWidth(0)
			w.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
			w.setRange(int(param.min)if param.min is not None else-10**9,int(param.max)if param.max is not None else 10**9)
			w.setValue(int(param.default or 0))
			w.valueChanged.connect(lambda v,n=param.name:self._param_changed(n,int(v)))
			return w
		if param.type==ParamType.FLOAT:
			w=QDoubleSpinBox()
			w.setMinimumWidth(0)
			w.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
			w.setRange(float(param.min)if param.min is not None else-1e12,float(param.max)if param.max is not None else 1e12)
			w.setDecimals(6)
			w.setSingleStep(float(param.step)if param.step is not None else 0.01)
			w.setValue(float(param.default or 0.0))
			w.valueChanged.connect(lambda v,n=param.name:self._param_changed(n,float(v)))
			return w
		if param.type==ParamType.BOOL:
			w=QCheckBox()
			w.setChecked(bool(param.default))
			w.stateChanged.connect(lambda st,n=param.name:self._param_changed(n,st!=0))
			return w
		if param.type==ParamType.CHOICE:
			w=QComboBox()
			w.setMinimumWidth(0)
			w.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
			for ch in param.choices:
				if isinstance(ch,(tuple,list)) and len(ch)==2:
					value,label_key=ch
					w.addItem(tr_analysis(str(label_key)),value)
				else:
					w.addItem(str(ch),ch)
			for i in range(w.count()):
				if w.itemData(i)==param.default:
					w.setCurrentIndex(i)
					break
			w.currentIndexChanged.connect(lambda idx,n=param.name,ww=w:self._param_changed(n,ww.currentData()))
			return w
		if param.type==ParamType.TEXT:
			w=QLineEdit(str(param.default or ""))
			w.setMinimumWidth(0)
			w.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
			w.editingFinished.connect(lambda n=param.name,ww=w:self._param_changed(n,ww.text()))
			return w
		return None
	def _resolve_title(self,desc)->str:
		from..models import tr_analysis
		return tr_analysis(desc.title_key)
	def _add_tool_item(self,desc)->None:
		self.tool_combo.addItem(self._resolve_title(desc),desc.tool_id)
		idx=self.tool_combo.count()-1
		if desc.tooltip_key:
			tip=tr_analysis(desc.tooltip_key)
			if tip:
				self.tool_combo.setItemData(idx,tip,Qt.ToolTipRole)
	def _resolve_tool_title(self,tool_id:str)->str:
		d=self.registry.get(tool_id)
		return self._resolve_title(d)if d else tool_id