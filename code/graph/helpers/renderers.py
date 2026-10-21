import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets


_QT_STYLE = {
    "solid":   QtCore.Qt.SolidLine,
    "dash":    QtCore.Qt.DashLine,
    "dot":     QtCore.Qt.DotLine,
    "dashdot": QtCore.Qt.DashDotLine,
}


def _style(name):
    return _QT_STYLE.get(name, QtCore.Qt.SolidLine)


def _center(manager):
    """Центр и размах текущего видимого диапазона в координатах данных."""
    try:
        rx, ry = manager.graph_view.plotItem.vb.viewRange()
        cx = (rx[0] + rx[1]) / 2.0
        cy = (ry[0] + ry[1]) / 2.0
        sx = (rx[1] - rx[0]) or 1.0
        sy = (ry[1] - ry[0]) or 1.0
        return cx, cy, sx, sy
    except Exception:
        return 0.0, 0.0, 1.0, 1.0


def _add_item(manager, item):
    manager.graph_view.addItem(item)
    return item


def _remove_item(manager, item):
    try:
        manager.graph_view.removeItem(item)
    except Exception:
        pass


def create_helper(manager, helper):
    fn = _CREATORS.get(helper.helper_type)
    if fn is None:
        return []
    return fn(manager, helper) or []


def remove_helper(manager, helper):
    for item in list(helper.items):
        _remove_item(manager, item)
    helper.items = []


# ---------------------------------------------------------------------------
# Курсоры — две параллельные линии, ΔX / ΔY / расстояние
# ---------------------------------------------------------------------------
def _create_cursors(manager, helper):
    p = helper.params
    cx, cy, sx, sy = _center(manager)
    orient = p.get("orientation", "vertical")
    color = p.get("color", "#ffcc00")
    width = int(p.get("width", 1))
    style = p.get("style", "dash")
    fmt = p.get("format", ".4g")
    show_dx = bool(p.get("show_dx", True))
    show_dy = bool(p.get("show_dy", False))
    show_dist = bool(p.get("show_dist", False))

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    label_opts = {"color": color, "position": 0.92}

    if orient == "vertical":
        v1 = p.get("x1", cx - sx * 0.1)
        v2 = p.get("x2", cx + sx * 0.1)
        line1 = pg.InfiniteLine(pos=v1, angle=90, movable=True, pen=pen,
                                label=f"{v1:{fmt}}", labelOpts=dict(label_opts))
        line2 = pg.InfiniteLine(pos=v2, angle=90, movable=True, pen=pen,
                                label=f"{v2:{fmt}}", labelOpts=dict(label_opts))
    else:
        v1 = p.get("y1", cy - sy * 0.1)
        v2 = p.get("y2", cy + sy * 0.1)
        line1 = pg.InfiniteLine(pos=v1, angle=0, movable=True, pen=pen,
                                label=f"{v1:{fmt}}", labelOpts=dict(label_opts))
        line2 = pg.InfiniteLine(pos=v2, angle=0, movable=True, pen=pen,
                                label=f"{v2:{fmt}}", labelOpts=dict(label_opts))

    text = pg.TextItem("", color=color, anchor=(0, 0))
    items = [line1, line2, text]
    for it in items:
        _add_item(manager, it)

    def update():
        a = line1.value()
        b = line2.value()
        y1 = float(p.get("y1", cy))
        y2 = float(p.get("y2", cy))
        x1 = float(p.get("x1", cx))
        x2 = float(p.get("x2", cx))
        parts = []
        if orient == "vertical":
            if show_dx:
                parts.append(f"ΔX = {b - a:{fmt}}")
            if show_dy:
                parts.append(f"ΔY = {y2 - y1:{fmt}}")
            if show_dist:
                parts.append(f"d = {np.hypot(b - a, y2 - y1):{fmt}}")
            text.setPos(min(a, b), max(y1, y2))
        else:
            if show_dy:
                parts.append(f"ΔY = {b - a:{fmt}}")
            if show_dx:
                parts.append(f"ΔX = {x2 - x1:{fmt}}")
            if show_dist:
                parts.append(f"d = {np.hypot(x2 - x1, b - a):{fmt}}")
            text.setPos(max(x1, x2), min(a, b))
        text.setText("\n".join(parts))
        if orient == "vertical":
            helper.params.update({"x1": a, "x2": b})
        else:
            helper.params.update({"y1": a, "y2": b})

    line1.sigPositionChanged.connect(update)
    line2.sigPositionChanged.connect(update)
    update()
    return items


