import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets
import logging
logger = logging.getLogger(__name__)

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


def _add_item(manager, item, ignore_bounds: bool = False):
    """Добавить item на график.

    ``ignore_bounds=True`` — элемент не участвует в auto-range ViewBox.
    Нужно для всех TextItem/LabelItem-подобных элементов, иначе они
    «расталкивают» поле в auto-режиме (особенно band/threshold).
    """
    if ignore_bounds:
        manager.graph_view.plotItem.addItem(item, ignoreBounds=True)
        return item
        
    manager.graph_view.addItem(item)
    return item


def _remove_item(manager, item):
    try:
        manager.graph_view.removeItem(item)
    except (AttributeError, RuntimeError) as exc:
        logger.debug("helper remove: %s", exc)


class _DraggableText(pg.TextItem):
    """TextItem, который можно таскать мышкой.

    Пока пользователь не двигал — родитель переставляет его
    автоматически (например, к середине курсоров). Как только
    пользователь сделал drag — позиция фиксируется, а helper.params
    хранит ``text_pos`` и ``_text_dragged``.
    """

    def __init__(self, *args, on_moved=None, **kwargs):
        self._suppress_pos_change = True
        self._on_moved = on_moved
        super().__init__(*args, **kwargs)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(200)
        self._suppress_pos_change = False

    def itemChange(self, change, value):
        if (change == QtWidgets.QGraphicsItem.ItemPositionHasChanged
                and not self._suppress_pos_change and self._on_moved is not None):
            try:
                self._on_moved(self.pos())
            except Exception:
                pass
        return super().itemChange(change, value)

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
    show_line1_label = bool(p.get("show_line1_label", True))
    show_line2_label = bool(p.get("show_line2_label", True))

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    # Всегда создаём метку на линии. Видимость переключаем отдельно через
    # setVisible — это надёжнее, чем label=None: label=None в некоторых
    # сборках pyqtgraph ломает layout/отрисовку InfiniteLine.
    label_fmt = f"{{value:{fmt}}}"
    lab_opts = {"color": color, "position": 0.92}

    if orient == "vertical":
        v1 = p.get("x1", cx - sx * 0.1)
        v2 = p.get("x2", cx + sx * 0.1)
        line1 = pg.InfiniteLine(pos=v1, angle=90, movable=True, pen=pen,
                                label=label_fmt, labelOpts=lab_opts)
        line2 = pg.InfiniteLine(pos=v2, angle=90, movable=True, pen=pen,
                                label=label_fmt, labelOpts=lab_opts)
    else:
        v1 = p.get("y1", cy - sy * 0.1)
        v2 = p.get("y2", cy + sy * 0.1)
        line1 = pg.InfiniteLine(pos=v1, angle=0, movable=True, pen=pen,
                                label=label_fmt, labelOpts=lab_opts)
        line2 = pg.InfiniteLine(pos=v2, angle=0, movable=True, pen=pen,
                                label=label_fmt, labelOpts=lab_opts)

    _add_item(manager, line1)
    _add_item(manager, line2)

    # Раздельная видимость «значения» (метки) на каждой линии
    for line, visible in ((line1, show_line1_label), (line2, show_line2_label)):
        try:
            lbl = getattr(line, "label", None)
            if lbl is not None:
                lbl.setVisible(bool(visible))
        except Exception:
            logger.exception("cursors: set label visible failed")

    # Безопасный диапазон view (для только что созданного графика vb.viewRange()
    # может вернуть (0,1)/(0,1) или мусор — тогда откатываемся на дефолт).
    def _safe_view():
        try:
            (xmin, xmax), (ymin, ymax) = manager.graph_view.plotItem.vb.viewRange()
        except Exception:
            return 0.0, 1.0, 0.0, 1.0
        if not (xmax > xmin and ymax > ymin):
            return 0.0, 1.0, 0.0, 1.0
        return xmin, xmax, ymin, ymax

    def _midpoint():
        a, b = line1.value(), line2.value()
        xmin, xmax, ymin, ymax = _safe_view()
        if orient == "vertical":
            # центр по X, чуть ниже верхней кромки, чтобы текст не «прилипал»
            inset = (ymax - ymin) * 0.05
            return ((a + b) / 2.0, ymax - inset)
        # горизонтальная: правая кромка минус отступ, центр по Y
        inset = (xmax - xmin) * 0.05
        return (xmax - inset, (a + b) / 2.0)

    def _on_text_moved(pos):
        helper.params["text_pos"] = (pos.x(), pos.y())
        helper.params["_text_dragged"] = True

    # anchor: «верх-центр» для вертикали, «право-центр» для горизонтали —
    # текст всегда раскрывается внутрь поля.
    anchor = (0.5, 1.0) if orient == "vertical" else (1.0, 0.5)
    text = _DraggableText("", color=color, anchor=anchor,
                          on_moved=_on_text_moved)
    _add_item(manager, text, ignore_bounds=True)

    saved = p.get("text_pos")
    if saved and p.get("_text_dragged", False):
        text._suppress_pos_change = True
        try:
            text.setPos(saved[0], saved[1])
        finally:
            text._suppress_pos_change = False
    else:
        text._suppress_pos_change = True
        try:
            text.setPos(*_midpoint())
        finally:
            text._suppress_pos_change = False

    def update():
        a, b = line1.value(), line2.value()
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
        else:
            if show_dy:
                parts.append(f"ΔY = {b - a:{fmt}}")
            if show_dx:
                parts.append(f"ΔX = {x2 - x1:{fmt}}")
            if show_dist:
                parts.append(f"d = {np.hypot(x2 - x1, b - a):{fmt}}")
        text.setText("\n".join(parts))
        if not helper.params.get("_text_dragged", False):
            text._suppress_pos_change = True
            try:
                text.setPos(*_midpoint())
            finally:
                text._suppress_pos_change = False
        if orient == "vertical":
            helper.params.update({"x1": a, "x2": b})
        else:
            helper.params.update({"y1": a, "y2": b})

    line1.sigPositionChanged.connect(update)
    line2.sigPositionChanged.connect(update)
    update()
    return [line1, line2, text]

