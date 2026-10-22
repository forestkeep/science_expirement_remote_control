from PyQt5 import QtCore

PRESETS_LINE = {
    "Scientific 1 - Blue Solid": {
        'color': '#1f77b4',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'o',
        'symbol_size': 8,
        'symbol_color': '#1f77b4',
        'fill_color': 'w'
    },
    "Scientific 2 - Red Dashed": {
        'color': '#d62728',
        'line_style': QtCore.Qt.DashLine,
        'line_width': 2,
        'symbol': 's',
        'symbol_size': 8,
        'symbol_color': '#d62728',
        'fill_color': 'w'
    },
    "Scientific 3 - Green Dotted": {
        'color': '#2ca02c',
        'line_style': QtCore.Qt.DotLine,
        'line_width': 2,
        'symbol': "arrow_up",
        'symbol_size': 8,
        'symbol_color': '#2ca02c',
        'fill_color': 'w'
    },
    "Scientific 4 - Purple DashDot": {
        'color': '#9467bd',
        'line_style': QtCore.Qt.DashDotLine,
        'line_width': 2,
        'symbol': 'd',
        'symbol_size': 8,
        'symbol_color': '#9467bd',
        'fill_color': 'w'
    },
    "Scientific 5 - Brown Solid Circle": {
        'color': '#8c564b',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'o',
        'symbol_size': 7,
        'symbol_color': '#8c564b',
        'fill_color': '#ff7f0e'
    },
    "Scientific 6 - Orange Solid Square": {
        'color': '#ff7f0e',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 's',
        'symbol_size': 7,
        'symbol_color': '#ff7f0e',
        'fill_color': '#1f77b4'
    },
    "Scientific 7 - Magenta Solid Diamond": {
        'color': '#e377c2',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'd',
        'symbol_size': 7,
        'symbol_color': '#e377c2',
        'fill_color': '#2ca02c'
    },
    "Scientific 8 - Gray Solid Cross": {
        'color': '#7f7f7f',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': '+',
        'symbol_size': 7,
        'symbol_color': '#7f7f7f',
        'fill_color': 'w'
    },
    "Scientific 9 - Black Thick Solid": {
        'color': '#000000',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 3,
        'symbol': 'o',
        'symbol_size': 6,
        'symbol_color': '#000000',
        'fill_color': 'w'
    },
    "Scientific 10 - Blue-Red Dual": {
        'color': '#1f77b4',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'o',
        'symbol_size': 6,
        'symbol_color': '#d62728',
        'fill_color': '#d62728'
    },

    "Scientific 11 - Orange Dotted": {
        'color': '#ff7f0e',
        'line_style': QtCore.Qt.DotLine,
        'line_width': 2,
        'symbol': 't1',
        'symbol_size': 7,
        'symbol_color': '#ff7f0e',
        'fill_color': 'w'
    },
    "Scientific 12 - Green Dashed": {
        'color': '#2ca02c',
        'line_style': QtCore.Qt.DashLine,
        'line_width': 2,
        'symbol': 'p',
        'symbol_size': 8,
        'symbol_color': '#2ca02c',
        'fill_color': 'w'
    },
    "Scientific 13 - Red Solid": {
        'color': '#d62728',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'x',
        'symbol_size': 7,
        'symbol_color': '#d62728',
        'fill_color': 'w'
    },
    "Scientific 14 - Purple Dotted": {
        'color': '#9467bd',
        'line_style': QtCore.Qt.DotLine,
        'line_width': 2,
        'symbol': 'h',
        'symbol_size': 8,
        'symbol_color': '#9467bd',
        'fill_color': 'w'
    },
    "Scientific 15 - Brown DashDot": {
        'color': '#8c564b',
        'line_style': QtCore.Qt.DashDotLine,
        'line_width': 2,
        'symbol': 'star',
        'symbol_size': 7,
        'symbol_color': '#8c564b',
        'fill_color': 'w'
    },
    "Scientific 16 - Gray Dashed": {
        'color': '#7f7f7f',
        'line_style': QtCore.Qt.DashLine,
        'line_width': 2,
        'symbol': 'd',
        'symbol_size': 7,
        'symbol_color': '#7f7f7f',
        'fill_color': 'w'
    },
    "Scientific 17 - Blue DotLine": {
        'color': '#1f77b4',
        'line_style': QtCore.Qt.DotLine,
        'line_width': 2,
        'symbol': 'arrow_down',
        'symbol_size': 8,
        'symbol_color': '#1f77b4',
        'fill_color': 'w'
    },
    "Scientific 18 - Black Thin Solid": {
        'color': '#000000',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 1,
        'symbol': '+',
        'symbol_size': 6,
        'symbol_color': '#000000',
        'fill_color': 'w'
    },
    "Scientific 19 - Magenta DashDot": {
        'color': '#e377c2',
        'line_style': QtCore.Qt.DashDotLine,
        'line_width': 2,
        'symbol': 't2',
        'symbol_size': 7,
        'symbol_color': '#e377c2',
        'fill_color': 'w'
    },
    "Scientific 20 - Olive Solid": {
        'color': '#bcbd22',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': '_',
        'symbol_size': 6,
        'symbol_color': '#bcbd22',
        'fill_color': 'w'
    },
    "Scientific 21 - Cyan Dashed": {
        'color': '#17becf',
        'line_style': QtCore.Qt.DashLine,
        'line_width': 2,
        'symbol': 'arrow_right',
        'symbol_size': 8,
        'symbol_color': '#17becf',
        'fill_color': 'w'
    },
    "Scientific 22 - Black Double": {
        'color': '#000000',
        'line_style': QtCore.Qt.DashDotDotLine,
        'line_width': 2,
        'symbol': '|',
        'symbol_size': 6,
        'symbol_color': '#000000',
        'fill_color': 'w'
    },
    "Scientific 23 - Red-Blue Combo": {
        'color': '#d62728',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 's',
        'symbol_size': 6,
        'symbol_color': '#1f77b4',
        'fill_color': '#1f77b4'
    },
    "Scientific 24 - Green-Black Combo": {
        'color': '#2ca02c',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'o',
        'symbol_size': 6,
        'symbol_color': "#183B23",
        'fill_color': "#36325E"
    },
    "Scientific 25 - Purple Open": {
        'color': '#9467bd',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'p',
        'symbol_size': 7,
        'symbol_color': '#9467bd',
        'fill_color': 'w'
    },
    "Scientific 26 - Gray Filled": {
        'color': '#7f7f7f',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'd',
        'symbol_size': 7,
        'symbol_color': '#7f7f7f',
        'fill_color': '#7f7f7f'
    },
    "Scientific 27 - Orange SolidLine": {
        'color': '#ff7f0e',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 0,
        'symbol': 't3',
        'symbol_size': 8,
        'symbol_color': '#ff7f0e',
        'fill_color': 'w'
    },
    "Scientific 28 - Blue Cross": {
        'color': '#1f77b4',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 2,
        'symbol': 'crosshair',
        'symbol_size': 8,
        'symbol_color': '#1f77b4',
        'fill_color': 'w'
    },
    "Scientific 29 - Black Minimal": {
        'color': '#000000',
        'line_style': QtCore.Qt.DotLine,
        'line_width': 1,
        'symbol': 'crosshair',
        'symbol_size': 0,
        'symbol_color': "#6D4444",
        'fill_color': 'w'
    },
    "Scientific 30 - Red Thick": {
        'color': '#d62728',
        'line_style': QtCore.Qt.SolidLine,
        'line_width': 3,
        'symbol': 'arrow_up',
        'symbol_size': 8,
        'symbol_color': '#d62728',
        'fill_color': 'w'
    }
}