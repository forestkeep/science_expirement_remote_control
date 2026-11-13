from __future__ import annotations

import logging
import os
import time

from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox

from ...core.json_io import load_spec, save_spec
from ...model.figure_model import FigureSpec
from ...model.panel import CurveSlot
from ...model.session_ref import DataSnapshot, StyleSnapshot
from ...model.stylestack import StyleStack
from ...presets.builtin import SAFE_DEFAULTS
from ...presets.loader import load_lab_profile_auto, load_style_profile_by_id
from ...validation.validator import Validator
from ...export.exporter import Exporter, BackgroundExporter
from ..context_menus import ImportSessionDialog
from ..template_chooser import TemplateChooserDialog

logger = logging.getLogger(__name__)


class PublicationWidgetPanelsMixin:
	def _on_panel_reordered(self,ordered_ids:list):
		by_id={p.id:p for p in self.spec.panels}
		new_panels=[by_id[pid] for pid in ordered_ids if pid in by_id]
		for i,p in enumerate(new_panels):
			p.z=i+1
		self.spec.panels=new_panels
		self._refresh_tree()
		self._schedule_render()
	def _on_panel_duplicate(self,panel_id:str):
		src=self.spec.find_panel(panel_id)
		if src is None:
			return
		import copy
		new_panel=self.spec.add_panel(x_mm=src.x_mm+5,y_mm=src.y_mm+5,w_mm=src.w_mm,h_mm=src.h_mm,title=src.title+" (copy)",)
		new_panel.x_label=src.x_label
		new_panel.y_label=src.y_label
		new_panel.y2_label=src.y2_label
		new_panel.y2_visible=src.y2_visible
		new_panel.show_tools=dict(src.show_tools)
		new_panel.curves=[copy.deepcopy(s) for s in src.curves]
		new_panel.style_overrides=dict(src.style_overrides)
		self._refresh_tree()
		self._schedule_render()
	def _on_refresh_data_requested(self,panel_id:str):
		panel=self.spec.find_panel(panel_id)
		if panel is None:
			return
		for slot in panel.curves:
			if slot.data_ref is None or slot.data_ref.is_empty():
				continue
			sess,curve=self.data_loader._get_curve(slot.data_ref.session_id,slot.data_ref.series_root_name)
			if curve is not None:
				slot.data_ref.data=DataSnapshot.take(curve)
				slot.data_ref.stale_data=False
		self._schedule_render()
	def _on_refresh_style_requested(self,panel_id:str):
		panel=self.spec.find_panel(panel_id)
		if panel is None:
			return
		for slot in panel.curves:
			if slot.data_ref is None or slot.data_ref.is_empty():
				continue
			sess,curve=self.data_loader._get_curve(slot.data_ref.session_id,slot.data_ref.series_root_name)
			if curve is not None:
				slot.data_ref.style=StyleSnapshot.take(curve,lambda c:self._artifacts_for_curve(c))
				slot.data_ref.stale_style=False
		self._schedule_render()
	def _on_enable_live_requested(self,panel_id:str):
		panel=self.spec.find_panel(panel_id)
		if panel is None:
			return
		for slot in panel.curves:
			if slot.data_ref is not None:
				slot.data_ref.refresh_policy="live"
				slot.data_ref.stale_data=False
		self._schedule_render()
	def _on_reload(self):
		self.source_bus.ensure_all_attached()
		self._schedule_render()
		self._refresh_tree()
		self._set_status_state("Сессии перепривязаны")
	def _on_zoom_toggled(self,checked:bool):
		self._canvas.set_real_size(bool(checked))
	def _add_panel(self):
		panel=self.spec.add_panel(x_mm=5.0,y_mm=5.0,w_mm=60.0,h_mm=45.0)
		self._current_panel_id=panel.id
		self._canvas.set_selected_panels([panel.id])
		self._on_panel_selected(panel.id)
		self._refresh_tree()
		self._refresh_counters()
		self._schedule_render()
	def _delete_panel(self,panel_id:str):
		if not panel_id:
			return
		removed=self.spec.remove_panel(panel_id)
		if not removed:
			return
		if self._current_panel_id==panel_id:
			self._on_figure_selected()
		self._refresh_tree()
		self._refresh_counters()
		self._schedule_render()
	def _import_session_to_panel(self):
		dialog=ImportSessionDialog(self.session_controller,self)
		if dialog.exec_()!=QDialog.Accepted:
			return
		ref=dialog.get_data_ref()
		if ref.is_empty():
			return
		sess,curve=self.data_loader._get_curve(ref.session_id,ref.series_root_name)
		if curve is not None:
			ref.data=DataSnapshot.take(curve)
			ref.style=StyleSnapshot.take(curve,lambda c:self._artifacts_for_curve(c))
			ref.refresh_policy="snapshot"
		slot=CurveSlot(data_ref=ref,axis="y1",visible=True)
		panel=self._current_panel()
		if panel is not None:
			panel.curves.append(slot)
		else:
			panel=self.spec.add_panel(curves=[slot],x_mm=5.0,y_mm=5.0,w_mm=60.0,h_mm=45.0)
			self._current_panel_id=panel.id
		self._canvas.set_selected_panels([panel.id])
		self._on_panel_selected(panel.id)
		self._refresh_tree()
		self._refresh_counters()
		self._schedule_render()
	def _on_apply_layout(self):
		default_margin=float((self.preset.constraints or {}).get("margin_mm",3.0))
		default_gap=min(default_margin,2.0)
		last_template_id=self.spec.metadata.get("last_template_id")
		dialog=TemplateChooserDialog(self.spec,default_margin=default_margin,default_gap=default_gap,parent=self,last_template_id=last_template_id)
		if dialog.exec_()!=QDialog.Accepted:
			return
		if dialog._selected_template is not None:
			self.spec.metadata["last_template_id"]=dialog._selected_template.id
		current=self._current_panel_id
		still_exists=(current is not None and any(p.id==current for p in self.spec.panels))
		if still_exists:
			self._on_panel_selected(current)
		else:
			self._on_figure_selected()
			if self.spec.panels:
				self._on_panel_selected(self.spec.panels[0].id)
		self._refresh_tree()
		self._refresh_counters()
		self._schedule_render()
		self._set_status_state(f"Шаблон применён: {len(self.spec.panels)} панелей")
	def _on_validate(self):
		report=Validator(self.spec,self.preset,self.style_stack,self._resolve_data).validate()
		self._last_validation=report
		n_warn=len(report.warnings)
		n_err=len(report.errors)
		if n_err:
			label=f"валидация: {n_err} ошибок"
			self._validation_btn.setStyleSheet("text-align: left; color: #c02020; text-decoration: underline;")
		elif n_warn:
			label=f"валидация: {n_warn} предупреждений"
			self._validation_btn.setStyleSheet("text-align: left; color: #c08a20; text-decoration: underline;")
		else:
			label="валидация: OK"
			self._validation_btn.setStyleSheet("text-align: left; color: #2a82da; text-decoration: underline;")
		self._validation_btn.setText(label)
		if report.all_issues:
			self._show_validation_report()
	def _show_validation_report(self):
		if self._last_validation is None:
			return
		report=self._last_validation
		if not report.all_issues:
			QMessageBox.information(self,"Валидация","Проблем не найдено.")
			return
		lines=[]
		for issue in report.all_issues[:40]:
			line=f"[{issue.severity}] {issue.code}: {issue.message}"
			if issue.panel_id:
				line+=f" (panel={issue.panel_id})"
			lines.append(line)
		QMessageBox.information(self,"Валидация","\n".join(lines))
	def _on_export(self):
		report=Validator(self.spec,self.preset,self.style_stack,self._resolve_data).validate()
		self._last_validation=report
		if not report.ok:
			ans=QMessageBox.question(self,"Экспорт",f"Валидатор нашёл проблемы: ошибок {len(report.errors)}, "f"предупреждений {len(report.warnings)}. Продолжить?",QMessageBox.Yes|QMessageBox.No,)
			if ans!=QMessageBox.Yes:
				return
		dir_path=QFileDialog.getExistingDirectory(self,"Каталог пакета экспорта")
		if not dir_path:
			return
		if os.listdir(dir_path):
			dir_path=os.path.join(dir_path,f"pub_export_{int(time.time())}")
		exporter=Exporter(self.spec,self.preset,self.style_stack,self._resolve_data,self._resolve_override,validation_report=report,)
		self._set_status_state("Экспорт...")
		self._progress_bar.setVisible(True)
		self._progress_bar.setRange(0,0)
		self._exporter_bg=BackgroundExporter(exporter,self)
		self._exporter_bg.start(dir_path,include_png=False,on_finished=self._on_export_done,on_failed=self._on_export_failed,)
	def _on_export_done(self,path:str):
		self._progress_bar.setVisible(False)
		self._set_status_state(f"Экспорт готов: {path}")
		QMessageBox.information(self,"Экспорт",f"Готово:\n{path}")
	def _on_export_failed(self,msg:str):
		self._progress_bar.setVisible(False)
		self._set_status_state(f"Ошибка экспорта: {msg}")
		QMessageBox.critical(self,"Экспорт",msg)
	def save_to_file(self,path:str):
		save_spec(self.spec,path)
	def load_from_file(self,path:str):
		self.spec=load_spec(path)
		self._current_panel_id=None
		self._current_slot_index=-1
		self._current_ann_id=None
		self._canvas.set_spec(self.spec)
		self._canvas.set_selected_panels([])
		self._inspector_figure.set_spec(self.spec)
		self._inspector_panel.set_spec(self.spec)
		self._inspector_panel.set_panel("")
		self._inspector_annotation.set_spec(self.spec)
		self._load_journal(self.spec.journal_preset_id or "nature_double")
		self._load_style(self.spec.style_profile_id or "okabe_ito")
		self._refresh_tree()
		self._refresh_counters()
		self._schedule_render()
	def _on_panel_export(self,panel_id:str):
		panel=self.spec.find_panel(panel_id)
		if panel is None:
			return
		dir_path=QFileDialog.getExistingDirectory(self,f"Экспорт панели {panel_id}")
		if not dir_path:
			return
		tmp=FigureSpec.from_dict(self.spec.to_dict())
		tmp.panels=[p for p in tmp.panels if p.id==panel_id]
		tmp.presentation_annotations=[a for a in tmp.presentation_annotations if a.panel_id==panel_id]
		style_data=load_style_profile_by_id(tmp.style_profile_id)
		journal_data=self.preset.defaults if self.preset else{}
		stack=StyleStack(tmp,safe_defaults=SAFE_DEFAULTS,style_profile=style_data,journal_defaults=journal_data,lab_profile=load_lab_profile_auto(),)
		exporter=Exporter(tmp,self.preset,stack,self._resolve_data,self._resolve_override,)
		try:
			exporter.export_package(dir_path,include_png=False)
			self._set_status_state(f"Панель {panel_id} экспортирована: {dir_path}")
		except Exception as exc:
			logger.exception("panel export failed")
			QMessageBox.critical(self,"Экспорт панели",str(exc))


	def _create_legend_panel(self,source_panels:list)->None:
		panel=self.spec.add_legend_panel(source_panels=list(source_panels or []),source_slots=[],x_mm=5.0,y_mm=5.0,w_mm=40.0,h_mm=20.0,)
		panel.style_overrides["legend.hide_sources"]=True
		panel.style_overrides["legend.dedupe"]=True
		self._current_panel_id=panel.id
		self._canvas.set_selected_panels([panel.id])
		self._on_panel_selected(panel.id)
		self._refresh_tree()
		self._refresh_counters()
		self._schedule_render()

	def _on_request_create_legend(self,source_panel_id=None)->None:
		from PyQt5.QtWidgets import QDialog
		if source_panel_id:
			self._create_legend_panel([str(source_panel_id)])
			return
		candidates=[p for p in self.spec.sorted_panels()if p.kind!="legend"and p.visible and p.curves]
		if not candidates:
			self._create_legend_panel([])
			return
		if len(candidates)==1:
			self._create_legend_panel([candidates[0].id])
			return
		dlg=self._open_legend_create_dialog(None)
		if dlg is None:
			return
		if dlg.exec_()!=QDialog.Accepted:
			return
		self._create_legend_panel(dlg.result_sources())


	
	def _on_request_add_to_legend(self,source_panel_id:str)->None:
		legends=[p for p in self.spec.panels if p.kind=="legend"]
		if not legends:
			self._on_request_create_legend(source_panel_id)
			return
		from PyQt5.QtWidgets import QInputDialog
		names=[f"{p.title or p.id}"for p in legends]
		choice,ok=QInputDialog.getItem(self,"Добавить в легенду","Легенда:",names,0,False)
		if not ok:
			return
		target_idx=names.index(choice)
		legend=legends[target_idx]
		if source_panel_id not in legend.source_panels:
			legend.source_panels.append(source_panel_id)
		legend.source_slots=[(pid,sidx) for pid,sidx in legend.source_slots if pid!=source_panel_id]
		self._refresh_tree()
		self._schedule_render()
		self._set_status_state(f"Панель {source_panel_id} добавлена в легенду {legend.id}")
		
	
	def _open_legend_create_dialog(self,source_panel_id=None):
		from PyQt5.QtWidgets import(QDialog,QVBoxLayout,QLabel,QListWidget,QListWidgetItem,QDialogButtonBox,)
		from PyQt5.QtCore import Qt as _Qt
		candidates=[p for p in self.spec.sorted_panels()if p.kind!="legend"and p.visible and p.curves]
		dlg=QDialog(self)
		dlg.setWindowTitle("Создать легенду")
		dlg.resize(360,320)
		outer=QVBoxLayout(dlg)
		outer.addWidget(QLabel("Выберите панели-источники:"))
		lst=QListWidget()
		lst.setSelectionMode(QListWidget.NoSelection)
		for p in candidates:
			item=QListWidgetItem(p.title or p.id)
			item.setFlags(item.flags()|_Qt.ItemIsUserCheckable)
			item.setCheckState(_Qt.Checked)
			item.setData(_Qt.UserRole,p.id)
			lst.addItem(item)
		outer.addWidget(lst,1)
		bbox=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
		bbox.accepted.connect(dlg.accept)
		bbox.rejected.connect(dlg.reject)
		outer.addWidget(bbox)
		def _result_sources():
			src=[]
			for i in range(lst.count()):
				it=lst.item(i)
				if it.checkState()==_Qt.Checked:
					src.append(it.data(_Qt.UserRole))
			return src
		dlg.result_sources=_result_sources
		return dlg