"""Применение шаблона раскладки к FigureSpec."""
from __future__ import annotations
import logging
from typing import Tuple

from ..model.figure_model import FigureSpec
from .template import LayoutTemplate

logger = logging.getLogger(__name__)


def preview_counts(spec:FigureSpec,template:LayoutTemplate)->Tuple[int,int,int]:
	existing=len([p for p in spec.panels if p.kind=="plot"])
	cells=template.n_cells
	will_lose=max(0,existing-cells)
	return existing,cells,will_lose


def apply_template(spec:FigureSpec,template:LayoutTemplate,margin_mm:float,gap_mm:float,mode:str)->None:
	cells=template.resolve_mm(spec.width_mm,spec.height_mm,margin_mm,gap_mm)
	if not cells:
		raise ValueError("Шаблон не помещается при заданных margin/gap: "f"margin={margin_mm} мм, gap={gap_mm} мм, "f"figure={spec.width_mm:.1f}×{spec.height_mm:.1f} мм")
	if mode=="reflow":
		existing=[p for p in spec.sorted_panels()if p.kind=="plot"]
		if len(existing)>len(cells):
			raise ValueError(f"В фигуре {len(existing)} панелей, а шаблон {template.name} "f"вмещает только {len(cells)}. Выберите шаблон с большим "f"числом ячеек или режим «Заменить».")
		for idx,(panel,(x,y,w,h)) in enumerate(zip(existing,cells)):
			panel.x_mm,panel.y_mm,panel.w_mm,panel.h_mm=x,y,w,h
			panel.z=idx+1
		return
	if mode=="replace":
		spec.panels=[]
		for (x,y,w,h) in cells:
			spec.add_panel(x_mm=x,y_mm=y,w_mm=w,h_mm=h)
		return
	raise ValueError(f"unknown mode: {mode!r}")