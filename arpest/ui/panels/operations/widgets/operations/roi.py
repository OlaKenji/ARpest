"""UI widget for ROI selection on the active figure."""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .base import OperationWidget


class RoiOperationWidget(OperationWidget):
    title = "ROI"
    category = "General"
    description = "Draw a rectangular ROI on the figure to scope computed curves and cuts."

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        desc = QLabel("Use a rectangular ROI to limit computed curves and cut panels (non-destructive).")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.enable_checkbox = QCheckBox("Enable ROI")
        self.enable_checkbox.toggled.connect(self._on_enable_toggled)
        layout.addWidget(self.enable_checkbox)

        bounds_title = QLabel("ROI bounds:")
        layout.addWidget(bounds_title)
        self.bounds_label = QLabel("-")
        self.bounds_label.setWordWrap(True)
        layout.addWidget(self.bounds_label)

        self.count_label = QLabel("")
        self.count_label.setWordWrap(True)
        layout.addWidget(self.count_label)

        buttons_row = QHBoxLayout()
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        buttons_row.addWidget(self.reset_btn)
        buttons_row.addWidget(self.clear_btn)
        layout.addLayout(buttons_row)

        layout.addStretch()
        self.setLayout(layout)

        self._roi_controller = None
        self._sync_from_controller()

    def _roi(self):
        if self._roi_controller is None:
            self._roi_controller = self._get_context_value("roi_controller")
            if self._roi_controller is not None:
                try:
                    self._roi_controller.add_listener(self._sync_from_controller)
                except Exception:
                    pass
        return self._roi_controller

    def _sync_from_controller(self) -> None:
        controller = self._roi()
        if controller is None or not getattr(controller, "is_supported", lambda: False)():
            self.enable_checkbox.setEnabled(False)
            self.reset_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            self.bounds_label.setText("ROI not available for this view.")
            self.count_label.setText("")
            return

        enabled = bool(controller.is_enabled())
        self.enable_checkbox.setEnabled(True)
        self.enable_checkbox.blockSignals(True)
        self.enable_checkbox.setChecked(enabled)
        self.enable_checkbox.blockSignals(False)

        self.reset_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)

        bounds = controller.get_bounds()
        labels = controller.get_axis_labels()
        self._set_bounds_text(bounds, labels)

    def _set_bounds_text(
        self,
        bounds: Optional[Tuple[float, float, float, float]],
        labels: Optional[Tuple[str, str]],
    ) -> None:
        if bounds is None:
            self.bounds_label.setText("ROI disabled.")
            self.count_label.setText("")
            return

        x_min, x_max, y_min, y_max = bounds
        x_label, y_label = labels or ("X", "Y")
        self.bounds_label.setText(
            f"{x_label}: {x_min:.4g} to {x_max:.4g}\n{y_label}: {y_min:.4g} to {y_max:.4g}"
        )
        self.count_label.setText("")

    def _on_enable_toggled(self, enabled: bool) -> None:
        controller = self._roi()
        if controller is None:
            return
        controller.set_enabled(enabled)
        self._sync_from_controller()

    def _on_reset_clicked(self) -> None:
        controller = self._roi()
        if controller is None:
            return
        controller.reset()
        self._sync_from_controller()

    def _on_clear_clicked(self) -> None:
        controller = self._roi()
        if controller is None:
            return
        controller.clear()
        self._sync_from_controller()

    def _apply_operation(self, dataset):
        raise ValueError("ROI does not apply an operation.")
