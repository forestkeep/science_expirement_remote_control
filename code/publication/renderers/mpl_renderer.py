from __future__ import annotations
import logging
from typing import Any, Callable, Dict, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib import font_manager
from .base import RendererAdapter
from matplotlib.patches import Rectangle
from .helpers import qt_style_to_mpl, line_width_pt
from .colors import resolve_line_color
from ..core.units import mm_to_inch, panel_rect_to_figure_fraction
from ..core.sentinel import MISSING
from ..contract import get_attr, Origin

logger = logging.getLogger(__name__)

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["axes.unicode_minus"] = False

_MPL_LINESTYLES = {
	"Solid": "-", "Dash": (0, (4, 2)), "Dot": (0, (1, 3)),
	"DashDot": (0, (4, 2, 1, 2)), "DashDotDot": (0, (4, 2, 1, 2, 1, 2)),
}


def _style_name_to_mpl(name: str):
	if not name:
		return "-"
	return _MPL_LINESTYLES.get(str(name), "-")


def _slot_overrides(slot) -> dict:
	return getattr(slot, "style_overrides", None) or {}


def _resolve_font_family(name: str) -> str:
	try:
		font_manager.findfont(name, fallback_to_default=False)
		return name
	except Exception:
		return "DejaVu Sans"


def _contract_fallback(key: str):
	try:
		return get_attr(key).fallback
	except KeyError:
		logger.warning("_contract_fallback: %r отсутствует в CONTRACT", key)
		return None


