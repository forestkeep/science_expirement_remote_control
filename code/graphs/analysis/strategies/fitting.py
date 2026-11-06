from __future__ import annotations
import logging
from typing import Any,Dict,List,Optional
import numpy as np
from..models import(AnalysisToolDescriptor,OverlayPayload,ParamDescriptor,ParamType,PlacementType,ToolCategory,)
from..registry import AnalysisToolRegistry
from.base import AnalysisContext,AnalysisStrategy,ValidationResult
logger=logging.getLogger(__name__)
_registry=AnalysisToolRegistry.instance()
def _finite_float(value)->Optional[float]:
	try:
		v=float(value)
	except(TypeError,ValueError):
		return None
	if not np.isfinite(v):
		return None
	return v
def humanize_fit_error(exc:BaseException)->str:
	msg=str(exc)
	if "Optimal parameters not found" in msg:
		return "подгонка не сошлась — модель не описывает данные. Проверьте наличие чёткого пика или выберите другую модель"
	if "Residuals are not finite" in msg:
		return "в данных есть NaN или бесконечности — проверьте исходную кривую"
	if "maxfev" in msg.lower():
		return "превышен лимит итераций подгонки"
	return f"внутренняя ошибка подгонки: {msg}"
def _fit_metrics(y:np.ndarray,y_fit:np.ndarray,n_params:int)->Dict[str,Any]:
	y=np.asarray(y,dtype=float)
	y_fit=np.asarray(y_fit,dtype=float)
	if y.size==0 or y.size!=y_fit.size:
		return {}
	resid=y-y_fit
	n=int(resid.size)
	sse=float(np.sum(resid*resid))
	y_mean=float(np.mean(y))
	sst=float(np.sum((y-y_mean)**2))
	dof=int(n-int(n_params))
	metrics:Dict[str,Any]={"n":n,"dof":dof if dof>0 else 0,"n_params":int(n_params),"sse":sse,"sst":sst}
	r2=_finite_float(1.0-sse/sst)if sst>0 else None
	if r2 is not None:
		metrics["r2"]=r2
	if dof>0 and sst>0 and n>1:
		adj_r2=_finite_float(1.0-(sse/dof)/(sst/(n-1)))
		if adj_r2 is not None:
			metrics["adj_r2"]=adj_r2
	rmse=_finite_float(np.sqrt(sse/n))if n>0 else None
	if rmse is not None:
		metrics["rmse"]=rmse
	std_err=_finite_float(np.sqrt(sse/dof))if dof>0 else None
	if std_err is not None:
		metrics["std_err"]=std_err
	chi2_red=_finite_float(sse/dof)if dof>0 else None
	if chi2_red is not None:
		metrics["chi2_red"]=chi2_red
	return metrics
class LinearFitStrategy(AnalysisStrategy):
	def validate(self,params,sources):
		if not sources:
			return ValidationResult(False,"Не выделено кривых")
		for s in sources:
			if len(s.x)<2:
				return ValidationResult(False,"Мало точек")
		return ValidationResult(True)
	def compute(self,context:AnalysisContext,params:Dict[str,Any]):
		results=[]
		for snap in context.sources:
			x=np.asarray(snap.x,dtype=float)
			y=np.asarray(snap.y,dtype=float)
			mask=np.isfinite(x)&np.isfinite(y)
			x,y=x[mask],y[mask]
			if len(x)<2:
				results.append({"curve":snap.root_name,"error":"мало точек (нужно ≥ 2)"})
				continue
			k,b=np.polyfit(x,y,1)
			y_fit=k*x+b
			metrics=_fit_metrics(y,y_fit,2)
			entry={"curve":snap.root_name,"x":x,"y":y_fit,"k":float(k),"b":float(b),"params":{"k":float(k),"b":float(b)},"param_names":["k","b"]}
			entry.update(metrics)
			results.append(entry)
		return OverlayPayload(x=[r["x"] for r in results if"x"in r],y=[r["y"] for r in results if"y"in r],style_hint={"dashed":True,"thickness_factor":0.75},),results
	def describe(self,params):
		return "линейная"
