# Publication layer — что переносится, что нет

## Что переносится из графика-источника

Из `LineStyle` живой кривой в публикационный рендер попадают:

- `line.color` — цвет линии;
- `line.width` — толщина линии (pt);
- `line.style` — тип линии (Solid / Dash / Dot / DashDot / DashDotDot);
- `marker.symbol` — символ маркера;
- `marker.size` — размер маркера;
- `marker.edge` — цвет обводки маркера;
- `marker.face` — цвет заливки маркера.

Из данных кривой:

- `curve.name` — легенда (имя кривой на момент снапшота).

## Что переносится из пресета журнала

Из `JournalPreset.defaults` / `StyleStack`:

- `axes.line_width`;
- `axes.tick_size`;
- `axes.label_size`;
- `font.family`;
- `legend.enabled`;
- `legend.font_size`;
- `figure.dpi`;
- `figure.background`.

## Что переопределяется на уровне панели

- `axis.x_label`;
- `axis.y_label`;
- `panel.title`.

## Что НЕ переносится в v1

- `uncertainty.bars` — полосы погрешностей точек кривой;
- `analysis.attached` — attached-панели анализа (производные, интегралы);
- `analysis.domain` — domain-вкладки (FFT, автокорреляция).

Эти атрибуты помечены в `CONTRACT` как `Origin.CONSTANT` с `fallback=None`.
Рендерер их игнорирует. Чтобы включить перенос, нужно:

1. Изменить `origin` соответствующего атрибута в `publication/contract.py::CONTRACT`
   на `Origin.SOURCE_STYLE` (или `Origin.PRESET`);
2. Реализовать рендер в `publication/renderers/mpl_renderer.py`
   (`_plot_uncertainty` / `_plot_artifacts` уже реализованы, но вызываются
   только при включённом `show_tools` панели);
3. Добавить тест в `tests/test_publication_contract.py`.

## Таблица контракта

| ключ | источник | fallback | примечание |
|------|----------|----------|------------|
| `line.color` | source_style | `#1f77b4` | |
| `line.width` | source_style | `1.0` | |
| `line.style` | source_style | `Solid` | |
| `marker.symbol` | source_style |  | |
| `marker.size` | source_style | `5` | |
| `marker.edge` | source_style | `#ffffff` | |
| `marker.face` | source_style | `#ffffff` | |
| `curve.name` | source_data |  | |
| `axis.x_label` | panel_override |  | |
| `axis.y_label` | panel_override |  | |
| `panel.title` | panel_override |  | |
| `axes.line_width` | preset | `0.5` | |
| `axes.tick_size` | preset | `7.0` | |
| `axes.label_size` | preset | `8.0` | |
| `font.family` | preset | `DejaVu Sans` | |
| `legend.enabled` | preset | `True` | |
| `legend.font_size` | preset | `7.0` | |
| `figure.dpi` | preset | `300` | участвует в валидации |
| `figure.background` | preset | `#ffffff` | |
| `uncertainty.bars` | constant |  | не переносится в v1 |
| `analysis.attached` | constant |  | не переносится в v1 |
| `analysis.domain` | constant |  | не переносится в v1 |

Таблица сгенерирована `python -c "from publication.contract import render_readme; print(render_readme())"`
и намеренно продублирована здесь статично: пользователь читает файл, а не запускает код.