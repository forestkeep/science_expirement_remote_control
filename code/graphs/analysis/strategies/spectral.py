# graph/analysis/strategies/spectral.py
from __future__ import annotations

import re
import numpy as np

from ..models import (
    AnalysisToolDescriptor, DomainPayload, ParamDescriptor, ParamType,
    PlacementType, ToolCategory,
)
from ..registry import AnalysisToolRegistry
from .base import AnalysisContext, AnalysisStrategy, ValidationResult

_registry = AnalysisToolRegistry.instance()


class FFTStrategy(AnalysisStrategy):
	def compute(self,context:AnalysisContext,params:dict):
		xs,ys,details=[],[],[]
		x_label="Частота, 1/ед. X"
		for snap in context.sources:
			x=np.asarray(snap.x,dtype=float)
			y=np.asarray(snap.y,dtype=float)
			mask=np.isfinite(x)&np.isfinite(y)
			x,y=x[mask],y[mask]
			if len(x)<4:
				details.append({"curve":snap.root_name,"error":"мало точек (нужно ≥ 4)"})
				continue
			dx=float(np.mean(np.diff(x))) or 1.0
			y_detrended=y-np.mean(y)
			spectrum=np.fft.rfft(y_detrended)
			freqs=np.fft.rfftfreq(len(y_detrended),d=dx)
			amplitude=np.abs(spectrum)
			xs.append(freqs)
			ys.append(amplitude)
			x_label=self._make_freq_label(getattr(snap,"x_name",""))
			details.append({"curve":snap.root_name,"x_label":x_label,"y_label":"|A|","tab_title":f"Спектр: {snap.curve_name or snap.root_name}"})
		return DomainPayload(x=xs,y=ys,x_label=x_label,y_label="|A|",tab_title="Спектр",),details
	def describe(self,params):
		return "FFT"
class AutocorrelationStrategy(AnalysisStrategy):
	def compute(self,context:AnalysisContext,params:dict):
		xs,ys,details=[],[],[]
		x_label="Лаг"
		for snap in context.sources:
			x=np.asarray(snap.x,dtype=float)
			y=np.asarray(snap.y,dtype=float)
			mask=np.isfinite(x)&np.isfinite(y)
			x,y=x[mask],y[mask]
			if len(x)<3:
				details.append({"curve":snap.root_name,"error":"мало точек (нужно ≥ 3)"})
				continue
			y_c=y-np.mean(y)
			n=len(y_c)
			pad=2**int(np.ceil(np.log2(2*n-1)))
			fft=np.fft.fft(y_c,pad)
			ac=np.fft.ifft(fft*np.conj(fft))[:n].real
			norm=np.dot(y_c,y_c) or 1.0
			ac=ac/norm
			lags=np.arange(n)*(x[1]-x[0])if len(x)>1 else np.arange(n)
			xs.append(lags)
			ys.append(ac)
			x_label=f"Лаг, {snap.x_name}"if getattr(snap,"x_name","")else"Лаг"
			details.append({"curve":snap.root_name,"x_label":x_label,"y_label":"ACF","tab_title":f"Автокорреляция: {snap.curve_name or snap.root_name}"})
		return DomainPayload(x=xs,y=ys,x_label=x_label,y_label="ACF",tab_title="Автокорреляция",),details
	def describe(self,params):
		return "autocorr"

def _register():
    _registry.register(AnalysisToolDescriptor(
        tool_id="spectral.fft",
        category=ToolCategory.SPECTRAL,
        placement_type=PlacementType.DOMAIN,
        title_key="analysis.tool.spectral.fft.title",
        param_schema=[],
        strategy_factory=FFTStrategy,
    ))
    _registry.register(AnalysisToolDescriptor(
        tool_id="spectral.autocorr",
        category=ToolCategory.SPECTRAL,
        placement_type=PlacementType.DOMAIN,
        title_key="analysis.tool.spectral.autocorr.title",
        param_schema=[],
        strategy_factory=AutocorrelationStrategy,
    ))


_register()