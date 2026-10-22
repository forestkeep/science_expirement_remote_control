"""Встроенные safe defaults и стиль-профиль.

Работают без PlotStyle, без внешних файлов и без интернета.
"""

SAFE_DEFAULTS = {
    "figure.dpi": 300,
    "figure.background": "#ffffff",
    "figure.face_color": "#ffffff",
    "figure.font.family": "DejaVu Sans",
    "figure.font.size": 8.0,
    "figure.line.width": 0.75,
    "figure.line.color": "#000000",
    "figure.axes.line_width": 0.5,
    "figure.axes.tick_size": 7.0,
    "figure.axes.label_size": 8.0,
    "panel.title_size": 9.0,
    "panel.title_weight": "bold",
    "annotation.text_size": 8.0,
    "annotation.scalebar.width_mm": 5.0,
    "annotation.scalebar.thickness_pt": 0.6,
    "annotation.bracket.width_pt": 0.6,
    "color.palette": "okabe_ito",
    "color.background": "#ffffff",
    "color.foreground": "#000000",
    "margin.mm": 2.0,
}

STYLE_PROFILE_DEFAULT = {
    "figure.line.width": 1.0,
    "figure.font.size": 9.0,
    "figure.axes.line_width": 0.6,
}

OKABE_ITO = [
    "#000000", "#E69F00", "#56B4E9", "#009E73",
    "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
]

BUILTIN_JOURNALS = {
    "nature_single": {
        "schema_version": 1,
        "id": "nature_single",
        "name": "Nature single column",
        "column": {"width_mm": 89.0, "height_mm": 120.0, "dpi": 300},
        "constraints": {
            "min_font_pt": 5.0,
            "min_line_pt": 0.25,
            "dpi_min": 300,
            "colorblind_safe": False,
            "margin_mm": 2.0,
        },
        "defaults": {
            "figure.font.family": "Arial",
            "figure.font.size": 7.0,
            "figure.line.width": 0.75,
        },
    },
    "nature_double": {
        "schema_version": 1,
        "id": "nature_double",
        "name": "Nature double column",
        "column": {"width_mm": 183.0, "height_mm": 247.0, "dpi": 300},
        "constraints": {
            "min_font_pt": 5.0,
            "min_line_pt": 0.25,
            "dpi_min": 300,
            "colorblind_safe": False,
            "margin_mm": 3.0,
        },
        "defaults": {
            "figure.font.family": "Arial",
            "figure.font.size": 7.0,
            "figure.line.width": 0.75,
        },
    },
}