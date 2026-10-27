import json
import logging
import numpy as np

from .base import BaseHDF5Entity
from ..models import (
    Plot, GraphStyle, Statistics, FilterEntry, LinearData,
    CurveTreeItemData, UncertaintyEntry,
)

logger = logging.getLogger(__name__)

class HDF5Plot(BaseHDF5Entity):
    """Представление графика в HDF5."""
    def write(self, plot: Plot):
        """Записывает график в HDF5."""
        attributes = {
            'name': plot.name,
            'description': plot.description if plot.description else "",
            'status': plot.status,
            'is_draw': bool(plot.is_draw),
            'is_gen': bool(getattr(plot, "is_gen", False)),
            'x_name': plot.x_name or "",
            'y_name': plot.y_name or "",
            'is_curve_selected': bool(plot.is_curve_selected),
            'axis': int(plot.axis or 1),
        }
        self._write_attributes(attributes)

        if 'style' not in self._hdf5_object:
            self._hdf5_object.create_group('style')
        style_group = self._hdf5_object['style']

        style_attrs = {
            'name': plot.style.name or "",
            'description': plot.style.description or "",
            'color': plot.style.color or "#ffffff",
            'line_style': plot.style.line_style or "Solid",
            'line_width': float(plot.style.line_width or 1),
            'symbol': plot.style.symbol if plot.style.symbol is not None else "",
            'symbol_size': float(plot.style.symbol_size or 1),
            'symbol_color': plot.style.symbol_color or "#ffffff",
            'fill_color': plot.style.fill_color or "#ffffff",
        }
        for key, value in style_attrs.items():
            style_group.attrs[key] = value

        if 'statistics' not in self._hdf5_object:
            self._hdf5_object.create_group('statistics')
        stats_group = self._hdf5_object['statistics']

        stats_attrs = {
            'name': plot.statistics.name or "",
            'description': plot.statistics.description or "",
            'mean': float(plot.statistics.mean or 0.0),
            'median': float(plot.statistics.median or 0.0),
            'mode': float(plot.statistics.mode or 0.0),
            'std_dev': float(plot.statistics.std_dev or 0.0),
            'count': int(plot.statistics.count or 0),
            'min_x': float(plot.statistics.min_x or 0.0),
            'max_x': float(plot.statistics.max_x or 0.0),
            'min_y': float(plot.statistics.min_y or 0.0),
            'max_y': float(plot.statistics.max_y or 0.0),
        }
        for key, value in stats_attrs.items():
            stats_group.attrs[key] = value

        if 'history' in self._hdf5_object:
            del self._hdf5_object['history']
        if plot.history:
            history_group = self._hdf5_object.create_group('history')
            for i, entry in enumerate(plot.history):
                entry_group = history_group.create_group(f'entry_{i}')
                entry_group.attrs['name'] = entry.name if entry.name else "filter"
                entry_group.attrs['description'] = entry.description if entry.description else ""
                entry_group.attrs['filter_type'] = entry.filter_type
                entry_group.attrs['enabled'] = bool(getattr(entry, "enabled", True))

                try:
                    entry_group.attrs['params'] = json.dumps(
                        entry.params or {}, ensure_ascii=False, default=str
                    )
                except Exception:
                    logger.exception("write filter params failed")
                    entry_group.attrs['params'] = '{}'

        # --- Погрешности ---
        if 'uncertainty' in self._hdf5_object:
            del self._hdf5_object['uncertainty']
        unc_group = self._hdf5_object.create_group('uncertainty')
        try:
            unc_group.attrs['default_style'] = json.dumps(
                plot.uncertainty_style or {}, ensure_ascii=False)
        except Exception:
            unc_group.attrs['default_style'] = '{}'

        for i, entry in enumerate(getattr(plot, 'uncertainty_records', []) or []):
            eg = unc_group.create_group(f"u{i}")
            eg.attrs['id'] = entry.id or ""
            eg.attrs['method'] = entry.method or "std"
            eg.attrs['active'] = bool(entry.active)
            try:
                eg.attrs['params'] = json.dumps(entry.params or {}, ensure_ascii=False)
            except Exception:
                eg.attrs['params'] = '{}'
            try:
                eg.attrs['style'] = json.dumps(entry.style or {}, ensure_ascii=False)
            except Exception:
                eg.attrs['style'] = '{}'
            if entry.y_err is not None:
                try:
                    eg.create_dataset('y_err', data=np.asarray(entry.y_err),
                                      dtype=float, compression='gzip')
                except Exception:
                    logger.exception("write uncertainty y_err failed")
            if entry.x_err is not None:
                try:
                    eg.create_dataset('x_err', data=np.asarray(entry.x_err),
                                      dtype=float, compression='gzip')
                except Exception:
                    logger.exception("write uncertainty x_err failed")

        if 'linear_data' in self._hdf5_object:
            del self._hdf5_object['linear_data']
        linear_data_group = self._hdf5_object.create_group('linear_data')

        linear_attrs = {
            'device': plot.linear_data.device if plot.linear_data.device else "",
            'channel': plot.linear_data.channel if plot.linear_data.channel else "",
            'curve_name': plot.linear_data.curve_name if plot.linear_data.curve_name else "",
            'is_name_customized': bool(plot.linear_data.is_name_customized),
            'number': plot.linear_data.number if plot.linear_data.number is not None else -1,
            'number_axis': plot.linear_data.number_axis if plot.linear_data.number_axis is not None else -1,
            'is_draw': 1 if plot.linear_data.is_draw else 0,
            'is_curve_selected': 1 if plot.linear_data.is_curve_selected else 0,
            'name': plot.linear_data.name or "",
            'description': plot.linear_data.description or "",
            'tip': plot.linear_data.tip or "linear",
        }
        for key, value in linear_attrs.items():
            linear_data_group.attrs[key] = value

        linear_data_group.create_dataset('raw_data_x', data=plot.linear_data.raw_data_x, dtype=float, compression='gzip')
        linear_data_group.create_dataset('raw_data_y', data=plot.linear_data.raw_data_y, dtype=float, compression='gzip')
        linear_data_group.create_dataset('filtered_x_data', data=plot.linear_data.filtered_x_data, dtype=float, compression='gzip')
        linear_data_group.create_dataset('filtered_y_data', data=plot.linear_data.filtered_y_data, dtype=float, compression='gzip')

        tree_item_group = linear_data_group.create_group('tree_item_data')

        tree_item_attrs = {
            'name': plot.linear_data.tree_item_data.name or "",
            'description': plot.linear_data.tree_item_data.description or "",
            'font_info': plot.linear_data.tree_item_data.font_info or "Italic,10",
            'color_info': plot.linear_data.tree_item_data.color_info or "#ff30ea",
            'col_font_info': plot.linear_data.tree_item_data.col_font_info or "15",
        }
        for key, value in tree_item_attrs.items():
            tree_item_group.attrs[key] = value

        try:
            tree_item_group.attrs['parameters'] = json.dumps(
                plot.linear_data.tree_item_data.parameters or {},
                ensure_ascii=False, default=str,
            )
        except Exception:
            tree_item_group.attrs['parameters'] = '{}'


    def read(self) -> Plot:
        """Читает график из HDF5 и возвращает объект Plot."""
        name = self._hdf5_object.attrs.get('name', '')
        description = self._hdf5_object.attrs.get('description', '')
        status = self._hdf5_object.attrs.get('status', 'active')
        is_draw = bool(self._hdf5_object.attrs.get('is_draw', False))
        is_gen = bool(self._hdf5_object.attrs.get('is_gen', False))
        is_curve_selected = bool(self._hdf5_object.attrs.get('is_curve_selected', False))
        x_name = self._hdf5_object.attrs.get('x_name', 'X_default')
        y_name = self._hdf5_object.attrs.get('y_name', 'Y_default')
        axis = int(self._hdf5_object.attrs.get('axis', 1))

        style = GraphStyle()
        if 'style' in self._hdf5_object:
            style_group = self._hdf5_object['style']
            style.name = style_group.attrs.get('name', '')
            style.description = style_group.attrs.get('description', '')
            style.color = style_group.attrs.get('color', '#FF0000')
            style.line_width = float(style_group.attrs.get('line_width', 1.0))
            style.line_style = style_group.attrs.get('line_style', 'Solid')
            sym = style_group.attrs.get('symbol', '')
            if isinstance(sym, bytes):
                sym = sym.decode('utf-8', errors='replace')
            style.symbol = sym if sym and sym != "None" else None
            style.symbol_size = float(style_group.attrs.get('symbol_size', 1.0))
            style.symbol_color = style_group.attrs.get('symbol_color', '#FF0000')
            style.fill_color = style_group.attrs.get('fill_color', '#FF0000')

        statistics = Statistics()
        if 'statistics' in self._hdf5_object:
            stats_group = self._hdf5_object['statistics']
            statistics.name = stats_group.attrs.get('name', '')
            statistics.description = stats_group.attrs.get('description', '')
            statistics.mean = float(stats_group.attrs.get('mean', 0.0))
            statistics.median = float(stats_group.attrs.get('median', 0.0))
            statistics.mode = float(stats_group.attrs.get('mode', 0.0))
            statistics.std_dev = float(stats_group.attrs.get('std_dev', 0.0))
            statistics.count = int(stats_group.attrs.get('count', 0))
            statistics.min_x = float(stats_group.attrs.get('min_x', 0.0))
            statistics.max_x = float(stats_group.attrs.get('max_x', 0.0))
            statistics.min_y = float(stats_group.attrs.get('min_y', 0.0))
            statistics.max_y = float(stats_group.attrs.get('max_y', 0.0))

        history = []
        if 'history' in self._hdf5_object:
            history_group = self._hdf5_object['history']
            for entry_name in history_group:
                entry_group = history_group[entry_name]
                entry = FilterEntry()
                entry.name = entry_group.attrs.get('name', '')
                entry.description = entry_group.attrs.get('description', '')
                entry.filter_type = entry_group.attrs.get('filter_type', '')
                entry.enabled = bool(entry_group.attrs.get('enabled', True))

                raw = entry_group.attrs.get('params', '{}')
                if isinstance(raw, bytes):
                    raw = raw.decode('utf-8', errors='replace')
                try:
                    entry.params = json.loads(raw) if raw else {}
                except Exception:
                    logger.exception(
                        "read filter params failed: %r", raw
                    )
                    entry.params = {}

                if not entry.params and 'params' in entry_group:
                    legacy = entry_group['params']
                    for param_name in legacy.attrs:
                        value_str = legacy.attrs[param_name]
                        if isinstance(value_str, bytes):
                            value_str = value_str.decode('utf-8', errors='replace')
                        if value_str.lower() == 'true':
                            entry.params[param_name] = True
                        elif value_str.lower() == 'false':
                            entry.params[param_name] = False
                        else:
                            try:
                                entry.params[param_name] = int(value_str)
                            except ValueError:
                                try:
                                    entry.params[param_name] = float(value_str)
                                except ValueError:
                                    entry.params[param_name] = value_str
                history.append(entry)

        linear_data = LinearData()
        if 'linear_data' in self._hdf5_object:
            linear_data_group = self._hdf5_object['linear_data']
            linear_data.device = linear_data_group.attrs.get('device', '')
            linear_data.channel = linear_data_group.attrs.get('channel', '')
            linear_data.curve_name = linear_data_group.attrs.get('curve_name', '')
            linear_data.is_name_customized = bool(linear_data_group.attrs.get('is_name_customized', False))
            number = linear_data_group.attrs.get('number', -1)
            linear_data.number = int(number) if number != -1 else None
            number_axis = linear_data_group.attrs.get('number_axis', -1)
            linear_data.number_axis = int(number_axis) if number_axis != -1 else None
            linear_data.is_draw = bool(linear_data_group.attrs.get('is_draw', False))
            linear_data.is_curve_selected = bool(linear_data_group.attrs.get('is_curve_selected', False))
            linear_data.name = linear_data_group.attrs.get('name', '')
            linear_data.description = linear_data_group.attrs.get('description', '')
            linear_data.tip = linear_data_group.attrs.get('tip', 'linear')

            if 'raw_data_x' in linear_data_group:
                linear_data.raw_data_x = linear_data_group['raw_data_x'][:]
            if 'raw_data_y' in linear_data_group:
                linear_data.raw_data_y = linear_data_group['raw_data_y'][:]
            if 'filtered_x_data' in linear_data_group:
                linear_data.filtered_x_data = linear_data_group['filtered_x_data'][:]
            if 'filtered_y_data' in linear_data_group:
                linear_data.filtered_y_data = linear_data_group['filtered_y_data'][:]

            if 'tree_item_data' in linear_data_group:
                tree_item_group = linear_data_group['tree_item_data']
                tree_item_data = CurveTreeItemData()
                tree_item_data.name = tree_item_group.attrs.get('name', '')
                _desc = tree_item_group.attrs.get('description', '')
                if isinstance(_desc, bytes):
                    _desc = _desc.decode('utf-8', errors='replace')
                tree_item_data.description = _desc or ''
                tree_item_data.font_info = tree_item_group.attrs.get('font_info', 'Italic,10')
                tree_item_data.color_info = tree_item_group.attrs.get('color_info', '#ff30ea')
                tree_item_data.col_font_info = tree_item_group.attrs.get('col_font_info', '15')

                raw_params = tree_item_group.attrs.get('parameters', '{}')
                if isinstance(raw_params, bytes):
                    raw_params = raw_params.decode('utf-8', errors='replace')
                try:
                    tree_item_data.parameters = json.loads(raw_params) if raw_params else {}
                except Exception:
                    logger.exception("read tree item params failed: %r", raw_params)
                    tree_item_data.parameters = {}

                # Backward-compat: старый формат — подгруппа 'parameters'.
                if not tree_item_data.parameters and 'parameters' in tree_item_group:
                    legacy = tree_item_group['parameters']
                    tree_item_data.parameters = {}
                    for attr_name in legacy.attrs:
                        tree_item_data.parameters[attr_name] = legacy.attrs[attr_name]

                linear_data.tree_item_data = tree_item_data

        uncertainty_records = []
        uncertainty_style = {}
        if 'uncertainty' in self._hdf5_object:
            ug = self._hdf5_object['uncertainty']
            try:
                raw_style = ug.attrs.get('default_style', '{}')
                if isinstance(raw_style, bytes):
                    raw_style = raw_style.decode('utf-8', errors='replace')
                uncertainty_style = json.loads(raw_style) if raw_style else {}
            except Exception:
                uncertainty_style = {}
            for name in ug:
                eg = ug[name]
                entry = UncertaintyEntry()
                _id = eg.attrs.get('id', name)
                if isinstance(_id, bytes):
                    _id = _id.decode('utf-8', errors='replace')
                entry.id = _id or name
                _m = eg.attrs.get('method', 'std')
                if isinstance(_m, bytes):
                    _m = _m.decode('utf-8', errors='replace')
                entry.method = _m or "std"
                entry.active = bool(eg.attrs.get('active', True))
                try:
                    p_raw = eg.attrs.get('params', '{}')
                    if isinstance(p_raw, bytes):
                        p_raw = p_raw.decode('utf-8', errors='replace')
                    entry.params = json.loads(p_raw) if p_raw else {}
                except Exception:
                    entry.params = {}
                try:
                    s_raw = eg.attrs.get('style', '{}')
                    if isinstance(s_raw, bytes):
                        s_raw = s_raw.decode('utf-8', errors='replace')
                    entry.style = json.loads(s_raw) if s_raw else {}
                except Exception:
                    entry.style = {}
                if 'y_err' in eg:
                    entry.y_err = eg['y_err'][:]
                if 'x_err' in eg:
                    entry.x_err = eg['x_err'][:]
                uncertainty_records.append(entry)

        return Plot(
            name=name,
            description=description,
            status=status,
            style=style,
            statistics=statistics,
            history=history,
            linear_data=linear_data,
            x_name=x_name,
            y_name=y_name,
            is_draw=is_draw,
            is_gen=is_gen,
            is_curve_selected=is_curve_selected,
            axis=axis,
            uncertainty_records=uncertainty_records,
            uncertainty_style=uncertainty_style,
        )