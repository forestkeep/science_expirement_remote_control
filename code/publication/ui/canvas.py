from __future__ import annotations
import logging
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np
from PyQt5.QtCore import QEvent, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QFont, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (QAction, QApplication, QMenu, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from ..core.units import mm_to_px
from ..model.annotations import PresentationAnnotation
from ..model.panel import PanelSpec
import math
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGridLayout

logger = logging.getLogger(__name__)
SNAP_MM = 1.0


def _snap(value: float) -> float:
    return round(value / SNAP_MM) * SNAP_MM

class _RulerWidget(QWidget):
	def __init__(self,orientation,parent=None):
		super().__init__(parent)
		self._orientation=orientation
		self._offset=0
		self._px_per_mm=1.0
		self._length_mm=0.0
		if orientation==Qt.Horizontal:
			self.setFixedHeight(20)
		else:
			self.setFixedWidth(20)
		self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
		self.setAttribute(Qt.WA_OpaquePaintEvent,True)
	def set_geometry_info(self,length_mm:float,px_per_mm:float)->None:
		self._length_mm=float(length_mm)
		self._px_per_mm=float(px_per_mm)if px_per_mm and px_per_mm>0 else 1.0
		self.update()
	def set_offset(self,offset:int)->None:
		if self._offset!=offset:
			self._offset=int(offset)
			self.update()
	def _tick_step_mm(self)->int:
		if self._px_per_mm<=0:
			return 10
		target=80.0
		best=10
		best_diff=abs(10*self._px_per_mm-target)
		for c in (20,50,100):
			d=abs(c*self._px_per_mm-target)
			if d<best_diff:
				best=c
				best_diff=d
		return best
	def paintEvent(self,event):
		p=QPainter(self)
		try:
			p.fillRect(self.rect(),QColor("#f0f0f0"))
			p.setPen(QColor("#888888"))
			if self._orientation==Qt.Horizontal:
				p.drawLine(0,self.height()-1,self.width(),self.height()-1)
			else:
				p.drawLine(self.width()-1,0,self.width()-1,self.height())
			if self._px_per_mm<=0:
				return
			step_mm=self._tick_step_mm()
			step_px=step_mm*self._px_per_mm
			if step_px<=0:
				return
			f=QFont()
			f.setPointSize(7)
			p.setFont(f)
			p.setPen(QColor("#333333"))
			length=self.width()if self._orientation==Qt.Horizontal else self.height()
			edge_mm=self._offset/self._px_per_mm
			first_mm=math.floor(edge_mm/step_mm)*step_mm
			first_px=first_mm*self._px_per_mm-self._offset
			mm=first_mm
			px=first_px
			while px<=length+step_px:
				if px>=-step_px:
					x=int(px)
					label=str(int(round(mm)))
					if self._orientation==Qt.Horizontal:
						p.drawLine(x,self.height()-6,x,self.height())
						p.drawText(x+2,self.height()-8,label)
					else:
						p.drawLine(self.width()-6,x,self.width(),x)
						p.drawText(1,x-2,label)
				mm+=step_mm
				px+=step_px
		finally:
			p.end()


class _CanvasInner(FigureCanvasQTAgg):
	panel_selected=pyqtSignal(str,bool)
	panel_geometry_changed=pyqtSignal(str,float,float,float,float)
	annotation_selected=pyqtSignal(str)
	annotation_geometry_changed=pyqtSignal(str,tuple)
	annotation_delete_requested=pyqtSignal(str)
	annotation_properties=pyqtSignal(str)
	selection_cleared=pyqtSignal()
	refresh_data_requested=pyqtSignal(str)
	refresh_style_requested=pyqtSignal(str)
	enable_live_requested=pyqtSignal(str)
	add_panel_requested=pyqtSignal()
	add_text_requested=pyqtSignal()
	add_arrow_requested=pyqtSignal()
	add_scale_bar_requested=pyqtSignal()
	add_bracket_requested=pyqtSignal()
	apply_layout_requested=pyqtSignal()
	delete_panel_requested=pyqtSignal(str)
	drag_finished=pyqtSignal()
	spec_changed=pyqtSignal()
	def __init__(self,widget:"PublicationCanvas"):
		self._cached_pixmap:Optional[QPixmap]=None
		self._content_dirty:bool=True
		self._figure=Figure(figsize=(1,1),dpi=100)
		super().__init__(self._figure)
		self.widget=widget
		self.setMouseTracking(True)
		self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
		self.setFocusPolicy(Qt.StrongFocus)
		self._drag_mode=""
		self._drag_panel_id:Optional[str]=None
		self._drag_ann_id:Optional[str]=None
		self._press_pos:Tuple[float,float]=(0.0,0.0)
		self._orig_geom:Tuple[float,float,float,float]=(0.0,0.0,0.0,0.0)
		self._orig_ann_coords:Tuple[float,...]=()
		self._selected_panel_ids:list=[]
		self._undo_stack:List[Tuple[Callable[[],None],Callable[[],None]]]=[]
		self._redo_stack:List[Tuple[Callable[[],None],Callable[[],None]]]=[]
		self._kbd_orig_geoms:Dict[str,Tuple[float,float,float,float]]={}
		self._render_info:Dict[str,dict]={"legends":{}}
	def set_render_info(self,info:Optional[dict])->None:
		self._render_info=info or {"legends":{}}
		self._invalidate_cache()
	def _push_command(self,do_fn,undo_fn)->None:
		self._undo_stack.append((do_fn,undo_fn))
		self._redo_stack.clear()

	def _clamp_geom(self,x,y,w,h):
		spec=self.widget.spec
		if spec is None:
			return float(x),float(y),float(w),float(h)
		fw=float(spec.width_mm)
		fh=float(spec.height_mm)
		if fw<=0 or fh<=0:
			return float(x),float(y),float(w),float(h)
		w=max(2.0,min(float(w),fw))
		h=max(2.0,min(float(h),fh))
		x=max(0.0,min(float(x),fw-w))
		y=max(0.0,min(float(y),fh-h))
		return x,y,w,h

	def _hit_legend(self,x_mm:float,y_mm:float,tol_mm:float=2.0):
		spec=self.widget.spec
		if spec is None:
			return None
		for panel in reversed(spec.sorted_panels()):
			if not panel.visible or panel.kind!="legend":
				continue
			rect=self._legend_rect_for(panel.id)
			if rect is not None:
				rx,ry,rw,rh=rect
				if rx-tol_mm<=x_mm<=rx+rw+tol_mm and ry-tol_mm<=y_mm<=ry+rh+tol_mm:
					return panel
			px,py,pw,ph=panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm
			near_edge=((abs(x_mm-px)<=1.0 or abs(x_mm-(px+pw))<=1.0 or abs(y_mm-py)<=1.0 or abs(y_mm-(py+ph))<=1.0) and (px-2<=x_mm<=px+pw+2) and (py-2<=y_mm<=py+ph+2))
			if near_edge:
				return panel
		return None

	
	def _make_geom_command(self,changes):
		def do():
			for pid,_old,new in changes:
				self._apply_geom(pid,new)
		def undo():
			for pid,old,_new in changes:
				self._apply_geom(pid,old)
		return do,undo
	def _apply_geom(self,panel_id,geom)->None:
		x,y,w,h=geom
		self.panel_geometry_changed.emit(panel_id,x,y,w,h)
	def undo(self)->None:
		if not self._undo_stack:
			return
		do_fn,undo_fn=self._undo_stack.pop()
		undo_fn()
		self._redo_stack.append((do_fn,undo_fn))
		self.drag_finished.emit()
	def redo(self)->None:
		if not self._redo_stack:
			return
		do_fn,undo_fn=self._redo_stack.pop()
		do_fn()
		self._undo_stack.append((do_fn,undo_fn))
		self.drag_finished.emit()
	def _delete_selected_panels(self)->None:
		spec=self.widget.spec
		if spec is None:
			return
		targets=[]
		for pid in list(self._selected_panel_ids):
			panel=spec.find_panel(pid)
			if panel is None or panel.locked:
				continue
			anns=[a for a in spec.presentation_annotations if a.panel_id==pid]
			try:
				index=spec.panels.index(panel)
			except ValueError:
				index=len(spec.panels)
			targets.append({"panel":PanelSpec.from_dict(panel.to_dict()),"index":index,"annotations":[PresentationAnnotation.from_dict(a.to_dict()) for a in anns],})
		if not targets:
			return
		for t in targets:
			self.delete_panel_requested.emit(t["panel"].id)
		self._selected_panel_ids=[]
		self.update()
		def do():
			for t in targets:
				self.delete_panel_requested.emit(t["panel"].id)
		def undo():
			existing_ids={p.id for p in spec.panels}
			for t in sorted(targets,key=lambda x:x["index"]):
				panel=t["panel"]
				base=panel.id
				pid=base
				n=1
				while pid in existing_ids:
					pid=f"{base}_r{n}"
					n+=1
				panel.id=pid
				existing_ids.add(pid)
				for ann in t["annotations"]:
					ann.panel_id=pid
				if t["index"]<=len(spec.panels):
					spec.panels.insert(t["index"],panel)
				else:
					spec.panels.append(panel)
				spec.presentation_annotations.extend(t["annotations"])
			self.spec_changed.emit()
		self._push_command(do,undo)
		self.drag_finished.emit()

	def keyPressEvent(self,event):
		key=event.key()
		mods=event.modifiers()
		if mods&Qt.ControlModifier:
			if key==Qt.Key_Z:
				self.undo();event.accept(); return
			if key==Qt.Key_Y:
				self.redo();event.accept(); return
		if key==Qt.Key_Delete:
			self._delete_selected_panels();event.accept(); return
		if key in (Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down):
			if not self._selected_panel_ids:
				super().keyPressEvent(event); return
			if not self._kbd_orig_geoms:
				for pid in self._selected_panel_ids:
					panel=self.widget.spec.find_panel(pid)
					if panel is not None and not panel.locked:
						self._kbd_orig_geoms[pid]=(panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm)
			step=1.0
			dx=dy=0.0
			if key==Qt.Key_Left:dx=-step
			elif key==Qt.Key_Right:dx=step
			elif key==Qt.Key_Up:dy=-step
			elif key==Qt.Key_Down:dy=step
			for panel_id in self._selected_panel_ids:
				panel=self.widget.spec.find_panel(panel_id)
				if panel is None or panel.locked:
					continue
				new_x,new_y,_,_=self._clamp_geom(_snap(panel.x_mm+dx),_snap(panel.y_mm+dy),panel.w_mm,panel.h_mm)
				if(new_x,new_y)!=(panel.x_mm,panel.y_mm):
					self._apply_geom(panel_id,(new_x,new_y,panel.w_mm,panel.h_mm))
			self.update();event.accept(); return
		super().keyPressEvent(event)

	def keyReleaseEvent(self,event):
		key=event.key()
		if key in (Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down) and not event.isAutoRepeat():
			if self._kbd_orig_geoms:
				changes=[]
				for pid,old_geom in self._kbd_orig_geoms.items():
					panel=self.widget.spec.find_panel(pid)
					if panel is None:
						continue
					new_geom=(panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm)
					if old_geom!=new_geom:
						changes.append((pid,old_geom,new_geom))
				self._kbd_orig_geoms={}
				if changes:
					do,undo=self._make_geom_command(changes)
					self._push_command(do,undo)
					self.drag_finished.emit()
			event.accept(); return
		super().keyReleaseEvent(event)
	def set_selected_panels(self,panel_ids:list)->None:
		self._selected_panel_ids=list(panel_ids or [])
		self.update()
	@property
	def selected_panel_ids(self)->list:
		return list(self._selected_panel_ids)
	def _invalidate_cache(self)->None:
		self._cached_pixmap=None
		self._content_dirty=True
	def draw(self)->None:
		super().draw()
		if hasattr(self,"_cached_pixmap"):
			self._cache_from_buffer()
			self._content_dirty=False
	def _cache_from_buffer(self)->None:
		try:
			rgba=np.asarray(self.figure.canvas.buffer_rgba())
			h,w=rgba.shape[:2]
			if w<=0 or h<=0:
				self._cached_pixmap=None
				return
			image=QImage(rgba.data,w,h,4*w,QImage.Format_RGBA8888).copy()
			self._cached_pixmap=QPixmap.fromImage(image)
		except Exception:
			logger.exception("_cache_from_buffer failed")
			self._cached_pixmap=None
	def _update_figure_size(self)->None:
		w,h=self.width(),self.height()
		if w<=0 or h<=0:
			return
		spec=getattr(self.widget,"spec",None)
		if spec is not None and spec.width_mm>0 and spec.height_mm>0:
			page_scale=w/spec.width_mm
			fig_dpi=max(1.0,25.4*page_scale)
			try:
				self.figure.set_dpi(fig_dpi)
				self.figure.set_size_inches(spec.width_mm/25.4,spec.height_mm/25.4,forward=False)
			except Exception:
				logger.exception("_update_figure_size failed")
			return
		dpi=float(self.figure.dpi) or 100.0
		try:
			self.figure.set_size_inches(w/dpi,h/dpi,forward=False)
		except Exception:
			logger.exception("_update_figure_size failed")

	def resizeEvent(self,event):
		self._invalidate_cache();super().resizeEvent(event);self._update_figure_size()
	def showEvent(self,event):
		super().showEvent(event);self._update_figure_size()
	def set_figure(self,figure:Figure)->None:
		if getattr(self,"figure",None) is figure:
			self.draw_idle(); return
		figure.set_canvas(self)
		self.figure=figure
		self._figure=figure
		self._update_figure_size()
		self._invalidate_cache()
		self.draw_idle()
	def _pos_to_mm(self,pos)->Optional[Tuple[float,float]]:
		spec=self.widget.spec
		if spec is None:
			return None
		w,h=self.width(),self.height()
		if w<=0 or h<=0:
			return None
		return (pos.x()/w*spec.width_mm,pos.y()/h*spec.height_mm)
	def _legend_rect_for(self,panel_id:str):
		legends=(self._render_info or {}).get("legends",{})
		r=legends.get(panel_id)
		if not r:
			return None
		return (float(r.get("x_mm",0.0)),float(r.get("y_mm",0.0)),float(r.get("w_mm",0.0)),float(r.get("h_mm",0.0)))
	
	def _hit_panel(self,x_mm:float,y_mm:float,tol_mm:float=2.0):
		spec=self.widget.spec
		if spec is None:
			return None
		legend=self._hit_legend(x_mm,y_mm,tol_mm=tol_mm)
		if legend is not None:
			return legend
		for panel in reversed(spec.sorted_panels()):
			if not panel.visible or panel.kind=="legend":
				continue
			if panel.contains_point_mm(x_mm,y_mm,tol_mm=tol_mm):
				return panel
		return None
	
	def _annotation_center_mm(self,ann):
		spec=self.widget.spec
		if spec is None or len(ann.coords)<2:
			return None
		x0,y0=float(ann.coords[0]),float(ann.coords[1])
		if ann.coordinate_space=="figure_mm":
			return x0,y0
		if ann.coordinate_space=="panel_mm"and ann.panel_id:
			panel=spec.find_panel(ann.panel_id)
			if panel is not None:
				return panel.x_mm+x0,panel.y_mm+y0
		return None
	def _hit_annotation(self,x_mm,y_mm,tol_mm=5.0):
		spec=self.widget.spec
		if spec is None:
			return None
		for ann in sorted(spec.presentation_annotations,key=lambda a:(-int(a.z),a.id)):
			if not ann.visible or ann.locked:
				continue
			c=self._annotation_center_mm(ann)
			if c is None:
				continue
			if abs(x_mm-c[0])<=tol_mm and abs(y_mm-c[1])<=tol_mm:
				return ann
		return None
	def _hit_stale_badge(self,x_mm:float,y_mm:float):
		spec=self.widget.spec
		if spec is None:
			return None
		w,h=self.width(),self.height()
		if w<=0 or h<=0:
			return None
		click_x_px=x_mm/spec.width_mm*w
		click_y_px=y_mm/spec.height_mm*h
		for panel in reversed(spec.sorted_panels()):
			if not panel.visible or panel.kind=="legend":
				continue
			stale_data=any(getattr(c.data_ref,"stale_data",False) for c in panel.curves if c.data_ref is not None)
			stale_style=any(getattr(c.data_ref,"stale_style",False) for c in panel.curves if c.data_ref is not None)
			if not (stale_data or stale_style):
				continue
			x_px=(panel.x_mm+panel.w_mm)/spec.width_mm*w-22
			y_px=panel.y_mm/spec.height_mm*h+4
			if x_px<=click_x_px<=x_px+18 and y_px<=click_y_px<=y_px+18:
				return panel,stale_data,stale_style
		return None
	def mousePressEvent(self,event):
		if event.button()!=Qt.LeftButton:
			super().mousePressEvent(event); return
		pt=self._pos_to_mm(event.localPos())
		if pt is None:
			super().mousePressEvent(event); return
		x_mm,y_mm=pt
		spec=self.widget.spec
		if spec is None:
			super().mousePressEvent(event); return
		badge=self._hit_stale_badge(x_mm,y_mm)
		if badge is not None:
			panel,stale_data,stale_style=badge
			if stale_data:
				self.refresh_data_requested.emit(panel.id)
			elif stale_style:
				self.refresh_style_requested.emit(panel.id)
			event.accept(); return
		additive=bool(event.modifiers()&Qt.ShiftModifier)
		ann=self._hit_annotation(x_mm,y_mm)
		if ann is not None:
			self._drag_mode="move_annotation"
			self._drag_ann_id=ann.id
			self._press_pos=(x_mm,y_mm)
			self._orig_ann_coords=tuple(ann.coords)
			self.annotation_selected.emit(ann.id)
			event.accept(); return
		panel=self._hit_panel(x_mm,y_mm,tol_mm=2.0)
		if panel is not None:
			edge=panel.edge_hit(x_mm,y_mm,tol_mm=2.0)if panel.kind!="legend"else""
			if edge:
				self._drag_mode="resize_"+edge
			else:
				self._drag_mode="move"
			self._drag_panel_id=panel.id
			self._press_pos=(x_mm,y_mm)
			self._orig_geom=(panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm)
			self._select_panel(panel.id,additive)
			event.accept(); return
		self._selected_panel_ids=[]
		self.selection_cleared.emit()
		super().mousePressEvent(event)
	def _select_panel(self,panel_id:str,additive:bool)->None:
		if additive:
			if panel_id in self._selected_panel_ids:
				self._selected_panel_ids.remove(panel_id)
			else:
				self._selected_panel_ids.append(panel_id)
		else:
			self._selected_panel_ids=[panel_id]
		self.panel_selected.emit(panel_id,additive)
		self.setFocus()
		self.update()
		
	def mouseMoveEvent(self,event):
		pt=self._pos_to_mm(event.localPos())
		if pt is None:
			super().mouseMoveEvent(event); return
		x_mm,y_mm=pt
		spec=self.widget.spec
		if not self._drag_mode:
			cursor=Qt.ArrowCursor
			if spec is not None:
				if self._hit_legend(x_mm,y_mm,tol_mm=2.0) is not None:
					cursor=Qt.SizeAllCursor
				else:
					for panel in reversed(spec.sorted_panels()):
						if not panel.visible or panel.kind=="legend":
							continue
						edge=panel.edge_hit(x_mm,y_mm,tol_mm=2.0)
						if edge=="br":
							cursor=Qt.SizeFDiagCursor;break
						if edge=="r":
							cursor=Qt.SizeHorCursor;break
						if edge=="b":
							cursor=Qt.SizeVerCursor;break
						if panel.contains_point_mm(x_mm,y_mm,tol_mm=2.0):
							cursor=Qt.SizeAllCursor;break
			self.setCursor(QCursor(cursor))
			super().mouseMoveEvent(event); return
		if self._drag_mode=="move_annotation":
			ann=spec.find_presentation(self._drag_ann_id or "")
			if ann is None or ann.locked:
				self._drag_mode="";self._drag_ann_id=None; return
			dx=_snap(x_mm-self._press_pos[0])
			dy=_snap(y_mm-self._press_pos[1])
			new=list(self._orig_ann_coords)
			if ann.coordinate_space in ("figure_mm","panel_mm") and len(new)>=2:
				new[0]=self._orig_ann_coords[0]+dx
				new[1]=self._orig_ann_coords[1]+dy
			self.annotation_geometry_changed.emit(ann.id,tuple(new))
			self.update();event.accept(); return
		panel=spec.find_panel(self._drag_panel_id or "")
		if panel is None or panel.locked:
			self._drag_mode="";self._drag_panel_id=None; return
		dx=_snap(x_mm-self._press_pos[0])
		dy=_snap(y_mm-self._press_pos[1])
		ox,oy,ow,oh=self._orig_geom
		if self._drag_mode=="move":
			nx,ny,_,_=self._clamp_geom(_snap(ox+dx),_snap(oy+dy),ow,oh)
			self._apply_geom(panel.id,(nx,ny,ow,oh))
		elif self._drag_mode=="resize_br":
			nx,ny,nw,nh=self._clamp_geom(ox,oy,_snap(ow+dx),_snap(oh+dy))
			self._apply_geom(panel.id,(nx,ny,nw,nh))
		elif self._drag_mode=="resize_r":
			nx,ny,nw,_=self._clamp_geom(ox,oy,_snap(ow+dx),oh)
			self._apply_geom(panel.id,(nx,ny,nw,oh))
		elif self._drag_mode=="resize_b":
			nx,ny,_,nh=self._clamp_geom(ox,oy,ow,_snap(oh+dy))
			self._apply_geom(panel.id,(nx,ny,ow,nh))
		self.update();event.accept()

	def mouseReleaseEvent(self,event):
		was_dragging=bool(self._drag_mode)
		if was_dragging and self._drag_panel_id and self._drag_mode in ("move","resize_br","resize_r","resize_b"):
			panel=self.widget.spec.find_panel(self._drag_panel_id)
			if panel is not None:
				old_geom=self._orig_geom
				new_geom=(panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm)
				if old_geom!=new_geom:
					do,undo=self._make_geom_command([(self._drag_panel_id,old_geom,new_geom)])
					self._push_command(do,undo)
		self._drag_mode=""
		self._drag_panel_id=None
		self._drag_ann_id=None
		super().mouseReleaseEvent(event)
		if was_dragging:
			self.drag_finished.emit()
	def paintEvent(self,event):
		if not self._content_dirty and self._cached_pixmap is not None:
			painter=QPainter(self)
			try:
				painter.drawPixmap(0,0,self._cached_pixmap)
			finally:
				painter.end()
		else:
			super().paintEvent(event)
		self._paint_overlay()

	def _paint_overlay(self):
		spec=self.widget.spec
		if spec is None:
			return
		painter=QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		try:
			w,h=self.width(),self.height()
			if w<=0 or h<=0:
				return
			if not spec.panels:
				painter.setPen(QColor("#5a5a5a"))
				f=QFont();f.setPointSize(13);painter.setFont(f)
				painter.drawText(self.rect(),Qt.AlignCenter,"Холст пуст\n\nПравый клик → «Добавить панель» или «Разложить по шаблону»")
			if spec.panels:
				min_x,min_y,max_x,max_y=spec.content_bbox_mm()
				if max_x>min_x and max_y>min_y:
					bx=int(min_x/spec.width_mm*w)
					by=int(min_y/spec.height_mm*h)
					bw=int((max_x-min_x)/spec.width_mm*w)
					bh=int((max_y-min_y)/spec.height_mm*h)
					if bw>0 and bh>0:
						pen=QPen(QColor("#1f8f4e"),2,Qt.DashLine)
						painter.setPen(pen)
						painter.setBrush(Qt.NoBrush)
						painter.drawRect(bx,by,bw,bh)
			for panel in spec.sorted_panels():
				if panel.id not in self._selected_panel_ids:
					continue
				x_px=int(panel.x_mm/spec.width_mm*w)
				y_px=int(panel.y_mm/spec.height_mm*h)
				w_px=int(panel.w_mm/spec.width_mm*w)
				h_px=int(panel.h_mm/spec.height_mm*h)
				painter.setPen(QPen(QColor("#2a82da"),2,Qt.DashLine))
				painter.setBrush(QColor(42,130,218,30))
				painter.drawRect(x_px,y_px,w_px,h_px)
				if panel.kind=="legend":
					rect=self._legend_rect_for(panel.id)
					if rect is not None:
						rx,ry,rw,rh=rect
						lx=int(rx/spec.width_mm*w)
						ly=int(ry/spec.height_mm*h)
						lw=int(rw/spec.width_mm*w)
						lh=int(rh/spec.height_mm*h)
						painter.setPen(QPen(QColor("#888888"),1,Qt.DotLine))
						painter.setBrush(Qt.NoBrush)
						painter.drawRect(lx,ly,lw,lh)
			for panel in spec.sorted_panels():
				if not panel.visible or panel.kind=="legend":
					continue
				stale_data=any(getattr(c.data_ref,"stale_data",False) for c in panel.curves if c.data_ref is not None)
				stale_style=any(getattr(c.data_ref,"stale_style",False) for c in panel.curves if c.data_ref is not None)
				if not (stale_data or stale_style):
					continue
				x_px=int(panel.x_mm/spec.width_mm*w)+int(panel.w_mm/spec.width_mm*w)-22
				y_px=int(panel.y_mm/spec.height_mm*h)+4
				color=QColor("#ff4040")if stale_data else QColor("#f5c542")
				painter.setPen(QPen(color,2))
				painter.setBrush(QColor(0,0,0,120))
				painter.drawEllipse(x_px,y_px,18,18)
				f=QFont();f.setPointSize(11);f.setBold(True);painter.setFont(f)
				painter.setPen(color)
				painter.drawText(QRectF(x_px,y_px,18,18).toRect(),Qt.AlignCenter,"⟳")
		finally:
			painter.end()

	def contextMenuEvent(self,event):
		pt=self._pos_to_mm(event.pos())
		if pt is None:
			return
		x_mm,y_mm=pt
		spec=self.widget.spec
		if spec is None:
			return
		ann=self._hit_annotation(x_mm,y_mm)
		if ann is not None:
			self._annotation_menu(event.globalPos(),ann.id); return
		panel=self._hit_panel(x_mm,y_mm,tol_mm=2.0)
		if panel is not None:
			self._panel_menu(event.globalPos(),panel.id); return
		self._empty_menu(event.globalPos())
	def _empty_menu(self,global_pos):
		menu=QMenu(self)
		add_sub=menu.addMenu("Добавить")
		act_panel=add_sub.addAction("Панель")
		act_legend=add_sub.addAction("Легенда…")
		act_text=add_sub.addAction("Текст (presentation)")
		act_arrow=add_sub.addAction("Стрелка (presentation)")
		act_scale=add_sub.addAction("Scale bar (presentation)")
		act_bracket=add_sub.addAction("Скобка (presentation)")
		act_panel.triggered.connect(self.add_panel_requested.emit)
		act_legend.triggered.connect(lambda:self._request_create_legend())
		act_text.triggered.connect(self.add_text_requested.emit)
		act_arrow.triggered.connect(self.add_arrow_requested.emit)
		act_scale.triggered.connect(self.add_scale_bar_requested.emit)
		act_bracket.triggered.connect(self.add_bracket_requested.emit)
		menu.addSeparator()
		act_layout=menu.addAction("Разложить по шаблону…")
		act_layout.triggered.connect(self.apply_layout_requested.emit)
		menu.addSeparator()
		act_fit=menu.addAction("Вписать в окно")
		act_1to1=menu.addAction("1:1 (физический размер)")
		rulers_text="Скрыть линейки"if self.widget.rulers_visible else"Показать линейки"
		act_rulers=menu.addAction(rulers_text)
		act_fit.triggered.connect(self.widget.fit_to_window)
		act_1to1.triggered.connect(self.widget.set_physical_size)
		act_rulers.triggered.connect(self.widget.toggle_rulers)
		menu.exec_(global_pos)
	def _request_create_legend(self):
		cb=getattr(self.widget,"request_create_legend",None)
		if callable(cb):
			cb(None)
	def _panel_menu(self,global_pos,panel_id:str):
		menu=QMenu(self)
		spec=self.widget.spec
		panel=spec.find_panel(panel_id)if spec is not None else None
		if panel is not None and panel.kind=="legend":
			act_add=menu.addAction("Добавить в легенду…")
			act_add.triggered.connect(lambda _c=False,p=panel_id:self._request_add_to_legend(p))
			menu.addSeparator()
		act_del=menu.addAction("Удалить (Del)")
		act_del.triggered.connect(lambda _c=False,p=panel_id:self.delete_panel_requested.emit(p))
		if panel is not None and panel.kind!="legend":
			menu.addSeparator()
			act_data=menu.addAction("Обновить данные из источника")
			act_style=menu.addAction("Обновить стиль из источника")
			act_live=menu.addAction("Включить живое обновление данных")
			act_data.triggered.connect(lambda _c=False,p=panel_id:self.refresh_data_requested.emit(p))
			act_style.triggered.connect(lambda _c=False,p=panel_id:self.refresh_style_requested.emit(p))
			act_live.triggered.connect(lambda _c=False,p=panel_id:self.enable_live_requested.emit(p))
			menu.addSeparator()
			act_add=menu.addAction("Создать легенду")
			act_add.triggered.connect(lambda _c=False,p=panel_id:self._request_create_legend_for(p))
		menu.addSeparator()
		act_layout=menu.addAction("Разложить по шаблону…")
		act_layout.triggered.connect(self.apply_layout_requested.emit)
		menu.exec_(global_pos)
	def _request_add_to_legend(self,panel_id):
		cb=getattr(self.widget,"request_add_to_legend",None)
		if callable(cb):
			cb(panel_id)
	def _request_create_legend_for(self,panel_id):
		cb=getattr(self.widget,"request_create_legend",None)
		if callable(cb):
			cb(panel_id)
	def _annotation_menu(self,global_pos,ann_id:str):
		menu=QMenu(self)
		act_del=menu.addAction("Удалить")
		act_props=menu.addAction("Свойства…")
		act_del.triggered.connect(lambda _c=False,a=ann_id:self.annotation_delete_requested.emit(a))
		act_props.triggered.connect(lambda _c=False,a=ann_id:self.annotation_properties.emit(a))
		menu.exec_(global_pos)


class _PagePreview(QWidget):
	def __init__(self,parent=None):
		super().__init__(parent)
		self._page_layout=None
		self._scale=1.0
		self.setAutoFillBackground(False)
	def set_page_layout(self,layout,scale:float)->None:
		self._page_layout=layout
		self._scale=float(scale)if scale and scale>0 else 1.0
		self.update()
	def paintEvent(self,event):
		if self._page_layout is None:
			return
		p=QPainter(self)
		try:
			p.fillRect(self.rect(),QColor("#808080"))
			layout=self._page_layout
			scale=self._scale
			page_rect=QRectF(0.0,0.0,float(self.width()),float(self.height()))
			p.fillRect(page_rect,QColor("#ffffff"))
			margin_px=float(layout.get("margin_mm",10.0))*scale
			if margin_px>0.5:
				p.setPen(QPen(QColor("#c8c8c8"),1,Qt.DashLine))
				p.setBrush(Qt.NoBrush)
				p.drawRect(QRectF(margin_px,margin_px,float(self.width())-2.0*margin_px,float(self.height())-2.0*margin_px))
		finally:
			p.end()


class PublicationCanvas(QWidget):
	panel_geometry_changed=pyqtSignal(str,float,float,float,float)
	panel_selected=pyqtSignal(str,bool)
	annotation_selected=pyqtSignal(str)
	annotation_geometry_changed=pyqtSignal(str,tuple)
	annotation_delete_requested=pyqtSignal(str)
	annotation_properties=pyqtSignal(str)
	selection_cleared=pyqtSignal()
	refresh_data_requested=pyqtSignal(str)
	refresh_style_requested=pyqtSignal(str)
	enable_live_requested=pyqtSignal(str)
	add_panel_requested=pyqtSignal()
	add_text_requested=pyqtSignal()
	add_arrow_requested=pyqtSignal()
	add_scale_bar_requested=pyqtSignal()
	add_bracket_requested=pyqtSignal()
	apply_layout_requested=pyqtSignal()
	delete_panel_requested=pyqtSignal(str)
	drag_finished=pyqtSignal()
	spec_changed=pyqtSignal()
	def __init__(self,parent=None):
		super().__init__(parent)
		self.spec=None
		self._zoom=1.0
		self._page_layout=None
		self._rulers_visible=True
		self._widget=_CanvasInner(self)
		self._page_preview=_PagePreview()
		self._center=QWidget()
		self._center.setStyleSheet("background-color: #808080;")
		self._page_preview.setParent(self._center)
		self._widget.setParent(self._center)
		self._scroll=QScrollArea()
		self._scroll.setWidgetResizable(True)
		self._scroll.setWidget(self._center)
		self._scroll.viewport().installEventFilter(self)
		for name in ("panel_geometry_changed","panel_selected","annotation_selected","annotation_geometry_changed","annotation_delete_requested","annotation_properties","selection_cleared","refresh_data_requested","refresh_style_requested","enable_live_requested","add_panel_requested","add_text_requested","add_arrow_requested","add_scale_bar_requested","add_bracket_requested","apply_layout_requested","delete_panel_requested","drag_finished","spec_changed",):
			getattr(self._widget,name).connect(getattr(self,name))
		self._hruler=_RulerWidget(Qt.Horizontal)
		self._vruler=_RulerWidget(Qt.Vertical)
		self._corner=QWidget()
		self._corner.setFixedSize(20,20)
		self._corner.setStyleSheet("background-color: #f0f0f0;")
		grid=QGridLayout(self)
		grid.setContentsMargins(0,0,0,0)
		grid.setSpacing(0)
		grid.addWidget(self._corner,0,0)
		grid.addWidget(self._hruler,0,1)
		grid.addWidget(self._vruler,1,0)
		grid.addWidget(self._scroll,1,1)
		self._scroll.horizontalScrollBar().valueChanged.connect(self._on_scroll_changed)
		self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)


	@property
	def rulers_visible(self)->bool:
		return self._rulers_visible
	def set_render_info(self,info:Optional[dict])->None:
		self._widget.set_render_info(info)
	def set_page_layout(self,layout:Optional[dict])->None:
		self._page_layout=layout
		self._update_fit_geometry()
	def eventFilter(self,obj,event):
		if obj is self._scroll.viewport():
			if event.type()==QEvent.Resize:
				QTimer.singleShot(0,self._update_fit_geometry)
			elif event.type()==QEvent.Wheel:
				if event.modifiers()&Qt.ControlModifier:
					delta=event.angleDelta().y()
					if delta!=0:
						factor=1.0015**delta
						self._apply_zoom_at(factor,event.pos())
						return True
		return super().eventFilter(obj,event)
	def _on_scroll_changed(self,*_):
		self._update_rulers()

	def _update_rulers(self)->None:
		if self._page_layout is None:
			return
		layout=self._page_layout
		page_w_mm=float(layout.get("width_mm",210.0))
		page_h_mm=float(layout.get("height_mm",297.0))
		page_px_w=self._page_preview.width()
		page_px_h=self._page_preview.height()
		if page_px_w<=0 or page_px_h<=0 or page_w_mm<=0 or page_h_mm<=0:
			return
		px_per_mm=page_px_w/page_w_mm
		vp=self._scroll.viewport().size()
		hbar=self._scroll.horizontalScrollBar()
		vbar=self._scroll.verticalScrollBar()
		off_x=-(hbar.value()-self._page_preview.x())
		off_y=-(vbar.value()-self._page_preview.y())
		self._hruler.set_geometry_info(page_w_mm,px_per_mm)
		self._vruler.set_geometry_info(page_h_mm,px_per_mm)
		self._hruler.set_offset(off_x)
		self._vruler.set_offset(off_y)

	def _update_fit_geometry(self)->None:
		if self.spec is None:
			return
		layout=self._page_layout or {"width_mm":210.0,"height_mm":297.0,"margin_mm":10.0,"columns":1,"column_gap_mm":5.0,"body_font_pt":8.0,}
		page_w_mm=float(layout["width_mm"])
		page_h_mm=float(layout["height_mm"])
		if page_w_mm<=0 or page_h_mm<=0:
			return
		vp=self._scroll.viewport().size()
		if vp.width()<=0 or vp.height()<=0:
			return
		aspect=page_h_mm/page_w_mm
		w=vp.width()
		h=int(w*aspect)
		if h>vp.height():
			h=vp.height()
			w=int(h/max(1e-9,aspect))
		w=max(1,w)
		h=max(1,h)
		w_px=max(1,int(round(w*self._zoom)))
		h_px=max(1,int(round(h*self._zoom)))
		scale=w_px/page_w_mm
		margin_mm=float(layout.get("margin_mm",10.0))
		margin_px=margin_mm*scale
		content_w_px=max(1.0,w_px-2.0*margin_px)
		content_h_px=max(1.0,h_px-2.0*margin_px)
		cw=max(vp.width(),w_px)
		ch=max(vp.height(),h_px)
		offset_x=max(0,(cw-w_px)//2)
		offset_y=max(0,(ch-h_px)//2)
		self._center.setMinimumSize(cw,ch)
		self._center.setMaximumSize(cw,ch)
		self._page_preview.setGeometry(offset_x,offset_y,w_px,h_px)
		self._page_preview.set_page_layout(layout,scale)
		self._widget.setGeometry(int(offset_x+margin_px),int(offset_y+margin_px),int(content_w_px),int(content_h_px))
		self._widget.raise_()
		self._update_rulers()

	def _cursor_image_pos(self,cursor_vp_pos):
		w=self._page_preview.width()
		h=self._page_preview.height()
		vp=self._scroll.viewport().size()
		hbar=self._scroll.horizontalScrollBar()
		vbar=self._scroll.verticalScrollBar()
		if w>vp.width():
			cx=hbar.value()+cursor_vp_pos.x()
		else:
			cx=cursor_vp_pos.x()-(vp.width()-w)/2.0
		if h>vp.height():
			cy=vbar.value()+cursor_vp_pos.y()
		else:
			cy=cursor_vp_pos.y()-(vp.height()-h)/2.0
		return cx,cy
	def _apply_zoom_at(self,factor:float,cursor_vp_pos)->None:
		if self.spec is None or self._page_layout is None:
			return
		old_w=self._page_preview.width()
		old_h=self._page_preview.height()
		if old_w<=0 or old_h<=0:
			return
		cx,cy=self._cursor_image_pos(cursor_vp_pos)
		fx=cx/old_w
		fy=cy/old_h
		new_zoom=max(0.25,min(8.0,self._zoom*factor))
		if abs(new_zoom-self._zoom)<1e-9:
			return
		self._zoom=new_zoom
		self._update_fit_geometry()
		new_w=self._page_preview.width()
		new_h=self._page_preview.height()
		vp=self._scroll.viewport().size()
		hbar=self._scroll.horizontalScrollBar()
		vbar=self._scroll.verticalScrollBar()
		if new_w>vp.width():
			hbar.setValue(int(fx*new_w-cursor_vp_pos.x()))
		if new_h>vp.height():
			vbar.setValue(int(fy*new_h-cursor_vp_pos.y()))
	def fit_to_window(self)->None:
		self._zoom=1.0
		self._update_fit_geometry()
	def set_physical_size(self)->None:
		if self.spec is None or self._page_layout is None:
			return
		page_w_mm=float(self._page_layout.get("width_mm",210.0))
		page_h_mm=float(self._page_layout.get("height_mm",297.0))
		vp=self._scroll.viewport().size()
		if vp.width()<=0 or vp.height()<=0 or page_w_mm<=0 or page_h_mm<=0:
			return
		aspect=page_h_mm/page_w_mm
		w=vp.width()
		h=int(w*aspect)
		if h>vp.height():
			h=vp.height()
			w=int(h/max(1e-9,aspect))
		w=max(1,w)
		base_px_per_mm=w/page_w_mm
		screen=QApplication.primaryScreen()
		if screen is None:
			return
		physical_dpi=float(screen.physicalDotsPerInch())
		if physical_dpi<=0:
			return
		target=physical_dpi/(base_px_per_mm*25.4/96.0)
		self._zoom=max(0.25,min(8.0,target))
		self._update_fit_geometry()
	def toggle_rulers(self)->None:
		self._rulers_visible= not self._rulers_visible
		self._corner.setVisible(self._rulers_visible)
		self._hruler.setVisible(self._rulers_visible)
		self._vruler.setVisible(self._rulers_visible)
	def set_spec(self,spec)->None:
		self.spec=spec
		self._widget.set_selected_panels([])
		self._update_fit_geometry()
	def set_selected_panels(self,panel_ids:list)->None:
		self._widget.set_selected_panels(panel_ids)
	def set_figure(self,figure)->None:
		self._widget.set_figure(figure)
		self._update_fit_geometry()
	def resizeEvent(self,event):
		super().resizeEvent(event)
		QTimer.singleShot(0,self._update_fit_geometry)
	def request_create_legend(self,panel_id:Optional[str])->None:
		cb=getattr(self,"on_request_create_legend",None)
		if callable(cb):
			cb(panel_id)
	def request_add_to_legend(self,panel_id:str)->None:
		cb=getattr(self,"on_request_add_to_legend",None)
		if callable(cb):
			cb(panel_id)