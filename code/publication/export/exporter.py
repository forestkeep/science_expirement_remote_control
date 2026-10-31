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

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from ..renderers.mpl_renderer import MatplotlibRenderer
from ..core.sentinel import MISSING
from .provenance import Provenance

logger = logging.getLogger(__name__)


# =====================================================================
# Экспорт фигуры (основной класс)
# =====================================================================
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


# =====================================================================
# Фоновый экспорт (QThread) с прогрессом и отменой
# =====================================================================
class _ExportWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    cancelled = pyqtSignal()

    def __init__(self, exporter: Exporter, dir_path: str, include_png: bool):
        super().__init__()
        self.exporter = exporter
        self.dir_path = dir_path
        self.include_png = include_png
        self.cancel_requested = False

    def _check_cancel(self) -> bool:
        if self.cancel_requested:
            self.cancelled.emit()
            return True
        return False

    def run(self):
        try:
            os.makedirs(self.dir_path, exist_ok=True)
            steps = 8 + (1 if self.include_png else 0)
            done = 0

            def tick(msg: str):
                nonlocal done
                if self._check_cancel():
                    raise RuntimeError("cancelled")
                done += 1
                self.progress.emit(int(done / steps * 100), msg)

            pdf_path = os.path.join(self.dir_path, "figure.pdf")
            self.exporter.export_pdf(pdf_path, dpi=int(self.exporter._dpi()))
            tick("figure.pdf")

            svg_path = os.path.join(self.dir_path, "figure.svg")
            self.exporter.export_svg(svg_path)
            tick("figure.svg")

            if self.include_png:
                png_path = os.path.join(self.dir_path, "figure.png")
                self.exporter.export_png(png_path, dpi=int(self.exporter._dpi()))
                tick("figure.png")

            with open(os.path.join(self.dir_path, "spec.json"), "w", encoding="utf-8") as f:
                json.dump(self.exporter.spec.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
            tick("spec.json")

            if self.exporter.preset is not None:
                with open(os.path.join(self.dir_path, "preset.json"), "w", encoding="utf-8") as f:
                    json.dump(self.exporter.preset.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
            tick("preset.json")

            resolved = self.exporter._collect_resolved_style()
            with open(os.path.join(self.dir_path, "resolved_style.json"), "w", encoding="utf-8") as f:
                json.dump(resolved, f, ensure_ascii=False, indent=2, sort_keys=True)
            tick("resolved_style.json")

            from ..model.stylestack import list_overrides
            ov = list_overrides(self.exporter.spec)
            with open(os.path.join(self.dir_path, "overrides.json"), "w", encoding="utf-8") as f:
                json.dump(ov, f, ensure_ascii=False, indent=2, sort_keys=True)
            tick("overrides.json")

            prov = Provenance.collect(self.exporter.spec, self.exporter.preset, ov)
            with open(os.path.join(self.dir_path, "provenance.json"), "w", encoding="utf-8") as f:
                json.dump(prov.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
            tick("provenance.json")

            if self.exporter.validation_report is not None:
                with open(os.path.join(self.dir_path, "validation.json"), "w", encoding="utf-8") as f:
                    json.dump(self.exporter.validation_report.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
            tick("validation.json")

            self.finished.emit(self.dir_path)
        except RuntimeError as exc:
            if str(exc) == "cancelled":
                return
            self.failed.emit(str(exc))
        except Exception as exc:
            logger.exception("Background export failed")
            self.failed.emit(str(exc))


class BackgroundExporter(QObject):
    """Повторно запускаемый фоновый экспорт с прогрессом и отменой."""

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, exporter: Exporter, parent: QObject = None):
        super().__init__(parent)
        self.exporter = exporter
        self._thread = None
        self._worker = None
        self._finished_cb = None
        self._failed_cb = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def start(self, dir_path: str, include_png: bool = False,
              on_finished=None, on_failed=None) -> None:
        if self.is_running():
            logger.warning("BackgroundExporter.start: already running, ignored")
            return

        self._finished_cb = on_finished
        self._failed_cb = on_failed

        self._thread = QThread(self)
        self._worker = _ExportWorker(self.exporter, dir_path, include_png)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)

        self._thread.start()

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel_requested = True

    def wait(self, timeout_ms: int = 60000) -> bool:
        if self._thread is None:
            return True
        return self._thread.wait(timeout_ms)

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(3000)
        self._thread = None
        self._worker = None

    def _on_finished(self, path: str):
        self._cleanup()
        self.finished.emit(path)
        if self._finished_cb:
            self._finished_cb(path)

    def _on_failed(self, msg: str):
        self._cleanup()
        self.failed.emit(msg)
        if self._failed_cb:
            self._failed_cb(msg)

    def _on_cancelled(self):
        self._cleanup()
        self.cancelled.emit()