class PolynomialFitStrategy(AnalysisStrategy):
	def validate(self,params,sources):
		if not sources:
			return ValidationResult(False,"Не выделено кривых")
		deg=int(params.get("degree",2))
		for s in sources:
			if len(s.x)<deg+1:
				return ValidationResult(False,f"Нужно ≥ {deg + 1} точек")
		return ValidationResult(True)
	def compute(self,context:AnalysisContext,params:Dict[str,Any]):
		deg=max(2,min(6,int(params.get("degree",2))))
		results=[]
		for snap in context.sources:
			x=np.asarray(snap.x,dtype=float)
			y=np.asarray(snap.y,dtype=float)
			mask=np.isfinite(x)&np.isfinite(y)
			x,y=x[mask],y[mask]
			if len(x)<deg+1:
				results.append({"curve":snap.root_name,"error":f"мало точек (нужно ≥ {deg + 1})"})
				continue
			try:
				coeffs=np.polyfit(x,y,deg)
				y_fit=np.polyval(coeffs,x)
			except Exception as exc:
				logger.warning("polynomial fit failed for %s: %s",snap.root_name,exc)
				results.append({"curve":snap.root_name,"error":humanize_fit_error(exc)})
				continue
			names=[f"c{i}" for i in range(deg,-1,-1)]
			named={name:float(val) for name,val in zip(names,coeffs)}
			metrics=_fit_metrics(y,y_fit,deg+1)
			entry={"curve":snap.root_name,"x":x,"y":y_fit,"coeffs":coeffs.tolist(),"degree":deg,"params":named,"param_names":names}
			entry.update(metrics)
			results.append(entry)
		return OverlayPayload(x=[r["x"] for r in results if"x"in r],y=[r["y"] for r in results if"y"in r],style_hint={"dashed":True,"thickness_factor":0.75},),results
	def describe(self,params):
		return f"полином deg={params.get('degree', 2)}"
def _gaussian(x,amp,mu,sigma,base):
	return base+amp*np.exp(-0.5*((x-mu)/sigma)**2)
def _lorentz(x,amp,mu,gamma,base):
	return base+amp/(1.0+((x-mu)/gamma)**2)
