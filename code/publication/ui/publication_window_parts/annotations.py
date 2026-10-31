from __future__ import annotations

from PyQt5.QtWidgets import QDialog

from ..inspector_annotation import AnnotationPropertiesDialog, create_annotation


class PublicationWidgetAnnotationsMixin:
    # ==================================================================
    # Аннотации
    # ==================================================================
    def _on_annotation_create(self, kind: str):
        panel_id = self._current_panel_id
        ann = create_annotation(self.spec, kind, panel_id)
        dialog = AnnotationPropertiesDialog(ann, self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.apply()
        self._refresh_tree()
        self._refresh_counters()
        self._on_annotation_selected(ann.id)
        self._schedule_render()

    def _on_annotation_edit(self, ann_id: str):
        ann = self.spec.find_presentation(ann_id)
        if ann is None:
            return
        dialog = AnnotationPropertiesDialog(ann, self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.apply()
            self._refresh_tree()
            if self._current_ann_id == ann_id:
                self._inspector_annotation.set_annotation(ann_id)
            self._schedule_render()

    def _on_annotation_delete(self, ann_id: str):
        before = len(self.spec.presentation_annotations)
        self.spec.presentation_annotations = [
            a for a in self.spec.presentation_annotations if a.id != ann_id
        ]
        if len(self.spec.presentation_annotations) == before:
            return
        if self._current_ann_id == ann_id:
            self._current_ann_id = None
            self._inspector_stack.setCurrentWidget(self._inspector_figure)
        self._refresh_tree()
        self._refresh_counters()
        self._schedule_render()

    def _on_annotation_geometry_changed(self, ann_id: str, coords: tuple):
        ann = self.spec.find_presentation(ann_id)
        if ann is not None:
            ann.coords = tuple(coords)
            self._schedule_render()