# ---------------------------------------------------------------------------
# Линейка — 2 drag-handle (TargetItem) + соединяющая линия + подпись
# ---------------------------------------------------------------------------
def _create_ruler(manager, helper):
    """Линейка: всегда показывает ΔX и ΔY (общая длина убрана)."""
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

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    line = pg.PlotDataItem([x1, x2], [y1, y2], pen=pen)
    text = pg.TextItem("", color=color, anchor=(0.5, -0.2))
    text.setPos((x1 + x2) / 2, (y1 + y2) / 2)
    p1 = pg.TargetItem(pos=(x1, y1), size=8, symbol="o", pen=color, brush=color)
    p2 = pg.TargetItem(pos=(x2, y2), size=8, symbol="o", pen=color, brush=color)

    for it in (line, text, p1, p2):
        _add_item(manager, it, ignore_bounds=(it is text))

    def update():
        a = p1.pos()
        b = p2.pos()
        line.setData([a.x(), b.x()], [a.y(), b.y()])
        text.setPos((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
        text.setText(
            f"ΔX = {b.x() - a.x():{fmt}}\nΔY = {b.y() - a.y():{fmt}}"
        )
        helper.params.update({
            "x1": a.x(), "y1": a.y(), "x2": b.x(), "y2": b.y(),
        })

    p1.sigPositionChanged.connect(update)
    p2.sigPositionChanged.connect(update)
    update()
    return [line, text, p1, p2]


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

    # TargetItem — только drag-handle (без встроенного label).
    # Встроенный TargetLabel в разных версиях pyqtgraph не даёт
    # применить цвет: ни через setAttr (метода нет), ни через
    # setText(color=...) (не перерисовывает текст).
    anchor = pg.TargetItem(
        pos=(x, y), size=6, symbol="s",
        pen=(200, 200, 200, 80),
        brush=(200, 200, 200, 80),
    )

    # Отдельный TextItem — полный контроль над цветом и шрифтом.
    # ignoreBounds — чтобы текст не растягивал auto-range.
    text_item = pg.TextItem(text=text, color=color, anchor=(0.5, 1.2))
    text_item.setFont(QtGui.QFont("Arial", font_size))
    text_item.setPos(x, y)

    _add_item(manager, anchor)
    _add_item(manager, text_item, ignore_bounds=True)

    def update():
        pos = anchor.pos()
        text_item.setPos(pos.x(), pos.y())
        helper.params.update({"x": pos.x(), "y": pos.y()})

    anchor.sigPositionChanged.connect(update)

    helper.params.update({
        "text": text, "x": x, "y": y,
        "color": color, "font_size": font_size,
    })
    return [anchor, text_item]


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
    # НОВОЕ:
    text_size = int(p.get("text_size", 12))
    arrow_size = int(p.get("arrow_size", 12))
    arrow_style = p.get("arrow_style", "default")

    _ARROW_STYLES = {
        "default": {"tipAngle": 30, "baseAngle": 20},
        "narrow":  {"tipAngle": 20, "baseAngle": 14},
        "wide":    {"tipAngle": 45, "baseAngle": 30},
        "sharp":   {"tipAngle": 15, "baseAngle": 10},
    }
    arrow_kw = dict(_ARROW_STYLES.get(arrow_style, _ARROW_STYLES["default"]))
    arrow_kw["headLen"] = arrow_size

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    line = pg.PlotDataItem([x1, x2], [y1, y2], pen=pen)
    arrow = pg.ArrowItem(pos=(x2, y2), pen=color, brush=color, **arrow_kw)

    text_item = pg.TextItem(text, color=color, anchor=(0, 0))
    try:
        text_item.setFont(QtGui.QFont("Arial", text_size))
        text_item.setText(text, color=color, size=f"{text_size}pt")
    except Exception:
        pass
    text_item.setPos(x1, y1)

    p1 = pg.TargetItem(pos=(x1, y1), size=8, symbol="o", pen=color, brush=color)
    p2 = pg.TargetItem(pos=(x2, y2), size=8, symbol="o", pen=color, brush=color)

    for it in (line, arrow, text_item, p1, p2):
        _add_item(manager, it, ignore_bounds=(it is text_item))

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
    return [line, arrow, text_item, p1, p2]


# ---------------------------------------------------------------------------
# Пин — TargetItem с настраиваемым символом и размером
# ---------------------------------------------------------------------------
def _create_pin(manager, helper):
    p = helper.params
    cx, cy, _, _ = _center(manager)
    x = p.get("x", cx)
    y = p.get("y", cy)
    text = p.get("text", "")
    description = p.get("description", "")
    color = p.get("color", "#ff3366")
    size = int(p.get("size", 12))
    symbol = p.get("symbol", "o")
    text_size = int(p.get("text_size", 12))

    item = pg.TargetItem(pos=(x, y), size=size, symbol=symbol,
                         pen=color, brush=color, label=text)
    try:
        lbl = item.label()
        if lbl is not None:
            lbl.setFont(QtGui.QFont("Arial", text_size))
            lbl.setText(text, color=color, size=f"{text_size}pt")
    except Exception:
        pass

    # Тултип с описанием: наводим на значок — читаем заметку.
    # Ставим на сам TargetItem и на подпись отдельно: hit-area у подписи
    # своя (LabelItem — отдельный QGraphicsItem внутри TargetItem),
    # и без дублирования tooltip не появлялся бы при наведении на текст.
    if description:
        try:
            item.setToolTip(description)
        except Exception:
            pass
        try:
            lbl = item.label()
            if lbl is not None:
                lbl.setToolTip(description)
        except Exception:
            pass

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
        "description": description,
        "color": color, "size": size, "symbol": symbol,
        "text_size": text_size,
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
    line = pg.InfiniteLine(
        pos=x, angle=90, movable=True, pen=pen,
        label=label,
        labelOpts={"color": color, "movable": True},  # <- перетаскивание значения
    )
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
    line = pg.InfiniteLine(
        pos=y, angle=0, movable=True, pen=pen,
        label=label,
        labelOpts={"color": color, "movable": True},  # <- перетаскивание значения
    )
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
    direction = p.get("direction", "off")
    show_count = bool(p.get("show_count", False))
    fill_alpha = float(p.get("fill_alpha", 0.15))

    pen = pg.mkPen(color=color, width=width, style=_style(style))
    # Единственный визуальный текст — перемещаемая подпись ниже.
    # Встроенный label у InfiniteLine НЕ создаём: иначе на графике
    # одновременно висели два текста («значение» у линии и «Порог = …»).
    line = pg.InfiniteLine(pos=y, angle=0, movable=True, pen=pen)
    _add_item(manager, line)

    # Заливка опасной зоны
    fill_items = []
    if direction in ("above", "below", "both"):
        c = pg.mkColor(color)
        c.setAlpha(int(max(0.0, min(1.0, fill_alpha)) * 255))
        brush = pg.mkBrush(c)
        huge = 1e9
        if direction in ("above", "both"):
            reg = pg.LinearRegionItem(values=(y, huge), brush=brush,
                                      movable=False, orientation="horizontal")
            reg.setZValue(-10)
            _add_item(manager, reg, ignore_bounds=True)
            fill_items.append(("above", reg))
        if direction in ("below", "both"):
            reg = pg.LinearRegionItem(values=(-huge, y), brush=brush,
                                      movable=False, orientation="horizontal")
            reg.setZValue(-10)
            _add_item(manager, reg, ignore_bounds=True)
            fill_items.append(("below", reg))

    # Единственная подпись: «Порог = …» + опц. счётчики точек.
    # Свисает вниз от верхней кромки поля, тянется мышкой.
    def _safe_view():
        try:
            (xmin, xmax), (ymin, ymax) = manager.graph_view.plotItem.vb.viewRange()
        except Exception:
            return 0.0, 1.0, 0.0, 1.0
        if not (xmax > xmin and ymax > ymin):
            return 0.0, 1.0, 0.0, 1.0
        return xmin, xmax, ymin, ymax

    def _default_pos():
        v = line.value()
        xmin, xmax, _, _ = _safe_view()
        inset = (xmax - xmin) * 0.02
        return (xmin + inset, v)

    def _on_text_moved(pos):
        helper.params["text_pos"] = (pos.x(), pos.y())
        helper.params["_text_dragged"] = True

    label = _DraggableText("", color=color, anchor=(0.0, 1.0),
                           on_moved=_on_text_moved)
    _add_item(manager, label, ignore_bounds=True)

    saved = p.get("text_pos")
    if saved and p.get("_text_dragged", False):
        label._suppress_pos_change = True
        try:
            label.setPos(saved[0], saved[1])
        finally:
            label._suppress_pos_change = False
    else:
        label._suppress_pos_change = True
        try:
            label.setPos(*_default_pos())
        finally:
            label._suppress_pos_change = False

    def update():
        v = line.value()
        text = f"{prefix} = {v:{fmt}}"
        if show_count:
            n_above = n_below = 0
            for item in manager.graph_view.plotItem.listDataItems():
                try:
                    data = item.getData()
                    if data is None or data[1] is None:
                        continue
                    ys = np.asarray(data[1], dtype=float)
                    ys = ys[~np.isnan(ys)]
                    n_above += int(np.sum(ys > v))
                    n_below += int(np.sum(ys < v))
                except Exception:
                    continue
            text += f"\n▲ {n_above}  ▼ {n_below}"
        label.setText(text)
        for kind, reg in fill_items:
            if kind == "above":
                reg.setRegion([v, 1e9])
            else:
                reg.setRegion([-1e9, v])
        if not helper.params.get("_text_dragged", False):
            label._suppress_pos_change = True
            try:
                label.setPos(*_default_pos())
            finally:
                label._suppress_pos_change = False
        helper.params.update({"y": v})

    line.sigPositionChanged.connect(update)
    update()
    return [line, label] + [reg for _, reg in fill_items]

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

    # Для горизонтальной полосы — y1/y2, а не x1/x2.
    if orient == "vertical":
        v1 = p.get("x1", cx - sx * 0.1)
        v2 = p.get("x2", cx + sx * 0.1)
    else:
        v1 = p.get("y1", cy - sy * 0.1)
        v2 = p.get("y2", cy + sy * 0.1)

    c = pg.mkColor(color)
    c.setAlpha(int(max(0.0, min(1.0, alpha)) * 255))
    brush = pg.mkBrush(c)

    region = pg.LinearRegionItem(
        values=(v1, v2), brush=brush, movable=True,
        orientation="vertical" if orient == "vertical" else "horizontal",
    )
    _add_item(manager, region, ignore_bounds=True)

    # anchor: текст «свисает» внутрь поля от верхней/правой кромки.
    anchor = (0.5, 1.0) if orient == "vertical" else (1.0, 0.5)

    def _on_text_moved(pos):
        helper.params["text_pos"] = (pos.x(), pos.y())
        helper.params["_text_dragged"] = True

    text = _DraggableText("", color=color, anchor=anchor,
                          on_moved=_on_text_moved)
    _add_item(manager, text, ignore_bounds=True)

    def _safe_view():
        try:
            (xmin, xmax), (ymin, ymax) = manager.graph_view.plotItem.vb.viewRange()
        except Exception:
            return 0.0, 1.0, 0.0, 1.0
        if not (xmax > xmin and ymax > ymin):
            return 0.0, 1.0, 0.0, 1.0
        return xmin, xmax, ymin, ymax

    def _default_pos():
        a, b = region.getRegion()
        xmin, xmax, ymin, ymax = _safe_view()
        if orient == "vertical":
            inset = (ymax - ymin) * 0.05
            return ((a + b) / 2.0, ymax - inset)
        inset = (xmax - xmin) * 0.05
        return (xmax - inset, (a + b) / 2.0)

    saved = p.get("text_pos")
    if saved and p.get("_text_dragged", False):
        text._suppress_pos_change = True
        try:
            text.setPos(saved[0], saved[1])
        finally:
            text._suppress_pos_change = False
    else:
        text._suppress_pos_change = True
        try:
            text.setPos(*_default_pos())
        finally:
            text._suppress_pos_change = False

    def update():
        a, b = region.getRegion()
        text.setText(f"Δ = {b - a:{fmt}}" if show_label else "")
        if not helper.params.get("_text_dragged", False):
            text._suppress_pos_change = True
            try:
                text.setPos(*_default_pos())
            finally:
                text._suppress_pos_change = False
        if orient == "vertical":
            helper.params.update({"x1": a, "x2": b})
        else:
            helper.params.update({"y1": a, "y2": b})

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