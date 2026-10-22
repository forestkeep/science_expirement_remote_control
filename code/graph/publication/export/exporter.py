"""Экспорт фигуры: PDF/SVG/PNG + export_package().

Вектор-first. PDF/SVG содержат редактируемый текст.
PNG/TIFF — по запросу с контролем DPI.
"""
from __future__ import annotations
import json
import logging
import os
from dataclasses import asdict
from typing import Any, Callable, Dict, Optional

from ..renderers.mpl_renderer import MatplotlibRenderer
from ..core.sentinel import MISSING
from .provenance import Provenance

logger = logging.getLogger(__name__)


class Exporter:
    def __init__(
        self,
        spec,
        preset,
        style_stack,
        data_resolver: Callable,
        overrides_resolver: Callable,
        validation_report=None,
    ):
        self.spec = spec
        self.preset = preset
        self.stack = style_stack
        self.data_resolver = data_resolver
        self.overrides_resolver = overrides_resolver
        self.validation_report = validation_report
        self.renderer = MatplotlibRenderer()

    # ------------------------------------------------------------ single file
    def export_pdf(self, path: str, dpi: int = 300) -> str:
        return self._export(path, "pdf", dpi)

    def export_svg(self, path: str) -> str:
        return self._export(path, "svg", dpi=72)

    def export_png(self, path: str, dpi: int = 600) -> str:
        return self._export(path, "png", dpi)

    def _export(self, path: str, fmt: str, dpi: int) -> str:
        fig = self.renderer.create_figure(self.spec)
        self.renderer.render(
            fig, self.spec, self.data_resolver,
            self.stack.resolve, self.overrides_resolver,
        )
        self.renderer.save(fig, path, fmt=fmt, dpi=dpi)
        # освободить память
        try:
            fig.clf()
        except Exception:
            pass
        return path

    # --------------------------------------------------------- export_package
    def export_package(self, dir_path: str, include_png: bool = False) -> str:
        os.makedirs(dir_path, exist_ok=True)

        # 1) figure.pdf
        pdf_path = os.path.join(dir_path, "figure.pdf")
        self.export_pdf(pdf_path, dpi=int(self._dpi()))

        # 2) figure.svg
        svg_path = os.path.join(dir_path, "figure.svg")
        self.export_svg(svg_path)

        # 3) (опционально) figure.png
        if include_png:
            png_path = os.path.join(dir_path, "figure.png")
            self.export_png(png_path, dpi=int(self._dpi()))

        # 4) spec.json
        with open(os.path.join(dir_path, "spec.json"), "w", encoding="utf-8") as f:
            json.dump(self.spec.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)

        # 5) preset.json — снимок пресета
        if self.preset is not None:
            with open(os.path.join(dir_path, "preset.json"), "w", encoding="utf-8") as f:
                json.dump(self.preset.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)

        # 6) resolved_style.json
        resolved = self._collect_resolved_style()
        with open(os.path.join(dir_path, "resolved_style.json"), "w", encoding="utf-8") as f:
            json.dump(resolved, f, ensure_ascii=False, indent=2, sort_keys=True)

        # 7) overrides.json
        from ..model.stylestack import list_overrides
        ov = list_overrides(self.spec)
        with open(os.path.join(dir_path, "overrides.json"), "w", encoding="utf-8") as f:
            json.dump(ov, f, ensure_ascii=False, indent=2, sort_keys=True)

        # 8) provenance.json
        prov = Provenance.collect(self.spec, self.preset, ov)
        with open(os.path.join(dir_path, "provenance.json"), "w", encoding="utf-8") as f:
            json.dump(prov.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)

        # 9) validation.json
        if self.validation_report is not None:
            with open(os.path.join(dir_path, "validation.json"), "w", encoding="utf-8") as f:
                json.dump(self.validation_report.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)

        return dir_path

    def _dpi(self) -> int:
        dpi = self.stack.resolve("figure.dpi")
        return 300 if dpi is MISSING else int(dpi)

    def _collect_resolved_style(self) -> Dict[str, Any]:
        """Собрать все ключи из известных слоёв и resolved-значения."""
        keys = set()
        for layer in (self.stack.safe_defaults, self.stack.style_profile,
                      self.stack.journal_defaults, self.stack.lab_profile,
                      self.spec.figure_overrides):
            keys.update(layer.keys())
        for p in self.spec.panels:
            keys.update(p.style_overrides.keys())
        result = {}
        for k in sorted(keys):
            v = self.stack.resolve(k)
            result[k] = None if v is MISSING else v
        return result


# --------------------------------------------------------------- background
from PyQt5.QtCore import QObject, pyqtSignal


class _ExportWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, exporter: Exporter, dir_path: str, include_png: bool):
        super().__init__()
        self.exporter = exporter
        self.dir_path = dir_path
        self.include_png = include_png

    def run(self):
        try:
            result = self.exporter.export_package(self.dir_path, include_png=self.include_png)
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Background export failed")
            self.failed.emit(str(e))


class BackgroundExporter:
    """Тонкая обёртка: запускает экспорт в отдельном потоке."""

    def __init__(self, exporter: Exporter, parent: QObject = None):
        from PyQt5.QtCore import QThread
        self._thread = QThread(parent)
        self._worker = _ExportWorker(exporter, "", False)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._finished_cb = None
        self._failed_cb = None

    def start(self, dir_path: str, include_png: bool = False,
              on_finished: Callable[[str], None] = None,
              on_failed: Callable[[str], None] = None) -> None:
        self._worker.dir_path = dir_path
        self._worker.include_png = include_png
        self._finished_cb = on_finished
        self._failed_cb = on_failed
        self._thread.start()

    def _on_finished(self, path: str):
        self._thread.quit()
        if self._finished_cb:
            self._finished_cb(path)

    def _on_failed(self, msg: str):
        self._thread.quit()
        if self._failed_cb:
            self._failed_cb(msg)

    def wait(self, timeout_ms: int = 60000) -> bool:
        return self._thread.wait(timeout_ms)
    