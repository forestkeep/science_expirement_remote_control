"""Ручной запуск headless-рендера без приложения.

    python -m graph.publication.examples.demo_headless out/figure.pdf
"""
from __future__ import annotations
import os
import sys

# Убедиться, что graph публикуется в PYTHONPATH
if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out/figure.pdf"
    here = os.path.dirname(os.path.abspath(__file__))
    spec_path = os.path.join(here, "session_example.json")
    from graph.publication.headless import render_headless
    result = render_headless(
        spec_path, out,
        preset_id="nature_double",
        data_provider=None,      # синтетика
        export_dir=os.path.join(os.path.dirname(out), "package"),
    )
    print(result)