"""Matplotlib-рендерер. Единственный в этой итерации.

Ключевые моменты:
  - Точное позиционирование через fig.add_axes(rect) с прямоугольниками
    в долях фигуры, вычисленными из мм (units.panel_rect_to_figure_fraction).
  - bbox_inches=None — фигура сохраняется ровно своих физических размеров.
  - svg.fonttype='none', pdf.fonttype=42 — текст остаётся редактируемым.
  - Никакого timestamp в рендере.
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib import font_manager

from .base import RendererAdapter
from .helpers import qt_style_to_mpl, color_for_series, line_width_pt
from ..core.units import mm_to_inch, panel_rect_to_figure_fraction
from ..core.sentinel import MISSING

logger = logging.getLogger(__name__)

matplotlib.rcParams["pdf.fonttype"] = 42     # редактируемый TrueType
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["svg.fonttype"] = "none"  # текст как текст
matplotlib.rcParams["axes.unicode_minus"] = False


def _resolve_font_family(name: str) -> str:
    """Если шрифт не установлен — тихо откатиться на DejaVu Sans."""
    try:
        font_manager.findfont(name, fallback_to_default=False)
        return name
    except Exception:
        return "DejaVu Sans"


class MatplotlibRenderer(RendererAdapter):
    def create_figure(self, spec) -> Figure:
        fig = Figure(
            figsize=(mm_to_inch(spec.width_mm), mm_to_inch(spec.height_mm)),
            dpi=100,
        )
        FigureCanvasAgg(fig)
        return fig

    def get_native_size_px(self, figure_handle: Figure, dpi: float) -> tuple:
        w_in, h_in = figure_handle.get_size_inches()
        return int(round(w_in * dpi)), int(round(h_in * dpi))

    # ---------------------------------------------------------------- render
    def render(
        self,
        fig: Figure,
        spec,
        data_resolver: Callable[[Any, Any], Optional[dict]],
        style_resolver: Callable[[str], Any],
        overrides_resolver: Callable[[str], Any],
    ) -> Figure:
        fig.clear()
        bg = style_resolver("figure.background")
        if bg is MISSING:
            bg = "#ffffff"
        fig.patch.set_facecolor(bg)

        # Панели
        axes_by_panel = {}
        for panel in spec.sorted_panels():
            if not panel.visible:
                continue
            ax = self._render_panel(fig, spec, panel, data_resolver, style_resolver)
            if ax is not None:
                axes_by_panel[panel.id] = (ax, panel)

        # Data-bound аннотации — ТОЛЬКО из источника, только overrides здесь
        for panel in spec.sorted_panels():
            if not panel.visible:
                continue
            entry = axes_by_panel.get(panel.id)
            if entry is None:
                continue
            ax, _ = entry
            data = data_resolver(panel, panel.data_ref)
            if not data:
                continue
            for ann in data.get("panel_annotations", []) or []:
                ov = overrides_resolver(ann["id"])
                if ov is not None and getattr(ov, "visible_override", None) is False:
                    continue
                self._render_data_bound(ax, ann, ov, style_resolver)

        # Presentation-only аннотации
        for ann in sorted(spec.presentation_annotations, key=lambda a: (int(a.z), a.id)):
            if not ann.visible:
                continue
            self._render_presentation(fig, spec, ann, axes_by_panel, style_resolver)

        return fig

    # -------------------------------------------------------------- panel
    def _render_panel(self, fig, spec, panel, data_resolver, style_resolver):
        x, y, w, h = panel_rect_to_figure_fraction(
            panel.x_mm, panel.y_mm, panel.w_mm, panel.h_mm,
            spec.width_mm, spec.height_mm,
        )
        if w <= 0 or h <= 0:
            return None
        ax = fig.add_axes([x, y, w, h])

        # Стили осей
        axes_lw = style_resolver("figure.axes.line_width")
        if axes_lw is MISSING:
            axes_lw = 0.5
        tick_size = style_resolver("figure.axes.tick_size")
        if tick_size is MISSING:
            tick_size = 7.0
        label_size = style_resolver("figure.axes.label_size")
        if label_size is MISSING:
            label_size = 8.0
        font_family = style_resolver("figure.font.family")
        if font_family is MISSING:
            font_family = "DejaVu Sans"
        font_family = _resolve_font_family(font_family)

        for spine in ax.spines.values():
            spine.set_linewidth(float(axes_lw))
        ax.tick_params(labelsize=float(tick_size), width=float(axes_lw))

        data = data_resolver(panel, panel.data_ref)
        if not data:
            ax.text(0.5, 0.5, "(no data)", ha="center", va="center",
                    transform=ax.transAxes, fontsize=float(label_size),
                    color="#999999")
            if panel.x_label:
                ax.set_xlabel(panel.x_label, fontsize=float(label_size),
                              family=font_family)
            if panel.y_label:
                ax.set_ylabel(panel.y_label, fontsize=float(label_size),
                              family=font_family)
            return ax

        xs = data.get("x")
        ys = data.get("y")
        if xs is not None and ys is not None and len(xs) > 0:
            color = color_for_series(data.get("saved_style"), 0)
            lw = line_width_pt(data.get("saved_style"),
                               style_resolver("figure.line.width")
                               if style_resolver("figure.line.width") is not MISSING else 1.0)
            ls = qt_style_to_mpl(getattr(data.get("saved_style"), "line_style", None))
            ax.plot(xs, ys, color=color, linewidth=float(lw),
                    linestyle=ls, label=data.get("curve_name", ""))

        if panel.x_range:
            ax.set_xlim(*panel.x_range)
        if panel.y_range:
            ax.set_ylim(*panel.y_range)
        if panel.x_log:
            ax.set_xscale("log")
        if panel.y_log:
            ax.set_yscale("log")

        xl = panel.x_label or (data.get("x_name") or "")
        yl = panel.y_label or (data.get("y_name") or "")
        if xl:
            ax.set_xlabel(xl, fontsize=float(label_size), family=font_family)
        if yl:
            ax.set_ylabel(yl, fontsize=float(label_size), family=font_family)

        if panel.title:
            title_size = style_resolver("panel.title_size")
            if title_size is MISSING:
                title_size = 9.0
            ax.set_title(panel.title, fontsize=float(title_size),
                         family=font_family)

        return ax

    # -------------------------------------------------- data-bound annotations
    def _render_data_bound(self, ax, ann, override, style_resolver):
        x = ann.get("x")
        y = ann.get("y")
        if x is None or y is None:
            return
        if override is not None and override.position_override:
            x, y = override.position_override
        label = ann.get("label", "") or ""
        # tool_id → понятный маркер
        kind = (ann.get("annotation_kind") or "").split(".")[-1]
        marker = "+" if kind in ("peaks", "valleys") else "o"
        size = style_resolver("annotation.text_size")
        if size is MISSING:
            size = 8.0
        if override is not None:
            size = override.style_override.get("size", size)
        ax.plot([x], [y], marker=marker, linestyle="None",
                markersize=float(size) * 0.6, color="#d62728")
        if label:
            ax.annotate(label, (x, y), textcoords="offset points",
                        xytext=(4, 4), fontsize=float(size) * 0.8,
                        color="#333333")

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
        # panel_mm: (0,0) — левый верхний угол панели
        ax_x = x_mm / panel.w_mm if panel.w_mm > 0 else 0.0
        ax_y = 1.0 - (y_mm / panel.h_mm if panel.h_mm > 0 else 0.0)
        return ax_x, ax_y

    def _font_kwargs(self, ann, style_resolver, size_key="annotation.text_size"):
        size = style_resolver(size_key)
        if size is MISSING:
            size = 8.0
        family = style_resolver("figure.font.family")
        if family is MISSING:
            family = "DejaVu Sans"
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
            ax, panel = entry
            ax_x, ax_y = self._mm_to_axes_xy(panel, ann.coords[0], ann.coords[1])
            ax.text(ax_x, ax_y, ann.text, ha="left", va="top",
                    transform=ax.transAxes, **kw)
        elif ann.coordinate_space == "axes_data":
            entry = axes_by_panel.get(ann.panel_id)
            if entry is None or len(ann.coords) < 2:
                return
            ax, _ = entry
            ax.text(ann.coords[0], ann.coords[1], ann.text, ha="left", va="top", **kw)

    def _render_panel_label(self, fig, spec, ann, axes_by_panel, style_resolver):
        entry = axes_by_panel.get(ann.panel_id)
        if entry is None:
            return
        ax, panel = entry
        # По умолчанию: чуть выше левого верхнего угла панели
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
        ax, panel = entry
        width_mm = float(ann.style.get("width_mm",
            style_resolver("annotation.scalebar.width_mm")
            if style_resolver("annotation.scalebar.width_mm") is not MISSING else 5.0))
        thickness_pt = float(ann.style.get("thickness_pt",
            style_resolver("annotation.scalebar.thickness_pt")
            if style_resolver("annotation.scalebar.thickness_pt") is not MISSING else 0.6))
        x_mm = float(ann.coords[0]) if len(ann.coords) > 0 else 3.0
        y_mm = float(ann.coords[1]) if len(ann.coords) > 1 else panel.h_mm - 3.0
        x0, y0 = self._mm_to_axes_xy(panel, x_mm, y_mm)
        x1, _ = self._mm_to_axes_xy(panel, x_mm + width_mm, y_mm)
        ax.plot([x0, x1], [y0, y0], color="black", lw=thickness_pt,
                transform=ax.transAxes, clip_on=False, solid_capstyle="butt")
        if ann.text:
            ax.text((x0 + x1) / 2.0, y0 - 0.03, ann.text, ha="center", va="top",
                    transform=ax.transAxes, fontsize=float(ann.style.get("size", 7.0)))

    def _render_bracket(self, fig, spec, ann, axes_by_panel, style_resolver):
        entry = axes_by_panel.get(ann.panel_id)
        if entry is None or len(ann.coords) < 4:
            return
        ax, panel = entry
        x1_mm, y1_mm, x2_mm, y2_mm = ann.coords[:4]
        a0 = self._mm_to_axes_xy(panel, x1_mm, y1_mm)
        a1 = self._mm_to_axes_xy(panel, x2_mm, y2_mm)
        thickness = float(ann.style.get("thickness_pt",
            style_resolver("annotation.bracket.width_pt")
            if style_resolver("annotation.bracket.width_pt") is not MISSING else 0.6))
        ax.plot([a0[0], a0[0], a1[0], a1[0]],
                [a0[1] - 0.02, a0[1], a1[1], a1[1] - 0.02],
                color="black", lw=thickness, transform=ax.transAxes,
                clip_on=False)
        if ann.text:
            ax.text((a0[0] + a1[0]) / 2.0, max(a0[1], a1[1]) + 0.02, ann.text,
                    ha="center", va="bottom", transform=ax.transAxes,
                    fontsize=float(ann.style.get("size", 7.0)))

    def _render_arrow(self, fig, spec, ann, axes_by_panel, style_resolver):
        entry = axes_by_panel.get(ann.panel_id)
        if entry is None or len(ann.coords) < 4:
            return
        ax, panel = entry
        x1_mm, y1_mm, x2_mm, y2_mm = ann.coords[:4]
        a0 = self._mm_to_axes_xy(panel, x1_mm, y1_mm)
        a1 = self._mm_to_axes_xy(panel, x2_mm, y2_mm)
        ax.annotate(ann.text, xy=a1, xytext=a0,
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", color="black"),
                    fontsize=float(ann.style.get("size", 8.0)))

    # -------------------------------------------------------------- save
    def save(self, fig: Figure, path: str, fmt: str, dpi: int = 300) -> None:
        if fig.canvas is None or not hasattr(fig.canvas, "print_figure"):
            FigureCanvasAgg(fig)
        fig.savefig(
            path, format=fmt, dpi=dpi,
            bbox_inches=None, pad_inches=0.0,
            facecolor=fig.get_facecolor(),
        )