class MatplotlibRenderer(RendererAdapter):
	def create_figure(self, spec) -> Figure:
		fig = Figure(figsize=(mm_to_inch(spec.width_mm), mm_to_inch(spec.height_mm)), dpi=100)
		FigureCanvasAgg(fig)
		return fig

	def get_native_size_px(self, figure_handle: Figure, dpi: float) -> tuple:
		w_in, h_in = figure_handle.get_size_inches()
		return int(round(w_in * dpi)), int(round(h_in * dpi))

	def render(self, fig, spec, data_resolver, style_resolver, overrides_resolver) -> Dict[str, Any]:
		fig.clear()
		bg = style_resolver("figure.background")
		if bg is MISSING:
			bg = _contract_fallback("figure.background")
		fig.patch.set_facecolor(bg)

		hide_legend_sources = set()
		for lp in spec.sorted_panels():
			if not lp.visible or lp.kind != "legend":
				continue
			if bool(lp.style_overrides.get("legend.hide_sources", True)):
				hide_legend_sources.update(lp.source_panels or [])
				for pid, _sidx in (lp.source_slots or []):
					hide_legend_sources.add(pid)

		axes_by_panel: Dict[str, tuple] = {}
		handles_by_panel: Dict[str, Dict[int, Any]] = {}

		# проход 1: plot-панели
		for panel in spec.sorted_panels():
			if not panel.visible or panel.kind == "legend":
				continue
			result = self._render_panel(
				fig, spec, panel, data_resolver, style_resolver,
				handles_by_panel=handles_by_panel,
				hide_legend=panel.id in hide_legend_sources,
			)
			if result is not None:
				axes_by_panel[panel.id] = result

		# data-bound аннотации
		for panel in spec.sorted_panels():
			if not panel.visible or panel.kind == "legend":
				continue
			entry = axes_by_panel.get(panel.id)
			if entry is None:
				continue
			ax, ax2, panel_obj = entry
			for slot in panel_obj.curves:
				if not slot.visible:
					continue
				data = data_resolver(panel_obj, slot.data_ref)
				if not data:
					continue
				style_snap = data.get("style")
				if style_snap is None:
					continue
				for ann in data.get("panel_annotations", []) or []:
					ov = overrides_resolver(ann["id"])
					if ov is not None and getattr(ov, "visible_override", None) is False:
						continue
					target = ax if slot.axis == "y1" else (ax2 or ax)
					self._render_data_bound(target, ann, ov, style_resolver)

		# проход 2: legend-панели
		legends_info: Dict[str, Dict[str, float]] = {}
		for panel in spec.sorted_panels():
			if not panel.visible or panel.kind != "legend":
				continue
			rect = self._render_legend_panel(
				fig, spec, panel, handles_by_panel, axes_by_panel, style_resolver,
			)
			if rect is not None:
				legends_info[panel.id] = rect

		# проход 3: презентационные аннотации
		for ann in sorted(spec.presentation_annotations, key=lambda a: (int(a.z), a.id)):
			if not ann.visible:
				continue
			self._render_presentation(fig, spec, ann, axes_by_panel, style_resolver)

		return {"legends": legends_info}

	# ---------- plot-панель ----------

	def _render_panel(self, fig, spec, panel, data_resolver, style_resolver,
					  handles_by_panel: Optional[Dict[str, Dict[int, Any]]] = None,
					  hide_legend: bool = False):
		x, y, w, h = panel_rect_to_figure_fraction(
			panel.x_mm, panel.y_mm, panel.w_mm, panel.h_mm,
			spec.width_mm, spec.height_mm,
		)
		if w <= 0 or h <= 0:
			return None
		tick_size = style_resolver("figure.axes.tick_size")
		if tick_size is MISSING:
			tick_size = _contract_fallback("axes.tick_size") or 7.0
		label_size = style_resolver("figure.axes.label_size")
		if label_size is MISSING:
			label_size = _contract_fallback("axes.label_size") or 8.0
		tick_in = float(tick_size) / 72.0
		label_in = float(label_size) / 72.0
		fig_w_in, fig_h_in = fig.get_size_inches()
		left_margin = ((tick_in * 2.5 + label_in * 1.5) / fig_w_in
					   if panel.y_label else (tick_in * 2.5) / fig_w_in)
		bottom_margin = ((tick_in * 1.5 + label_in * 1.5) / fig_h_in
						 if panel.x_label else (tick_in * 1.5) / fig_h_in)
		if panel.y2_visible:
			right_margin = ((tick_in * 2.5 + label_in * 1.5) / fig_w_in
							if panel.y2_label else (tick_in * 2.5) / fig_w_in)
		else:
			right_margin = 0.0
		top_margin = (label_in * 1.5) / fig_h_in if panel.title else 0.0
		if left_margin + right_margin >= w or bottom_margin + top_margin >= h:
			left_margin = right_margin = bottom_margin = top_margin = 0.0
		ix = x + left_margin
		iy = y + bottom_margin
		iw = w - left_margin - right_margin
		ih = h - bottom_margin - top_margin
		if iw <= 0 or ih <= 0:
			return None

		ax = fig.add_axes([ix, iy, iw, ih])
		axes_lw = style_resolver("figure.axes.line_width")
		if axes_lw is MISSING:
			axes_lw = _contract_fallback("axes.line_width")
		font_family = style_resolver("figure.font.family")
		if font_family is MISSING:
			font_family = _contract_fallback("font.family")
		font_family = _resolve_font_family(font_family)
		for spine in ax.spines.values():
			spine.set_linewidth(float(axes_lw))
		ax.tick_params(labelsize=float(tick_size), width=float(axes_lw))
		ax2 = None
		if panel.y2_visible:
			ax2 = ax.twinx()
			for spine in ax2.spines.values():
				spine.set_linewidth(float(axes_lw))
			ax2.tick_params(labelsize=float(tick_size), width=float(axes_lw))
		ax.get_xaxis().set_visible(bool(panel.style_overrides.get("axis.x.visible", True)))
		ax.get_yaxis().set_visible(bool(panel.style_overrides.get("axis.y1.visible", True)))
		if ax2 is not None:
			ax2.get_yaxis().set_visible(
				bool(panel.style_overrides.get("axis.y2.visible", panel.y2_visible))
			)

		any_curve = False
		for idx, slot in enumerate(panel.curves):
			if not slot.visible:
				continue
			data = data_resolver(panel, slot.data_ref)
			if data is None:
				logger.warning("_render_panel: пустые данные для панели %s, слот %d", panel.id, idx)
				continue
			target_ax = ax if slot.axis == "y1" else (ax2 or ax)
			style_snap = data.get("style")
			line_style = getattr(style_snap, "line_style", None) if style_snap else None
			if data.get("orphan"):
				target_ax.text(0.5, 0.5, "(источник не найден)", ha="center", va="center",
							   transform=target_ax.transAxes,
							   fontsize=float(label_size), color="#a02020")
				any_curve = True
				continue
			handle = self._plot_curve(
				target_ax, slot, data, idx, panel, style_resolver, line_style,
			)
			if handle is not None and handles_by_panel is not None:
				handles_by_panel.setdefault(panel.id, {})[idx] = handle
			if style_snap is not None:
				self._plot_uncertainty(target_ax, slot, data, panel)
				self._plot_artifacts(target_ax, slot, data, panel)
			any_curve = True

		if not any_curve:
			ax.text(0.5, 0.5, "(no data)", ha="center", va="center",
					transform=ax.transAxes, fontsize=float(label_size), color="#999999")

		if panel.x_range:
			ax.set_xlim(*panel.x_range)
		if panel.y_range:
			ax.set_ylim(*panel.y_range)
		if ax2 is not None and panel.y2_range:
			ax2.set_ylim(*panel.y2_range)
		if panel.x_log:
			ax.set_xscale("log")
		if panel.y_log:
			ax.set_yscale("log")
		if ax2 is not None and panel.y2_log:
			ax2.set_yscale("log")
		if panel.x_label:
			ax.set_xlabel(panel.x_label, fontsize=float(label_size), family=font_family)
		if panel.y_label:
			ax.set_ylabel(panel.y_label, fontsize=float(label_size), family=font_family)
		if ax2 is not None and panel.y2_label:
			ax2.set_ylabel(panel.y2_label, fontsize=float(label_size), family=font_family)

		legend_enabled = style_resolver("legend.enabled")
		if legend_enabled is MISSING:
			legend_enabled = _contract_fallback("legend.enabled")
		legend_fs = style_resolver("legend.font_size")
		if legend_fs is MISSING:
			legend_fs = _contract_fallback("legend.font_size")
		if bool(legend_enabled) and any_curve and not hide_legend:
			try:
				handles, labels = ax.get_legend_handles_labels()
				if ax2 is not None:
					h2, l2 = ax2.get_legend_handles_labels()
					handles += h2
					labels += l2
				if handles:
					ax.legend(handles, labels, fontsize=float(legend_fs),
							  frameon=False, loc="best")
			except Exception:
				logger.exception("legend add failed")

		if panel.title:
			title_size = style_resolver("panel.title_size")
			if title_size is MISSING:
				title_size = 9.0
			ax.set_title(panel.title, fontsize=float(title_size), family=font_family)

		return (ax, ax2, panel)

	# ---------- legend-панель ----------

	def _render_legend_panel(self,fig,spec,panel,handles_by_panel,axes_by_panel,style_resolver):
		x,y,w,h=panel_rect_to_figure_fraction(panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm,spec.width_mm,spec.height_mm,)
		if w<=0 or h<=0:
			return None
		overlay_ax=fig.add_axes([x,y,w,h],frameon=False)
		overlay_ax.axis("off")
		overlay_ax.set_zorder(1000+int(panel.z or 0))
		def _collect_for_pid(pid:str):
			src_panel=spec.find_panel(pid)
			n_slots=len(src_panel.curves)if src_panel is not None else 0
			hdict=handles_by_panel.get(pid,{}) or {}
			out=[]
			if hdict:
				for sidx in sorted(hdict.keys()):
					handle=hdict[sidx]
					lbl=self._label_for_handle(handle,pid,sidx,spec)
					out.append((sidx,handle,lbl))
				return out
			entry=axes_by_panel.get(pid)
			if entry is None:
				return out
			ax=entry[0]
			try:
				lines=list(ax.get_lines())
			except Exception:
				lines=[]
			if not lines:
				return out
			limit=n_slots if n_slots>0 else len(lines)
			for sidx,ln in enumerate(lines[:limit]):
				lbl=self._label_for_handle(ln,pid,sidx,spec)
				out.append((sidx,ln,lbl))
			return out
		handles=[]
		labels=[]
		seen_keys=set()
		for pid in panel.source_panels or []:
			for sidx,handle,label in _collect_for_pid(pid):
				key=(pid,sidx)
				if key in seen_keys:
					continue
				seen_keys.add(key)
				handles.append(handle)
				labels.append(label)
		for pid,sidx in panel.source_slots or []:
			sidx=int(sidx)
			key=(pid,sidx)
			if key in seen_keys:
				continue
			seen_keys.add(key)
			handle=(handles_by_panel.get(pid,{}) or {}).get(sidx)
			if handle is None:
				entry=axes_by_panel.get(pid)
				if entry is not None:
					try:
						lines=list(entry[0].get_lines())
					except Exception:
						lines=[]
					if 0<=sidx<len(lines):
						handle=lines[sidx]
			if handle is None:
				continue
			label=self._label_for_handle(handle,pid,sidx,spec)
			handles.append(handle)
			labels.append(label)
		fs=style_resolver("legend.font_size")
		if fs is MISSING:
			fs=_contract_fallback("legend.font_size") or 7.0
		font_size=float(panel.style_overrides.get("legend.font_size",fs))
		frameon=bool(panel.style_overrides.get("legend.frameon",False))
		if not handles:
			txt=overlay_ax.text(0.5,0.5,"(нет источника)",ha="center",va="center",transform=overlay_ax.transAxes,fontsize=font_size,color="#999999")
			fig.canvas.draw()
			renderer=fig.canvas.get_renderer()
			bbox=txt.get_window_extent(renderer)
			bbox_in=bbox.transformed(fig.dpi_scale_trans.inverted())
			new_w_mm=max(2.0,float(bbox_in.width)*25.4)
			new_h_mm=max(2.0,float(bbox_in.height)*25.4)
			panel.w_mm=new_w_mm
			panel.h_mm=new_h_mm
			nx,ny,nw,nh=panel_rect_to_figure_fraction(panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm,spec.width_mm,spec.height_mm,)
			if nw>0 and nh>0:
				overlay_ax.set_position([nx,ny,nw,nh])
			if frameon:
				rect=Rectangle((0.0,0.0),1.0,1.0,transform=overlay_ax.transAxes,facecolor="none",edgecolor="black",linewidth=1.0,clip_on=False,)
				overlay_ax.add_patch(rect)
			return {"x_mm":float(panel.x_mm),"y_mm":float(panel.y_mm),"w_mm":float(panel.w_mm),"h_mm":float(panel.h_mm),}
		dedupe=bool(panel.style_overrides.get("legend.dedupe",True))
		if dedupe:
			seen_labels=set()
			nh_,nl_=[],[]
			for hnd,lbl in zip(handles,labels):
				if lbl in seen_labels:
					continue
				seen_labels.add(lbl)
				nh_.append(hnd)
				nl_.append(lbl)
			handles,labels=nh_,nl_
		legend_kwargs=dict(loc="center",frameon=frameon,fontsize=font_size)
		if frameon:
			legend_kwargs["framealpha"]=1.0
			legend_kwargs["facecolor"]="white"
			legend_kwargs["edgecolor"]="black"
		legend=overlay_ax.legend(handles,labels,**legend_kwargs)
		fig.canvas.draw()
		renderer=fig.canvas.get_renderer()
		bbox=legend.get_window_extent(renderer)
		bbox_in=bbox.transformed(fig.dpi_scale_trans.inverted())
		new_w_mm=max(2.0,float(bbox_in.width)*25.4)
		new_h_mm=max(2.0,float(bbox_in.height)*25.4)
		panel.w_mm=new_w_mm
		panel.h_mm=new_h_mm
		nx,ny,nw,nh=panel_rect_to_figure_fraction(panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm,spec.width_mm,spec.height_mm,)
		if nw>0 and nh>0:
			overlay_ax.set_position([nx,ny,nw,nh])
		return {"x_mm":float(panel.x_mm),"y_mm":float(panel.y_mm),"w_mm":float(panel.w_mm),"h_mm":float(panel.h_mm),}



	@staticmethod
	def _label_for_handle(handle, pid: str, sidx: int, spec) -> str:
		try:
			lbl = handle.get_label()
		except Exception:
			lbl = None
		if lbl and not str(lbl).startswith("_"):
			return str(lbl)
		panel = spec.find_panel(pid)
		if panel is not None and 0 <= sidx < len(panel.curves):
			slot = panel.curves[sidx]
			if slot.legend_label:
				return str(slot.legend_label)
			if slot.data_ref is not None:
				data = getattr(slot.data_ref, "data", None)
				if data is not None and getattr(data, "curve_name", ""):
					return str(data.curve_name)
				if slot.data_ref.series_root_name:
					return str(slot.data_ref.series_root_name)
		return f"{pid} #{sidx + 1}"

	
	def _measure_legend_rect(self, fig, legend, panel) -> dict:
		try:
			fig.canvas.draw()
			renderer = fig.canvas.get_renderer()
			bbox = legend.get_window_extent(renderer)
			bbox_in = bbox.transformed(fig.dpi_scale_trans.inverted())
			fig_h_in = fig.get_size_inches()[1]
			return {
				"x_mm": float(bbox_in.x0) * 25.4,
				"y_mm": float(fig_h_in - bbox_in.y1) * 25.4,
				"w_mm": float(bbox_in.width) * 25.4,
				"h_mm": float(bbox_in.height) * 25.4,
			}
		except Exception:
			logger.exception("legend rect measure failed")
			return {
				"x_mm": float(panel.x_mm), "y_mm": float(panel.y_mm),
				"w_mm": float(panel.w_mm), "h_mm": float(panel.h_mm),
			}

	def _measure_axes_rect(self, fig, overlay_ax, panel) -> dict:
		# При отсутствии handles геометрию оцениваем по bbox осей
		try:
			fig.canvas.draw()
			renderer = fig.canvas.get_renderer()
			bbox = overlay_ax.get_window_extent(renderer)
			bbox_in = bbox.transformed(fig.dpi_scale_trans.inverted())
			fig_h_in = fig.get_size_inches()[1]
			return {
				"x_mm": float(bbox_in.x0) * 25.4,
				"y_mm": float(fig_h_in - bbox_in.y1) * 25.4,
				"w_mm": float(bbox_in.width) * 25.4,
				"h_mm": float(bbox_in.height) * 25.4,
			}
		except Exception:
			return {
				"x_mm": float(panel.x_mm), "y_mm": float(panel.y_mm),
				"w_mm": float(panel.w_mm), "h_mm": float(panel.h_mm),
			}
	# ------------------------------------------------------------ curve
	def _plot_curve(self, target_ax, slot, data, index, panel, style_resolver, line_style):
		from ..contract import get_attr as _get
		overrides = _slot_overrides(slot)
		color_override = overrides.get("line.color", MISSING)
		if color_override is not MISSING and color_override not in (None, ""):
			color = str(color_override)
		else:
			try:
				color = resolve_line_color(slot, index, panel, line_style)
			except Exception:
				color = _get("line.color").fallback
		lw_default = style_resolver("figure.line.width")
		if lw_default is MISSING:
			lw_default = 1.0
		width_override = overrides.get("line.width", MISSING)
		if width_override is not MISSING:
			try:
				lw = max(0.1, float(width_override))
			except (TypeError, ValueError):
				lw = line_width_pt(line_style, float(lw_default))
		else:
			lw = line_width_pt(line_style, float(lw_default))
		style_override = overrides.get("line.style", MISSING)
		if style_override is not MISSING:
			ls = _style_name_to_mpl(str(style_override))
		else:
			ls = qt_style_to_mpl(getattr(line_style, "line_style", None) if line_style else None)
		marker_override = overrides.get("marker.symbol", MISSING)
		if marker_override is not MISSING:
			marker = marker_override if marker_override not in ("", None) else None
		else:
			marker = getattr(line_style, "symbol", None) if line_style else None
		size_override = overrides.get("marker.size", MISSING)
		if size_override is not MISSING:
			try:
				ms = float(size_override)
			except (TypeError, ValueError):
				ms = float(_get("marker.size").fallback)
		elif line_style is not None:
			ms = float(getattr(line_style, "symbol_size", _get("marker.size").fallback))
		else:
			ms = float(_get("marker.size").fallback)
		face_override = overrides.get("marker.face", MISSING)
		if face_override is not MISSING and face_override not in (None, ""):
			mfc = str(face_override)
		elif line_style is not None:
			mfc = str(getattr(line_style, "fill_color", _get("marker.face").fallback))
		else:
			mfc = str(_get("marker.face").fallback)
		edge_override = overrides.get("marker.edge", MISSING)
		if edge_override is not MISSING and edge_override not in (None, ""):
			mec = str(edge_override)
		elif line_style is not None:
			mec = str(getattr(line_style, "symbol_color", _get("marker.edge").fallback))
		else:
			mec = str(_get("marker.edge").fallback)
		mew = max(0.5, float(lw))
		label = slot.legend_label or data.get("curve_name", "")
		xs = data.get("x")
		ys = data.get("y")
		if xs is None or ys is None or len(xs) == 0:
			return None
		lines = target_ax.plot(
			xs, ys,
			color=color, linewidth=float(lw), linestyle=ls,
			marker=marker, markersize=ms,
			markerfacecolor=mfc, markeredgecolor=mec, markeredgewidth=mew,
			label=label, zorder=2,
		)
		return lines[0] if lines else None

	# ------------------------------------------------------- uncertainty
	def _plot_uncertainty(self, target_ax, slot, data, panel):
		if not panel.show_tools.get("uncertainty.estimate", False):
			return
		style_snap = data.get("style")
		if style_snap is None:
			return
		records = getattr(style_snap, "uncertainty_records", []) or []
		if not records:
			return

		xs = np.asarray(data.get("x"), dtype=float)
		ys = np.asarray(data.get("y"), dtype=float)
		if xs.size == 0:
			return

		line_style = getattr(style_snap, "line_style", None)
		overrides = _slot_overrides(slot)
		color_override = overrides.get("line.color", MISSING)
		if color_override is not MISSING and color_override not in (None, ""):
			base_color = str(color_override)
		else:
			base_color = str(getattr(line_style, "color", "#333333")) if line_style else "#333333"

		for rec in records:
			yerr_raw = getattr(rec, "y_err", None)
			if yerr_raw is None:
				continue
			yerr = np.asarray(yerr_raw, dtype=float)
			if yerr.size != ys.size:
				continue
			style = dict(getattr(rec, "style", {}) or {})
			mode = style.get("mode", "bars")
			alpha = int(style.get("alpha", 180))
			width = int(style.get("width", 1))
			cap = int(style.get("cap_size", 6))
			color = style.get("color", "auto")
			if not color or color == "auto":
				color = base_color

			if mode == "shaded":
				target_ax.fill_between(
					xs, ys - yerr, ys + yerr,
					color=color,
					alpha=max(0.05, alpha / 255.0 * 0.5),
					zorder=1,
				)
			elif mode == "line":
				target_ax.plot(
					xs, ys + yerr, color=color, linewidth=width,
					linestyle=":", zorder=1,
				)
				target_ax.plot(
					xs, ys - yerr, color=color, linewidth=width,
					linestyle=":", zorder=1,
				)
			elif mode == "caps":
				if cap > 0:
					target_ax.errorbar(
						xs, ys, yerr=yerr, fmt="none",
						ecolor=color, elinewidth=width,
						capsize=cap / 2.0, zorder=1,
					)
			else:  # bars
				target_ax.errorbar(
					xs, ys, yerr=yerr, fmt="none",
					ecolor=color, elinewidth=width, capsize=0, zorder=1,
				)

	# --------------------------------------------------------- artifacts
	def _plot_artifacts(self, target_ax, slot, data, panel):
		style_snap = data.get("style")
		if style_snap is None:
			return
		artifacts = getattr(style_snap, "artifacts", []) or []
		if not artifacts:
			return

		line_style = getattr(style_snap, "line_style", None)
		overrides = _slot_overrides(slot)
		color_override = overrides.get("line.color", MISSING)
		if color_override is not MISSING and color_override not in (None, ""):
			base_color = str(color_override)
		else:
			base_color = str(getattr(line_style, "color", "#1f77b4")) if line_style else "#1f77b4"

		# Артефакт, временно запрошенный пользователем через «показать»
		# в инспекторе кривой. Рисуется акцентным цветом поверх остальных,
		# игнорируя panel.show_tools.
		highlight_tool = slot.style_overrides.get("__highlight_tool__")
		highlight_color = "#ff2ecc"

		for art in artifacts:
			tool_id = getattr(art, "tool_id", "")
			is_highlight = (tool_id == highlight_tool)

			if not is_highlight and not panel.show_tools.get(tool_id, False):
				continue

			payload = getattr(art, "payload", None)
			if payload is None:
				continue

			kind = getattr(payload, "kind", None)
			if kind in ("attached", "domain"):
				continue

			color = highlight_color if is_highlight else base_color
			width = 2.4 if is_highlight else 0.75
			zorder = 6 if is_highlight else 3
			linestyle = "-" if is_highlight else (0, (4, 2))

			if kind == "overlay":
				xs_list = getattr(payload, "x", []) or []
				ys_list = getattr(payload, "y", []) or []
				for xarr, yarr in zip(xs_list, ys_list):
					try:
						xa = np.asarray(xarr, dtype=float)
						ya = np.asarray(yarr, dtype=float)
					except (TypeError, ValueError):
						continue
					if xa.size == 0 or xa.size != ya.size:
						continue
					target_ax.plot(
						xa, ya,
						color=color,
						linewidth=width,
						linestyle=linestyle,
						zorder=zorder,
					)

			elif kind == "annotation":
				points = getattr(payload, "points", []) or []
				if not points:
					continue
				px = []
				py = []
				for p in points:
					try:
						px.append(float(p.get("x", 0.0)))
						py.append(float(p.get("y", 0.0)))
					except (TypeError, ValueError):
						continue
				if not px:
					continue
				label_kind = getattr(payload, "label", "peaks")
				marker = "+" if label_kind in ("peaks", "valleys") else "o"
				marker_size = 12 if is_highlight else 8
				target_ax.plot(
					px, py,
					linestyle="None",
					marker=marker,
					markersize=marker_size,
					markeredgewidth=1.4 if is_highlight else 1.0,
					color=color,
					zorder=zorder,
				)

			elif kind == "uncertainty":
				# uncertainty.estimate рисуется отдельно в _plot_uncertainty,
				# здесь не дублируем.
				continue

	# -------------------------------------------------- data-bound annotations
	def _render_data_bound(self, ax, ann, override, style_resolver):
		x = ann.get("x")
		y = ann.get("y")
		if x is None or y is None:
			return
		if override is not None and override.position_override:
			x, y = override.position_override
		label = ann.get("label", "") or ""
		kind = (ann.get("annotation_kind") or "").split(".")[-1]
		marker = "+" if kind in ("peaks", "valleys") else "o"
		size = style_resolver("annotation.text_size")
		if size is MISSING:
			size = _contract_fallback("annotation.text_size") or 8.0
		if override is not None:
			size = override.style_override.get("size", size)
		ax.plot(
			[x], [y], marker=marker, linestyle="None",
			markersize=float(size) * 0.6, color="#d62728",
		)
		if label:
			ax.annotate(
				label, (x, y), textcoords="offset points",
				xytext=(4, 4), fontsize=float(size) * 0.8,
				color="#333333",
			)

	# -------------------------------------------------- presentation-only
	def _render_presentation(self, fig, spec, ann, axes_by_panel, style_resolver):
		kind = ann.kind
		if kind == "panel_label":
			self._render_panel_label(fig, spec, ann, axes_by_panel, style_resolver)
		elif kind == "scale_bar":
			self._render_scale_bar(fig, spec, ann, axes_by_panel, style_resolver)
		elif kind == "bracket":
			self._render_bracket(fig, spec, ann, axes_by_panel, style_resolver)
		elif kind == "arrow":
			self._render_arrow(fig, spec, ann, axes_by_panel, style_resolver)
		else:
			self._render_text(fig, spec, ann, axes_by_panel, style_resolver)

	@staticmethod
	def _mm_to_fig_xy(spec, x_mm, y_mm):
		return x_mm / spec.width_mm, 1.0 - y_mm / spec.height_mm

	@staticmethod
	def _mm_to_axes_xy(panel, x_mm, y_mm):
		ax_x = x_mm / panel.w_mm if panel.w_mm > 0 else 0.0
		ax_y = 1.0 - (y_mm / panel.h_mm if panel.h_mm > 0 else 0.0)
		return ax_x, ax_y

	def _font_kwargs(self, ann, style_resolver, size_key="annotation.text_size"):
		size = style_resolver(size_key)
		if size is MISSING:
			size = _contract_fallback(size_key) or 8.0
		family = style_resolver("figure.font.family")
		if family is MISSING:
			family = _contract_fallback("font.family") or "DejaVu Sans"
		family = _resolve_font_family(family)
		overrides = ann.style or {}
		return {
			"fontsize": float(overrides.get("size", size)),
			"family": family,
			"weight": str(overrides.get("weight", "normal")),
			"color": str(overrides.get("color", "black")),
		}

	def _render_text(self, fig, spec, ann, axes_by_panel, style_resolver):
		kw = self._font_kwargs(ann, style_resolver)
		if ann.coordinate_space == "figure_mm" and len(ann.coords) >= 2:
			fx, fy = self._mm_to_fig_xy(spec, ann.coords[0], ann.coords[1])
			fig.text(fx, fy, ann.text, ha="left", va="top", **kw)
		elif ann.coordinate_space == "panel_mm":
			entry = axes_by_panel.get(ann.panel_id)
			if entry is None or len(ann.coords) < 2:
				return
			ax, _ax2, panel = entry
			ax_x, ax_y = self._mm_to_axes_xy(panel, ann.coords[0], ann.coords[1])
			ax.text(ax_x, ax_y, ann.text, ha="left", va="top",
					transform=ax.transAxes, **kw)
		elif ann.coordinate_space == "axes_data":
			entry = axes_by_panel.get(ann.panel_id)
			if entry is None or len(ann.coords) < 2:
				return
			ax, _ax2, _ = entry
			ax.text(ann.coords[0], ann.coords[1], ann.text, ha="left", va="top", **kw)

	def _render_panel_label(self, fig, spec, ann, axes_by_panel, style_resolver):
		entry = axes_by_panel.get(ann.panel_id)
		if entry is None:
			return
		ax, _ax2, panel = entry
		dx = ann.coords[0] if len(ann.coords) > 0 else -10.0
		dy = ann.coords[1] if len(ann.coords) > 1 else -2.0
		ax_x, ax_y = self._mm_to_axes_xy(panel, dx, dy)
		kw = self._font_kwargs(ann, style_resolver)
		kw["weight"] = kw.get("weight") or "bold"
		ax.text(ax_x, ax_y, ann.text or "a", ha="right", va="top",
				transform=ax.transAxes, **kw)

	def _render_scale_bar(self, fig, spec, ann, axes_by_panel, style_resolver):
		entry = axes_by_panel.get(ann.panel_id)
		if entry is None:
			return
		ax, _ax2, panel = entry
		width_mm = float(ann.style.get(
			"width_mm",
			style_resolver("annotation.scalebar.width_mm")
			if style_resolver("annotation.scalebar.width_mm") is not MISSING else 5.0,
		))
		thickness_pt = float(ann.style.get(
			"thickness_pt",
			style_resolver("annotation.scalebar.thickness_pt")
			if style_resolver("annotation.scalebar.thickness_pt") is not MISSING else 0.6,
		))
		x_mm = float(ann.coords[0]) if len(ann.coords) > 0 else 3.0
		y_mm = float(ann.coords[1]) if len(ann.coords) > 1 else panel.h_mm - 3.0
		x0, y0 = self._mm_to_axes_xy(panel, x_mm, y_mm)
		x1, _ = self._mm_to_axes_xy(panel, x_mm + width_mm, y_mm)
		ax.plot(
			[x0, x1], [y0, y0], color="black", lw=thickness_pt,
			transform=ax.transAxes, clip_on=False, solid_capstyle="butt",
		)
		if ann.text:
			ax.text(
				(x0 + x1) / 2.0, y0 - 0.03, ann.text,
				ha="center", va="top",
				transform=ax.transAxes,
				fontsize=float(ann.style.get("size", 7.0)),
			)

	def _render_bracket(self, fig, spec, ann, axes_by_panel, style_resolver):
		entry = axes_by_panel.get(ann.panel_id)
		if entry is None or len(ann.coords) < 4:
			return
		ax, _ax2, panel = entry
		x1_mm, y1_mm, x2_mm, y2_mm = ann.coords[:4]
		a0 = self._mm_to_axes_xy(panel, x1_mm, y1_mm)
		a1 = self._mm_to_axes_xy(panel, x2_mm, y2_mm)
		thickness = float(ann.style.get(
			"thickness_pt",
			style_resolver("annotation.bracket.width_pt")
			if style_resolver("annotation.bracket.width_pt") is not MISSING else 0.6,
		))
		ax.plot(
			[a0[0], a0[0], a1[0], a1[0]],
			[a0[1] - 0.02, a0[1], a1[1], a1[1] - 0.02],
			color="black", lw=thickness,
			transform=ax.transAxes, clip_on=False,
		)
		if ann.text:
			ax.text(
				(a0[0] + a1[0]) / 2.0, max(a0[1], a1[1]) + 0.02, ann.text,
				ha="center", va="bottom",
				transform=ax.transAxes,
				fontsize=float(ann.style.get("size", 7.0)),
			)

	def _render_arrow(self, fig, spec, ann, axes_by_panel, style_resolver):
		entry = axes_by_panel.get(ann.panel_id)
		if entry is None or len(ann.coords) < 4:
			return
		ax, _ax2, panel = entry
		x1_mm, y1_mm, x2_mm, y2_mm = ann.coords[:4]
		a0 = self._mm_to_axes_xy(panel, x1_mm, y1_mm)
		a1 = self._mm_to_axes_xy(panel, x2_mm, y2_mm)

		color = str((ann.style or {}).get("color", "black"))
		ax.annotate(
			ann.text, xy=a1, xytext=a0,
			xycoords="axes fraction", textcoords="axes fraction",
			arrowprops=dict(arrowstyle="->", color=color),
			fontsize=float(ann.style.get("size", 8.0)),
			color=color,
		)

	def save(self, fig: Figure, path: str, fmt: str, dpi: int = 300) -> None:
		if fig.canvas is None or not hasattr(fig.canvas, "print_figure"):
			FigureCanvasAgg(fig)
		fig.savefig(
			path, format=fmt, dpi=dpi,
			bbox_inches=None, pad_inches=0.0,
			facecolor=fig.get_facecolor(),
		)