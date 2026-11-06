import logging
from dataclasses import dataclass
from typing import Any,Dict,List,Optional,Set
from PyQt5.QtCore import QObject,QTimer,pyqtSignal
from PyQt5.QtWidgets import QApplication
from graphs.core.session_mode import SessionMode
from.commands import(ApplyAnalysisCommand,ApplyUncertaintyCommand,RemoveAnalysisCommand,RemoveUncertaintyCommand,UpdateAnalysisParamsCommand)
from.models import(AnalysisArtifact,SourceSnapshot,)
from.preview import AnalysisPreviewManager
from.registry import AnalysisToolRegistry
from.renderers.adapter import AnalysisRendererAdapter
from.store import SessionAnalysisStore
from.uncertainty import UncertaintyRecord,compute_uncertainty
logger=logging.getLogger(__name__)
_TR=lambda s:QApplication.translate("GraphWindow",s)
_METRIC_KEYS=("n","dof","n_params","sse","sst","r2","adj_r2","rmse","std_err","chi2_red","params","param_names",)
@dataclass
class ToolSession:
	tool_id:str
	params:Dict[str,Any]
	sources:List[SourceSnapshot]
	leader_index:int
	preview_handle:Any=None
class AnalysisController(QObject):
	tool_activated=pyqtSignal(str)
	tool_deactivated=pyqtSignal()
	preview_updated=pyqtSignal()
	artifact_applied=pyqtSignal(str)
	artifact_removed=pyqtSignal(str)
	artifacts_changed=pyqtSignal()
	tool_apply_failed=pyqtSignal(str,dict)
	tool_apply_partial=pyqtSignal(str,dict)
	def __init__(self,session,parent=None)->None:
		super().__init__(parent)
		self.session=session
		self.store=SessionAnalysisStore()
		self.preview=AnalysisPreviewManager()
		self.renderer=AnalysisRendererAdapter(session)
		self.registry=AnalysisToolRegistry.instance()
		self._active:Optional[ToolSession]=None
		self._uncertainty_archive:Dict[str,UncertaintyRecord]={}
		self._highlighted:set=set()
		self._subscribed_curves:Dict[str,Any]={}
		self._pending_recompute:Set[str]=set()
		self._last_data_version:Dict[str,int]={}
		self._recomputing:bool=False
		self._recompute_timer=QTimer(self)
		self._recompute_timer.setSingleShot(True)
		self._recompute_timer.setInterval(150)
		self._recompute_timer.timeout.connect(self._flush_recompute)
		self.last_apply_failures:Dict[str,str]={}
		self.last_apply_tool_id:Optional[str]=None
		model=getattr(session,"selection_model",None)
		if model is not None:
			model.selection_changed.connect(self._on_selection_changed)
	def activate_tool(self,tool_id:str,sources:Optional[List[str]]=None)->bool:
		if self.session.mode==SessionMode.LIVE:
			return False
		desc=self.registry.get(tool_id)
		if desc is None:
			return False
		snapshots=self._collect_sources(sources)
		if not snapshots:
			return False
		if self._active is not None and self._active.tool_id!=tool_id:
			self._active=None
		leader_index=len(snapshots)-1
		params={p.name:p.default for p in desc.param_schema}
		self._active=ToolSession(tool_id=tool_id,params=params,sources=snapshots,leader_index=leader_index)
		self.tool_activated.emit(tool_id)
		return True
	def cancel_preview(self)->None:
		if self._active is not None:
			if self._active.preview_handle is not None:
				self.renderer.remove(self._active.preview_handle)
		self.preview.clear()
		self._active=None
		self.preview_updated.emit()
		self.tool_deactivated.emit()
	def set_preview_params(self,params:Dict[str,Any])->None:
		if self._active is None:
			return
		self._active.params.update(params)
	def _build_payload_index_map(self,details)->Dict[str,int]:
		result:Dict[str,int]={}
		idx=0
		for d in details or []:
			if d.get("error"):
				continue
			curve=d.get("curve")
			if curve is None:
				continue
			result[curve]=idx
			idx+=1
		return result
	def _failure_reason_for(self,root_name:str,details)->str:
		for d in details or []:
			if d.get("curve")==root_name and d.get("error"):
				return str(d["error"])
		return "нет данных для отображения"
	def apply(self)->List[str]:
		self.last_apply_failures={}
		self.last_apply_tool_id=None
		if self._active is None:
			return []
		tool_id=self._active.tool_id
		self.last_apply_tool_id=tool_id
		descriptor=self.registry.get(tool_id)
		if descriptor is None:
			return []
		source_root_names=[s.root_name for s in self._active.sources]
		fresh_sources=self._collect_sources(source_root_names)
		if not fresh_sources:
			return []
		self._active.sources=fresh_sources
		created:List[str]=[]
		source_ids={s.root_name for s in self._active.sources}
		for art in list(self.store.all()):
			if art.tool_id==tool_id and set(art.source_curve_ids)&source_ids:
				self._do_remove(art.id)
		if tool_id=="uncertainty.estimate":
			for snap in self._active.sources:
				curve=self.session.graph_main.get_curve(snap.root_name)
				if curve is None:
					continue
				store=getattr(curve,"store",None)
				if store is None:
					continue
				for rec in list(getattr(store,"uncertainty_records",[]) or []):
					self._do_remove_uncertainty(snap.root_name,rec.id)
			for snap in self._active.sources:
				record=self._compute_uncertainty_record(snap,self._active.params)
				cmd=ApplyUncertaintyCommand(self,snap.root_name,record)
				self.session.undo_manager.push(cmd,execute=True)
			self.artifacts_changed.emit()
			return created
		strategy=self.registry.create_strategy(tool_id)
		if strategy is None:
			msg="внутренняя ошибка: стратегия инструмента не найдена"
			self.last_apply_failures={s.root_name:msg for s in self._active.sources}
			self.tool_apply_failed.emit(tool_id,dict(self.last_apply_failures))
			return []
		from.strategies.base import AnalysisContext
		ctx=AnalysisContext(sources=self._active.sources,filter_instance=getattr(self.session,"filter_class",None),alias_manager=getattr(self.session,"alias_manager",None),)
		try:
			payload,details=strategy.compute(ctx,self._active.params)
		except(ValueError,TypeError,RuntimeError,KeyError)as exc:
			logger.warning("apply: compute failed: %s",exc)
			msg=str(exc) or"внутренняя ошибка вычисления"
			self.last_apply_failures={s.root_name:msg for s in self._active.sources}
			self.tool_apply_failed.emit(tool_id,dict(self.last_apply_failures))
			return []
		kind=getattr(payload,"kind",None)
		payload_idx_map=self._build_payload_index_map(details)if kind!="annotation"else{}
		failures:Dict[str,str]={}
		for i,snap in enumerate(self._active.sources):
			if kind=="annotation":
				sub_payload=self._payload_for_source(payload,i,snap.root_name)
			else:
				idx=payload_idx_map.get(snap.root_name)
				if idx is None:
					failures[snap.root_name]=self._failure_reason_for(snap.root_name,details)
					continue
				sub_payload=self._payload_for_source(payload,idx,snap.root_name)
				xs=getattr(sub_payload,"x",[]) or []
				ys=getattr(sub_payload,"y",[]) or []
				if not xs or not ys or len(xs)==0 or len(ys)==0 or len(xs[0])==0 or len(ys[0])==0:
					failures[snap.root_name]="нет данных для отображения"
					continue
			metrics=self._extract_metrics(details,snap.root_name)
			if metrics:
				self._attach_metrics_to_payload(sub_payload,metrics)
			description=self._build_artifact_description(strategy,self._active.params,sub_payload,details,snap.root_name,)
			artifact=AnalysisArtifact(tool_id=tool_id,source_curve_ids=[snap.root_name],params=dict(self._active.params),placement_type=descriptor.placement_type,payload=sub_payload,description=description,leader_curve_id=snap.root_name,)
			if metrics:
				artifact.extras["metrics"]=metrics
			cmd=ApplyAnalysisCommand(self,artifact)
			self.session.undo_manager.push(cmd,execute=True)
			created.append(artifact.id)
		if failures:
			self.last_apply_failures=dict(failures)
			if not created:
				self.tool_apply_failed.emit(tool_id,dict(failures))
			else:
				self.tool_apply_partial.emit(tool_id,dict(failures))
		if created:
			self.artifacts_changed.emit()
		return created
	def apply_uncertainty_live(self)->None:
		if self._active is None or self._active.tool_id!="uncertainty.estimate":
			return
		source_root_names=[s.root_name for s in self._active.sources]
		fresh_sources=self._collect_sources(source_root_names)
		if fresh_sources:
			self._active.sources=fresh_sources
		for snap in self._active.sources:
			curve=self.session.graph_main.get_curve(snap.root_name)
			if curve is None:
				continue
			store=getattr(curve,"store",None)
			if store is None:
				continue
			for rec in list(getattr(store,"uncertainty_records",[]) or []):
				self._do_remove_uncertainty(snap.root_name,rec.id)
			record=self._compute_uncertainty_record(snap,self._active.params)
			self._do_apply_uncertainty(snap.root_name,record)
		self.artifacts_changed.emit()
	def remove_uncertainty(self,root_name:str,record_id:str)->None:
		cmd=RemoveUncertaintyCommand(self,root_name,record_id)
		self.session.undo_manager.push(cmd,execute=True)
		self.artifacts_changed.emit()
	def on_source_name_changed(self,root_name:str)->None:
		for art in self._artifacts_for_source(root_name):
			try:
				self.renderer.update_legend_names(art)
			except(AttributeError,RuntimeError,KeyError)as exc:
				logger.warning("on_source_name_changed: %s failed: %s",art.id,exc)
	def on_source_style_changed(self,root_name:str)->None:
		for art in list(self.store.for_curve(root_name)):
			try:
				old_handle=art.handle
				if old_handle is not None:
					self.renderer.remove(old_handle)
				new_handle=self.renderer.render(art,is_preview=False)
				art.handle=new_handle
				if new_handle is not None:
					self.renderer.set_visible(new_handle,art.visibility)
			except(AttributeError,RuntimeError,KeyError)as exc:
				logger.warning("on_source_style_changed: re-render %s failed: %s",art.id,exc)
		curve=self.session.graph_main.get_curve(root_name)
		if curve is not None:
			store=getattr(curve,"store",None)
			if store is not None and hasattr(curve.presenter,"set_error_bars"):
				try:
					curve.presenter.set_error_bars(store.active_uncertainty_records())
				except(AttributeError,RuntimeError)as exc:
					logger.warning("on_source_style_changed: error bars failed: %s",exc)
		self.artifacts_changed.emit()
	def apply_preset(self,preset,sources:Optional[List[str]]=None)->int:
		if preset is None or not getattr(preset,"artifacts",None):
			return 0
		snapshots=self._collect_sources(sources)
		if not snapshots:
			return 0
		applied=0
		aggregated_failures:Dict[str,str]={}
		for entry in preset.artifacts:
			tool_id=entry.get("tool_id")
			if not tool_id or self.registry.get(tool_id) is None:
				continue
			params=dict(entry.get("params") or {})
			self._active=ToolSession(tool_id=tool_id,params=params,sources=list(snapshots),leader_index=len(snapshots)-1,)
			try:
				created=self.apply()
				if created or tool_id=="uncertainty.estimate":
					applied+=1
				for curve,msg in (self.last_apply_failures or {}).items():
					aggregated_failures[curve]=msg
			except(ValueError,TypeError,RuntimeError,KeyError)as exc:
				logger.warning("apply_preset: tool %s failed: %s",tool_id,exc)
			finally:
				self._active=None
		self.last_apply_failures=dict(aggregated_failures)
		if aggregated_failures:
			if applied==0:
				self.tool_apply_failed.emit(preset.name or"preset",dict(aggregated_failures))
			else:
				self.tool_apply_partial.emit(preset.name or"preset",dict(aggregated_failures))
		self.artifacts_changed.emit()
		return applied
	def set_uncertainty_visible(self,root_name:str,record_id:str,visible:bool)->None:
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return
		store=getattr(curve,"store",None)
		if store is None:
			return
		store.set_uncertainty_active(record_id,visible)
		if hasattr(curve.presenter,"set_error_bars"):
			curve.presenter.set_error_bars(store.active_uncertainty_records())
		self.artifacts_changed.emit()
	def set_uncertainty_style(self,root_name:str,style:Dict[str,Any])->None:
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return
		store=getattr(curve,"store",None)
		if store is None:
			return
		from.uncertainty import normalize_uncertainty_style
		new_style=normalize_uncertainty_style(style or {})
		store.uncertainty_style=dict(new_style)
		for rec in getattr(store,"uncertainty_records",[]) or []:
			rec.style=dict(new_style)
		if hasattr(curve.presenter,"set_error_bars"):
			curve.presenter.set_error_bars(store.active_uncertainty_records())
		self.artifacts_changed.emit()
	def get_uncertainty_style(self,root_name:str)->Optional[Dict[str,Any]]:
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return None
		store=getattr(curve,"store",None)
		if store is None:
			return None
		from.uncertainty import normalize_uncertainty_style
		style=dict(getattr(store,"uncertainty_style",{}) or {})
		if not style and getattr(store,"uncertainty_records",None):
			style=dict(store.uncertainty_records[0].style or {})
		return normalize_uncertainty_style(style)
	def _on_selection_changed(self,selected)->None:
		selected_roots=set()
		for item in selected or []:
			root=None
			if hasattr(item,"store") and hasattr(item.store,"rel_data"):
				root=item.store.rel_data.root_name
			elif hasattr(item,"rel_data"):
				root=item.rel_data.root_name
			if root:
				selected_roots.add(root)
		if self._active is not None:
			fresh_sources=self._collect_sources(None)
			self._active.sources=fresh_sources
			self._active.leader_index=(len(fresh_sources)-1 if fresh_sources else-1)
		for art in self.store.all():
			is_sel=any(s in selected_roots for s in art.source_curve_ids)
			if is_sel and art.id not in self._highlighted:
				self._highlighted.add(art.id)
				try:
					self.renderer.set_highlighted(art.handle,True)
				except(AttributeError,RuntimeError,KeyError)as exc:
					logger.debug("_on_selection_changed: highlight on failed for %s: %s",art.id,exc,)
			elif not is_sel and art.id in self._highlighted:
				self._highlighted.discard(art.id)
				try:
					self.renderer.set_highlighted(art.handle,False)
				except(AttributeError,RuntimeError,KeyError)as exc:
					logger.debug("_on_selection_changed: highlight off failed for %s: %s",art.id,exc,)
	def remove_artifact(self,artifact_id:str)->None:
		artifact=self.store.get(artifact_id)
		if artifact is None:
			return
		cmd=RemoveAnalysisCommand(self,artifact)
		self.session.undo_manager.push(cmd,execute=True)
		self.artifacts_changed.emit()
	def _artifacts_for_source(self,root_name:str)->List[AnalysisArtifact]:
		return [art for art in self.store.all()if root_name in art.source_curve_ids]
	def on_source_hidden(self,root_name:str)->None:
		for art in self._artifacts_for_source(root_name):
			try:
				self.renderer.set_visible(art.handle,False)
			except(AttributeError,RuntimeError,KeyError)as exc:
				logger.warning("on_source_hidden: set_visible failed for %s: %s",art.id,exc,)
		self.artifacts_changed.emit()
	def on_source_shown(self,root_name:str)->None:
		for art in self._artifacts_for_source(root_name):
			try:
				self.renderer.set_visible(art.handle,bool(art.visibility))
			except(AttributeError,RuntimeError,KeyError)as exc:
				logger.warning("on_source_shown: set_visible failed for %s: %s",art.id,exc,)
		self.artifacts_changed.emit()
	def set_artifact_visibility(self,artifact_id:str,visible:bool)->None:
		artifact=self.store.get(artifact_id)
		if artifact is None:
			return
		artifact.visibility=bool(visible)
		self.renderer.set_visible(artifact.handle,bool(visible))
		self.artifacts_changed.emit()
	def get_artifacts_for_curve(self,root_name:str)->List[AnalysisArtifact]:
		return self.store.for_curve(root_name)
	def get_active_tool(self)->Optional[ToolSession]:
		return self._active
	def _do_apply(self,artifact:AnalysisArtifact)->None:
		self.store.add(artifact)
		handle=self.renderer.render(artifact,is_preview=False)
		artifact.handle=handle
		self.renderer.set_visible(handle,artifact.visibility)
		for root_name in artifact.source_curve_ids:
			self._subscribe_curve(root_name)
		self.artifacts_changed.emit()
		self.artifact_applied.emit(artifact.id)
	def _do_remove(self,artifact_id:str)->None:
		artifact=self.store.get(artifact_id)
		if artifact is None:
			return
		self.renderer.remove(artifact.handle)
		self.store.remove(artifact_id)
		for root_name in artifact.source_curve_ids:
			self._maybe_unsubscribe_curve(root_name)
		self.artifacts_changed.emit()
		self.artifact_removed.emit(artifact_id)
	def _extract_metrics(self,details,root_name:Optional[str])->Dict[str,Any]:
		if not details:
			return {}
		for d in details:
			if root_name is not None and d.get("curve")==root_name:
				if d.get("error"):
					return {}
				return {k:d[k] for k in _METRIC_KEYS if k in d and d[k]is not None}
		if root_name is None and len(details)==1:
			d=details[0]
			if d.get("error"):
				return {}
			return {k:d[k] for k in _METRIC_KEYS if k in d and d[k]is not None}
		return {}
	def _attach_metrics_to_payload(self,payload,metrics:Dict[str,Any])->None:
		if payload is None or not metrics:
			return
		kind=getattr(payload,"kind",None)
		if kind=="overlay":
			sh=dict(getattr(payload,"style_hint",{}) or {})
			sh["metrics"]=metrics
			try:
				payload.style_hint=sh
			except AttributeError:
				pass
		elif kind in ("attached","domain"):
			ex=dict(getattr(payload,"extras",{}) or {})
			ex["metrics"]=metrics
			try:
				payload.extras=ex
			except AttributeError:
				pass
	def _build_artifact_description(self,strategy,params:Dict[str,Any],sub_payload,details,root_name:Optional[str])->str:
		base=strategy.describe(params)
		kind=getattr(sub_payload,"kind",None)
		if kind=="annotation":
			n=len(getattr(sub_payload,"points",[]) or [])
			total=n
			for d in (details or []):
				if root_name is not None and d.get("curve")==root_name:
					total=d.get("total_found",n)
					break
			if total>n:
				tail=f"показано {n} из {total} — увеличьте max_points или минимальную значимость"
			elif n==0:
				tail="ничего не найдено — ослабьте фильтры"
			else:
				tail=f"найдено: {n}"
			return f"{base}; {tail}"if base else tail
		if kind=="overlay":
			metrics=self._extract_metrics(details,root_name)
			if metrics:
				parts=[]
				r2=metrics.get("r2")
				if r2 is not None:
					parts.append(f"R²={r2:.6f}")
				rmse=metrics.get("rmse")
				if rmse is not None:
					parts.append(f"RMSE={rmse:.4g}")
				if parts:
					tail=", ".join(parts)
					return f"{base}; {tail}"if base else tail
		return base
	def _subscribe_curve(self,root_name:str)->None:
		if root_name in self._subscribed_curves:
			return
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return
		store=getattr(curve,"store",None)
		if store is None:
			return
		callback=lambda rn=root_name:self._on_source_data_changed(rn)
		store.on_data_changed(callback)
		self._subscribed_curves[root_name]=callback
	def _unsubscribe_curve(self,root_name:str)->None:
		callback=self._subscribed_curves.pop(root_name,None)
		if callback is None:
			return
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return
		store=getattr(curve,"store",None)
		if store is not None:
			store.off_data_changed(callback)
	def _on_source_data_changed(self,root_name:str)->None:
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return
		store=getattr(curve,"store",None)
		if store is None:
			return
		current_version=getattr(store,"data_version",0)
		if current_version==self._last_data_version.get(root_name,-1):
			return
		has_artifacts=bool(self.store.for_curve(root_name))
		has_uncertainty=bool(getattr(store,"uncertainty_records",None))
		if not (has_artifacts or has_uncertainty):
			return
		self._last_data_version[root_name]=current_version
		self._pending_recompute.add(root_name)
		self._recompute_timer.start()
	def _flush_recompute(self)->None:
		if not self._pending_recompute:
			return
		pending=list(self._pending_recompute)
		self._pending_recompute.clear()
		if self._recomputing:
			self._pending_recompute.update(pending)
			self._recompute_timer.start()
			return
		self._recomputing=True
		try:
			for root_name in pending:
				self._recompute_uncertainty_for(root_name)
				for artifact in list(self.store.for_curve(root_name)):
					self._recompute_artifact(artifact)
		finally:
			self._recomputing=False
		self.artifacts_changed.emit()
	def _recompute_uncertainty_for(self,root_name:str)->None:
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return
		store=getattr(curve,"store",None)
		if store is None:
			return
		records=list(getattr(store,"uncertainty_records",[]) or [])
		if not records:
			return
		x=store.filtered_x_data
		y=store.filtered_y_data
		if len(x)==0 or len(y)==0:
			return
		for rec in records:
			try:
				fresh=compute_uncertainty(getattr(rec,"method","std"),x,y,dict(getattr(rec,"params",{}) or {}),)
			except(ValueError,TypeError,ZeroDivisionError,FloatingPointError)as exc:
				logger.warning("_recompute_uncertainty_for: compute failed for %s: %s",rec.id,exc,)
				continue
			rec.y_err=fresh.y_err
			rec.x_err=fresh.x_err
		if hasattr(curve.presenter,"set_error_bars"):
			try:
				curve.presenter.set_error_bars(store.active_uncertainty_records())
			except(AttributeError,RuntimeError)as exc:
				logger.warning("_recompute_uncertainty_for: set_error_bars failed: %s",exc)
	def _maybe_unsubscribe_curve(self,root_name:str)->None:
		if self.store.for_curve(root_name):
			return
		curve=self.session.graph_main.get_curve(root_name)
		store=getattr(curve,"store",None)if curve is not None else None
		if store is not None and getattr(store,"uncertainty_records",None):
			return
		self._unsubscribe_curve(root_name)
	def _recompute_artifact(self,artifact:AnalysisArtifact)->None:
		strategy=self.registry.create_strategy(artifact.tool_id)
		if strategy is None:
			return
		snapshots=self._collect_sources(artifact.source_curve_ids)
		if not snapshots:
			return
		from.strategies.base import AnalysisContext
		ctx=AnalysisContext(sources=snapshots,filter_instance=getattr(self.session,"filter_class",None),)
		params=dict(artifact.params)
		try:
			payload,details=strategy.compute(ctx,params)
		except(ValueError,TypeError,RuntimeError,KeyError)as exc:
			logger.warning("_recompute_artifact: compute failed for %s: %s",artifact.id,exc,)
			return
		source_id=(artifact.source_curve_ids[0]if artifact.source_curve_ids else None)
		new_payload=self._payload_for_source(payload,0,source_id)
		kind=getattr(new_payload,"kind",None)
		if kind in ("overlay","attached","domain"):
			xs=getattr(new_payload,"x",[]) or []
			ys=getattr(new_payload,"y",[]) or []
			if not xs or not ys or len(xs)==0 or len(ys)==0 or len(xs[0])==0:
				logger.warning("_recompute_artifact: source %s produced no data on recompute; keeping old artifact",source_id)
				return
		metrics=self._extract_metrics(details,source_id)if source_id else{}
		if metrics:
			self._attach_metrics_to_payload(new_payload,metrics)
		new_description=self._build_artifact_description(strategy,params,new_payload,details,source_id,)
		extras:Optional[Dict[str,Any]]={"metrics":metrics}if metrics else None
		self._do_update_params(artifact.id,params,new_payload,new_description,extras=extras)
	def _do_update_params(self,artifact_id:str,params:Dict[str,Any],payload,description:Optional[str]=None,extras:Optional[Dict[str,Any]]=None)->None:
		artifact=self.store.get(artifact_id)
		if artifact is None:
			return
		kind=getattr(payload,"kind",None)
		if kind=="annotation":
			self.renderer.remove(artifact.handle)
			artifact.handle=None
			artifact.params=dict(params)
			artifact.payload=payload
			if description is not None:
				artifact.description=description
			if extras:
				artifact.extras.update(extras)
			handle=self.renderer.render(artifact,is_preview=False)
			artifact.handle=handle
			self.renderer.set_visible(handle,artifact.visibility)
			return
		artifact.params=dict(params)
		artifact.payload=payload
		if description is not None:
			artifact.description=description
		if extras:
			artifact.extras.update(extras)
		self.renderer.update(artifact.handle,payload)
	def _do_apply_uncertainty(self,root_name:str,record:UncertaintyRecord)->None:
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return
		store=curve.store
		store.uncertainty_records.append(record)
		store.active_uncertainty_ids.add(record.id)
		self._uncertainty_archive[record.id]=record
		if hasattr(curve.presenter,"set_error_bars"):
			curve.presenter.set_error_bars(store.active_uncertainty_records())
		self._subscribe_curve(root_name)
		store._notify_changed()
	def _do_remove_uncertainty(self,root_name:str,record_id:str)->None:
		curve=self.session.graph_main.get_curve(root_name)
		if curve is None:
			return
		store=curve.store
		store.uncertainty_records=[r for r in store.uncertainty_records if r.id!=record_id]
		store.active_uncertainty_ids.discard(record_id)
		if hasattr(curve.presenter,"set_error_bars"):
			curve.presenter.set_error_bars(store.active_uncertainty_records())
		self._maybe_unsubscribe_curve(root_name)
		store._notify_changed()
	def _do_restore_uncertainty(self,root_name:str,record_id:str)->None:
		record=self._uncertainty_archive.get(record_id)
		if record is None:
			return
		self._do_apply_uncertainty(root_name,record)
	def _collect_sources(self,sources:Optional[List[str]])->List[SourceSnapshot]:
		selected_ids=sources
		if selected_ids is None:
			selected_ids=self._selected_curve_ids()
		result:List[SourceSnapshot]=[]
		for root_name in selected_ids:
			curve=self.session.graph_main.get_curve(root_name)
			if curve is None:
				continue
			result.append(SourceSnapshot(root_name=root_name,x=curve.filtered_x_data,y=curve.filtered_y_data,x_name=curve.rel_data.x_current_name,y_name=curve.rel_data.y_current_name,device=getattr(curve,"device","") or "",ch=getattr(curve,"ch","") or "",number_axis=curve.number_axis or 1,saved_style=curve.saved_style,curve_name=curve.curve_name,))
		return result
	def _selected_curve_ids(self)->List[str]:
		model=getattr(self.session,"selection_model",None)
		if model is None:
			return []
		ids:List[str]=[]
		for item in model.current():
			root_name=None
			if hasattr(item,"store") and hasattr(item.store,"rel_data"):
				root_name=item.store.rel_data.root_name
			elif hasattr(item,"rel_data"):
				root_name=item.rel_data.root_name
			if root_name and root_name not in ids:
				ids.append(root_name)
		return ids
	def _compute_uncertainty_record(self,snap:SourceSnapshot,params:Dict[str,Any])->UncertaintyRecord:
		method=params.get("method","std")
		rec=compute_uncertainty(method,snap.x,snap.y,params)
		curve=self.session.graph_main.get_curve(snap.root_name)
		if curve is not None:
			store_style=getattr(curve.store,"uncertainty_style",None) or {}
			if store_style:
				from.uncertainty import normalize_uncertainty_style
				rec.style=normalize_uncertainty_style(store_style)
		return rec
	def _payload_for_source(self,payload,index:int,source_id:Optional[str]=None):
		kind=getattr(payload,"kind",None)
		if kind=="annotation":
			pts=list(getattr(payload,"points",[]) or [])
			if source_id is not None:
				pts=[p for p in pts if p.get("curve") is None or p.get("curve")==source_id]
			return type(payload)(points=pts,label=payload.label)
		if kind=="overlay":
			xs=getattr(payload,"x",[])
			ys=getattr(payload,"y",[])
			return type(payload)(x=[xs[index]]if index<len(xs)else[],y=[ys[index]]if index<len(ys)else[],style_hint=dict(getattr(payload,"style_hint",{}) or {}),)
		if kind=="attached":
			xs=getattr(payload,"x",[])
			ys=getattr(payload,"y",[])
			return type(payload)(x=[xs[index]]if index<len(xs)else[],y=[ys[index]]if index<len(ys)else[],y_label=payload.y_label,panel_title=payload.panel_title,)
		if kind=="domain":
			xs=getattr(payload,"x",[])
			ys=getattr(payload,"y",[])
			return type(payload)(x=[xs[index]]if index<len(xs)else[],y=[ys[index]]if index<len(ys)else[],x_label=payload.x_label,y_label=payload.y_label,tab_title=payload.tab_title,)
		if kind=="uncertainty":
			return payload
		return payload