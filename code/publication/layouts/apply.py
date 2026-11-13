from __future__ import annotations
import logging
from typing import Optional,Tuple
from..model.figure_model import FigureSpec
from.template import LayoutTemplate
logger=logging.getLogger(__name__)
DEFAULT_CELL_ASPECT=0.75

logger = logging.getLogger(__name__)


def preview_counts(spec:FigureSpec,template:LayoutTemplate)->Tuple[int,int,int]:
	existing=len([p for p in spec.panels if p.kind=="plot"])
	cells=template.n_cells
	will_lose=max(0,existing-cells)
	return existing,cells,will_lose


def apply_template(spec:FigureSpec,template:LayoutTemplate,margin_mm:float,gap_mm:float,mode:str,area_width_mm:Optional[float]=None,max_height_mm:Optional[float]=None,cell_aspect:float=DEFAULT_CELL_ASPECT)->None:
	eff_w=float(spec.width_mm)if area_width_mm is None else min(float(area_width_mm),float(spec.width_mm))
	max_h=float(spec.height_mm)if max_height_mm is None else min(float(max_height_mm),float(spec.height_mm))
	if eff_w<=0 or max_h<=0:
		raise ValueError("Некорректные размеры области раскладки")
	natural_h=template.natural_height_mm(eff_w,gap_mm=gap_mm,margin_mm=margin_mm,cell_aspect=cell_aspect)
	if natural_h<=0:
		raise ValueError(f"Шаблон {template.name} не помещается в область {eff_w:.1f}×{max_h:.1f} мм "f"при margin={margin_mm:.1f} мм, gap={gap_mm:.1f} мм")
	area_h=min(natural_h,max_h)
	cells=template.resolve_mm(eff_w,area_h,margin_mm,gap_mm)
	if not cells:
		raise ValueError("Шаблон не помещается при заданных margin/gap: "f"margin={margin_mm} мм, gap={gap_mm} мм, "f"area={eff_w:.1f}×{area_h:.1f} мм")
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