class _PeakFitStrategy(AnalysisStrategy):
	_peak_fn=None
	_param_names=("amp","mu","width","base")
	_width_factor=2.355
	def validate(self,params,sources):
		if not sources:
			return ValidationResult(False,"Не выделено кривых")
		return ValidationResult(True)
	def _init_guess_robust(self,x:np.ndarray,y:np.ndarray)->List[float]:
		baseline=float(np.nanpercentile(y,10))
		y_above=y-baseline
		y_above=np.where(y_above>0,y_above,0.0)
		i_peak=int(np.argmax(y_above))
		amp=float(y_above[i_peak])
		if amp<=0:
			amp=max(float(np.nanmax(y)-np.nanmin(y)),1e-12)
			baseline=float(np.nanmin(y))
			i_peak=int(np.nanargmax(y))
		mu=float(x[i_peak])
		half=amp/2.0
		left=i_peak
		while left>0 and y_above[left]>half:
			left-=1
		right=i_peak
		while right<len(y_above)-1 and y_above[right]>half:
			right+=1
		fwhm=float(x[right]-x[left])if right>left else 0.0
		width=fwhm/self._width_factor if fwhm>0 else float(x[-1]-x[0])/6.0
		if width<=0:
			width=1.0
		return [amp,mu,width,baseline]
	def _init_guess_minmax(self,x:np.ndarray,y:np.ndarray)->List[float]:
		amp=float(np.nanmax(y)-np.nanmin(y))
		mu=float(x[int(np.nanargmax(y))])
		width=float((x[-1]-x[0])/6.0) or 1.0
		base=float(np.nanmin(y))
		return [amp if amp>0 else 1e-12,mu,width,base]
	def _bounds(self,x:np.ndarray,y:np.ndarray,p0:List[float]):
		x_span=float(x[-1]-x[0]) or 1.0
		y_span=float(np.nanmax(y)-np.nanmin(y)) or 1.0
		amp0=float(p0[0])
		lower=[0.0,float(x[0])-0.1*x_span,1e-12,float(np.nanmin(y))-y_span]
		upper=[max(2.0*amp0+y_span,1e-9),float(x[-1])+0.1*x_span,x_span*2.0,float(np.nanmax(y))+y_span]
		return lower,upper
	def _try_fit(self,x:np.ndarray,y:np.ndarray):
		from scipy.optimize import curve_fit
		last_exc:Optional[BaseException]=None
		for p0 in (self._init_guess_robust(x,y),self._init_guess_minmax(x,y)):
			try:
				lower,upper=self._bounds(x,y,p0)
				popt,_=curve_fit(self._peak_fn,x,y,p0=p0,bounds=(lower,upper),maxfev=20000)
				y_fit=self._peak_fn(x,*popt)
				return y_fit,popt
			except Exception as exc:
				last_exc=exc
				logger.debug("fit attempt failed for curve: %s",exc)
				continue
		if last_exc is not None:
			raise last_exc
		raise RuntimeError("fit: no attempts")
	def compute(self,context:AnalysisContext,params:Dict[str,Any]):
		try:
			from scipy.optimize import curve_fit  # noqa: F401
		except ImportError:
			logger.warning("scipy не установлен, фит пиков недоступен")
			return OverlayPayload(),[{"curve":s.root_name,"error":"scipy не установлен"} for s in context.sources]
		results=[]
		for snap in context.sources:
			x=np.asarray(snap.x,dtype=float)
			y=np.asarray(snap.y,dtype=float)
			mask=np.isfinite(x)&np.isfinite(y)
			x,y=x[mask],y[mask]
			if len(x)<4:
				results.append({"curve":snap.root_name,"error":"мало точек (нужно ≥ 4)"})
				continue
			try:
				y_fit,popt=self._try_fit(x,y)
			except Exception as exc:
				logger.warning("fit failed for %s: %s",snap.root_name,exc)
				results.append({"curve":snap.root_name,"error":humanize_fit_error(exc)})
				continue
			named={name:float(val) for name,val in zip(self._param_names,popt)}
			metrics=_fit_metrics(y,y_fit,len(popt))
			entry={"curve":snap.root_name,"x":x,"y":y_fit,"params":named,"param_names":list(self._param_names),"popt":popt.tolist()}
			entry.update(metrics)
			results.append(entry)
		return OverlayPayload(x=[r["x"] for r in results if"x"in r],y=[r["y"] for r in results if"y"in r],style_hint={"dashed":True,"thickness_factor":0.75},),results
	def describe(self,params):
		return "peak"
class GaussianFitStrategy(_PeakFitStrategy):
	_peak_fn=staticmethod(_gaussian)
	_param_names=("amp","mu","sigma","base")
	_width_factor=2.355
	def describe(self,params):
		return "Gaussian"
class LorentzFitStrategy(_PeakFitStrategy):
	_peak_fn=staticmethod(_lorentz)
	_param_names=("amp","mu","gamma","base")
	_width_factor=2.0
	def describe(self,params):
		return "Lorentz"
def _register():
	_registry.register(AnalysisToolDescriptor(tool_id="fit.linear",category=ToolCategory.FITTING,placement_type=PlacementType.OVERLAY,title_key="analysis.tool.fit.linear.title",tooltip_key="analysis.tool.fit.linear.tooltip",param_schema=[],strategy_factory=LinearFitStrategy,))
	_registry.register(AnalysisToolDescriptor(tool_id="fit.polynomial",category=ToolCategory.FITTING,placement_type=PlacementType.OVERLAY,title_key="analysis.tool.fit.polynomial.title",param_schema=[ParamDescriptor("degree",ParamType.INT,default=2,min=2,max=6,title_key="analysis.param.fit.polynomial.degree",tooltip_key="analysis.param.fit.polynomial.degree.tooltip"),],strategy_factory=PolynomialFitStrategy,))
	_registry.register(AnalysisToolDescriptor(tool_id="fit.gaussian",category=ToolCategory.FITTING,placement_type=PlacementType.OVERLAY,title_key="analysis.tool.fit.gaussian.title",param_schema=[],strategy_factory=GaussianFitStrategy,))
	_registry.register(AnalysisToolDescriptor(tool_id="fit.lorentz",category=ToolCategory.FITTING,placement_type=PlacementType.OVERLAY,title_key="analysis.tool.fit.lorentz.title",param_schema=[],strategy_factory=LorentzFitStrategy,))
_register()