# ---------------------------------------------------------------------------
# Линейка — 2 drag-handle (TargetItem) + соединяющая линия + подпись
# ---------------------------------------------------------------------------
def _create_ruler(manager, helper):
    p = helper.params
    cx, cy, sx, sy = _center(manager)
    x1 = p.get("x1", cx - sx * 0.15)
    y1 = p.get("y1", cy - sy * 0.15)
    x2 = p.get("x2", cx + sx * 0.15)
    y2 = p.get("y2", cy + sy * 0.15)
    color = p.get("color", "#00ff88")
    width = int(p.get("width", 2))
    style = p.get("style", "solid")
    fmt = p.get("format", ".4g")
    show_dist = bool(p.get("show_dist", True))
    show_dx = bool(p.get("show_dx", False))
    show_dy = bool(p.get("show_dy", False))

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    line = pg.PlotDataItem([x1, x2], [y1, y2], pen=pen)
    text = pg.TextItem("", color=color, anchor=(0.5, -0.2))
    text.setPos((x1 + x2) / 2, (y1 + y2) / 2)
    p1 = pg.TargetItem(pos=(x1, y1), size=8, symbol="o", pen=color, brush=color)
    p2 = pg.TargetItem(pos=(x2, y2), size=8, symbol="o", pen=color, brush=color)

    items = [line, text, p1, p2]
    for it in items:
        _add_item(manager, it)

    def update():
        a = p1.pos()
        b = p2.pos()
        line.setData([a.x(), b.x()], [a.y(), b.y()])
        text.setPos((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
        parts = []
        if show_dist:
            parts.append(f"d = {np.hypot(b.x() - a.x(), b.y() - a.y()):{fmt}}")
        if show_dx:
            parts.append(f"ΔX = {b.x() - a.x():{fmt}}")
        if show_dy:
            parts.append(f"ΔY = {b.y() - a.y():{fmt}}")
        text.setText("\n".join(parts))
        helper.params.update({
            "x1": a.x(), "y1": a.y(), "x2": b.x(), "y2": b.y(),
        })

    p1.sigPositionChanged.connect(update)
    p2.sigPositionChanged.connect(update)
    update()
    return items


# ---------------------------------------------------------------------------
# Текст — TargetItem с подписью (drag работает из коробки)
# ---------------------------------------------------------------------------
def _create_text(manager, helper):
    p = helper.params
    cx, cy, _, _ = _center(manager)
    text = p.get("text", "Текст")
    x = p.get("x", cx)
    y = p.get("y", cy)
    color = p.get("color", "#ffffff")
    font_size = int(p.get("font_size", 12))

    anchor = pg.TargetItem(
        pos=(x, y), size=6, symbol="s",
        pen=(200, 200, 200, 80),
        brush=(200, 200, 200, 80),
        label=text,
    )
    try:
        lbl = anchor.label()
        if lbl is not None:
            font = QtGui.QFont()
            font.setPointSize(font_size)
            lbl.setFont(font)
            lbl.setAttr("color", color)
    except Exception:
        pass

    _add_item(manager, anchor)

    def update():
        pos = anchor.pos()
        helper.params.update({"x": pos.x(), "y": pos.y()})

    try:
        anchor.sigPositionChanged.connect(update)
    except Exception:
        pass

    helper.params.update({
        "text": text, "x": x, "y": y,
        "color": color, "font_size": font_size,
    })
    return [anchor]


# ---------------------------------------------------------------------------
# Стрелка-выноска — 2 drag-handle + линия + наконечник + подпись
# ---------------------------------------------------------------------------
def _create_arrow(manager, helper):
    p = helper.params
    cx, cy, sx, sy = _center(manager)
    x1 = p.get("x1", cx - sx * 0.15)
    y1 = p.get("y1", cy - sy * 0.15)
    x2 = p.get("x2", cx + sx * 0.15)
    y2 = p.get("y2", cy + sy * 0.15)
    text = p.get("text", "")
    color = p.get("color", "#ff00ff")
    width = int(p.get("width", 2))
    style = p.get("style", "solid")

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    line = pg.PlotDataItem([x1, x2], [y1, y2], pen=pen)
    arrow = pg.ArrowItem(pos=(x2, y2), tipAngle=30, baseAngle=20,
                         headLen=12, pen=color, brush=color)
    text_item = pg.TextItem(text, color=color, anchor=(0, 0))
    text_item.setPos(x1, y1)
    p1 = pg.TargetItem(pos=(x1, y1), size=8, symbol="o", pen=color, brush=color)
    p2 = pg.TargetItem(pos=(x2, y2), size=8, symbol="o", pen=color, brush=color)

    items = [line, arrow, text_item, p1, p2]
    for it in items:
        _add_item(manager, it)

    def update():
        a = p1.pos()
        b = p2.pos()
        line.setData([a.x(), b.x()], [a.y(), b.y()])
        angle = float(np.degrees(np.arctan2(b.y() - a.y(), b.x() - a.x())))
        try:
            arrow.setStyle(angle=angle)
        except Exception:
            pass
        arrow.setPos(b.x(), b.y())
        text_item.setPos(a.x(), a.y())
        helper.params.update({
            "x1": a.x(), "y1": a.y(), "x2": b.x(), "y2": b.y(),
        })

    p1.sigPositionChanged.connect(update)
    p2.sigPositionChanged.connect(update)
    update()
    return items


# ---------------------------------------------------------------------------
# Пин — TargetItem с настраиваемым символом и размером
# ---------------------------------------------------------------------------
def _create_pin(manager, helper):
    p = helper.params
    cx, cy, _, _ = _center(manager)
    x = p.get("x", cx)
    y = p.get("y", cy)
    text = p.get("text", "")
    color = p.get("color", "#ff3366")
    size = int(p.get("size", 12))
    symbol = p.get("symbol", "o")

    item = pg.TargetItem(pos=(x, y), size=size, symbol=symbol,
                         pen=color, brush=color, label=text)
    _add_item(manager, item)

    def update():
        pos = item.pos()
        helper.params.update({"x": pos.x(), "y": pos.y()})

    try:
        item.sigPositionChanged.connect(update)
    except Exception:
        pass

    helper.params.update({
        "x": x, "y": y, "text": text,
        "color": color, "size": size, "symbol": symbol,
    })
    return [item]


# ---------------------------------------------------------------------------
# Вертикальная / горизонтальная бесконечные линии
# ---------------------------------------------------------------------------
def _create_vline(manager, helper):
    p = helper.params
    cx, cy, _, _ = _center(manager)
    x = p.get("x", cx)
    color = p.get("color", "#88ccff")
    width = int(p.get("width", 1))
    style = p.get("style", "dash")
    show_label = bool(p.get("show_label", True))
    fmt = p.get("format", ".4g")

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    label = f"{{value:{fmt}}}" if show_label else None
    line = pg.InfiniteLine(pos=x, angle=90, movable=True, pen=pen,
                            label=label, labelOpts={"color": color})

    _add_item(manager, line)

    def update():
        helper.params.update({"x": line.value()})
    line.sigPositionChanged.connect(update)
    return [line]


def _create_hline(manager, helper):
    p = helper.params
    cx, cy, _, _ = _center(manager)
    y = p.get("y", cy)
    color = p.get("color", "#88ccff")
    width = int(p.get("width", 1))
    style = p.get("style", "dash")
    show_label = bool(p.get("show_label", True))
    fmt = p.get("format", ".4g")

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    label = f"{{value:{fmt}}}" if show_label else None
    line = pg.InfiniteLine(pos=y, angle=0, movable=True, pen=pen,
                            label=label, labelOpts={"color": color})

    _add_item(manager, line)

    def update():
        helper.params.update({"y": line.value()})
    line.sigPositionChanged.connect(update)
    return [line]


# ---------------------------------------------------------------------------
# Порог — горизонтальная линия + подпись
# ---------------------------------------------------------------------------
def _create_threshold(manager, helper):
    p = helper.params
    cx, cy, _, _ = _center(manager)
    y = p.get("y", cy)
    color = p.get("color", "#ff0000")
    width = int(p.get("width", 2))
    style = p.get("style", "dash")
    prefix = p.get("prefix", "Порог")
    fmt = p.get("format", ".4g")

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    line = pg.InfiniteLine(pos=y, angle=0, movable=True, pen=pen)
    _add_item(manager, line)

    label = pg.TextItem("", color=color, anchor=(0, 1))
    _add_item(manager, label)

    def update():
        v = line.value()
        label.setText(f"{prefix} = {v:{fmt}}")
        try:
            rx, _ = manager.graph_view.plotItem.vb.viewRange()
            label.setPos(rx[0], v)
        except Exception:
            pass
        helper.params.update({"y": v})

    line.sigPositionChanged.connect(update)
    update()
    return [line, label]


# ---------------------------------------------------------------------------
# Полоса — LinearRegionItem, ориентация настраивается
# ---------------------------------------------------------------------------
def _create_band(manager, helper):
    p = helper.params
    cx, cy, sx, sy = _center(manager)
    orient = p.get("orientation", "vertical")
    color = p.get("color", "#00ffff")
    alpha = float(p.get("alpha", 0.25))
    show_label = bool(p.get("show_label", True))
    fmt = p.get("format", ".4g")

    if orient == "vertical":
        v1 = p.get("x1", cx - sx * 0.1)
        v2 = p.get("x2", cx + sx * 0.1)
    else:
        v1 = p.get("x1", cy - sy * 0.1)
        v2 = p.get("x2", cy + sy * 0.1)

    c = pg.mkColor(color)
    c.setAlpha(int(alpha * 255))
    brush = pg.mkBrush(c)

    region = pg.LinearRegionItem(values=(v1, v2), brush=brush, movable=True,
                                 orientation="vertical" if orient == "vertical" else "horizontal")
    _add_item(manager, region)

    text = pg.TextItem("", color=color, anchor=(0, 1))
    _add_item(manager, text)

    def update():
        a, b = region.getRegion()
        if show_label:
            text.setText(f"Δ = {b - a:{fmt}}")
        else:
            text.setText("")
        try:
            rx, ry = manager.graph_view.plotItem.vb.viewRange()
            if orient == "vertical":
                text.setPos(a, ry[1])
            else:
                text.setPos(rx[0], a)
        except Exception:
            pass
        helper.params.update({"x1": a, "x2": b})

    region.sigRegionChanged.connect(update)
    update()
    return [region, text]


_CREATORS = {
    "cursors":   _create_cursors,
    "ruler":     _create_ruler,
    "text":      _create_text,
    "arrow":     _create_arrow,
    "pin":       _create_pin,
    "vline":     _create_vline,
    "hline":     _create_hline,
    "threshold": _create_threshold,
    "band":      _create_band,
}