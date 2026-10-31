"""Встроенные safe defaults, палитры и стиль-профили.

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

# ---------------------------------------------------------------- палитры

OKABE_ITO = [
    "#000000", "#E69F00", "#56B4E9", "#009E73",
    "#F0E442", "#0072B2", "#D55E00", "#CC79A7",
]

NATURE_PALETTE = [
    "#000000", "#1f77b4", "#ff7f0e", "#2ca02c",
    "#d62728", "#9467bd", "#8c564b", "#e377c2",
]

SCIENCE_PALETTE = [
    "#000000", "#3b7dd8", "#d43f3a", "#EE9A3A",
    "#5cb85c", "#9b59b6", "#17becf", "#7f7f7f",
]

PALETTES = {
    "okabe_ito": OKABE_ITO,
    "nature": NATURE_PALETTE,
    "science": SCIENCE_PALETTE,
}

# --------------------------------------------------------------- профили

STYLE_PROFILES = {
    "okabe_ito": {
        "id": "okabe_ito",
        "name": "Okabe-Ito",
        "description": "Универсальная палитра, colorblind-safe",
        "palette": "okabe_ito",
        "defaults": {
            "figure.font.family": "DejaVu Sans",
            "figure.font.size": 8.0,
            "figure.line.width": 1.0,
            "figure.axes.tick_size": 7.0,
            "figure.axes.label_size": 8.0,
            "color.palette": "okabe_ito",
        },
    },
    "nature": {
        "id": "nature",
        "name": "Nature",
        "description": "Строгий журнальный стиль, тонкие линии",
        "palette": "nature",
        "defaults": {
            "figure.font.family": "Arial",
            "figure.font.size": 7.0,
            "figure.line.width": 0.75,
            "figure.axes.tick_size": 7.0,
            "figure.axes.label_size": 8.0,
            "color.palette": "nature",
        },
    },
    "science": {
        "id": "science",
        "name": "Science",
        "description": "Крупнее шрифты, контрастная палитра",
        "palette": "science",
        "defaults": {
            "figure.font.family": "Helvetica",
            "figure.font.size": 8.0,
            "figure.line.width": 1.0,
            "figure.axes.tick_size": 8.0,
            "figure.axes.label_size": 9.0,
            "color.palette": "science",
        },
    },
}


def list_style_profiles():
    return list(STYLE_PROFILES.keys())


def get_style_profile(profile_id: str):
    return STYLE_PROFILES.get(profile_id)


def get_palette(name: str):
    return list(PALETTES.get(name, OKABE_ITO))


# --------------------------------------------------------------- журналы

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
    "science_double": {
        "schema_version": 1,
        "id": "science_double",
        "name": "Science double column",
        "column": {"width_mm": 183.0, "height_mm": 247.0, "dpi": 300},
        "constraints": {
            "min_font_pt": 6.0,
            "min_line_pt": 0.5,
            "dpi_min": 300,
            "colorblind_safe": True,
            "margin_mm": 3.0,
        },
        "defaults": {
            "figure.font.family": "Helvetica",
            "figure.font.size": 8.0,
            "figure.line.width": 1.0,
        },
    },
}