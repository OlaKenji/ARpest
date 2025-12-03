"""UI widget for dataset rotation."""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ....models import Dataset
from ....operations.rotate import rotate_dataset
from ....utils.cursor.cursor_manager import CursorState
from .base import OperationWidget


class AnglePreviewWidget(QWidget):
    """Simple widget that displays a rotating line to preview the angle."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0.0
        self.setMinimumSize(80, 80)
        self.setMaximumHeight(120)

    def set_angle(self, angle: float) -> None:
        self._angle = float(angle)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(6, 6, -6, -6)
        center = QPointF(rect.center())
        radius = min(rect.width(), rect.height()) / 2.0

        guide_pen = QPen(self.palette().mid().color(), 1, Qt.DashLine)
        painter.setPen(guide_pen)
        painter.drawEllipse(center, radius, radius)
        painter.drawLine(rect.left(), center.y(), rect.right(), center.y())
        painter.drawLine(center.x(), rect.top(), center.x(), rect.bottom())

        angle_rad = np.deg2rad(self._angle)
        # Qt's y-axis points downwards; invert sine to keep CCW convention intuitive.
        dx = radius * np.cos(angle_rad)
        dy = -radius * np.sin(angle_rad)

        line_pen = QPen(self.palette().highlight().color(), 2)
        painter.setPen(line_pen)
        painter.drawLine(center, QPointF(center.x() + dx, center.y() + dy))


class RotateOperationWidget(OperationWidget):
    title = "Rotate dataset"
    category = "General"
    description = "Rotate the dataset around a chosen centre using bilinear interpolation."

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.dataset_info_label = QLabel("Select a dataset to configure rotation.")
        self.dataset_info_label.setWordWrap(True)
        layout.addWidget(self.dataset_info_label)

        params_group = QGroupBox("Rotation parameters")
        form = QFormLayout()
        form.setContentsMargins(4, 4, 4, 4)

        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-360.0, 360.0)
        self.angle_spin.setDecimals(2)
        self.angle_spin.setSingleStep(0.5)
        self.angle_spin.setSuffix(" °")
        self.angle_spin.setKeyboardTracking(False)
        self.angle_spin.valueChanged.connect(self._on_angle_changed)
        form.addRow("Rotation angle:", self.angle_spin)

        self.angle_preview = AnglePreviewWidget()
        layout.addWidget(self.angle_preview, alignment=Qt.AlignCenter)

        self._on_angle_changed(self.angle_spin.value())

        self.center_x_spin = QDoubleSpinBox()
        self.center_x_spin.setDecimals(6)
        self.center_x_spin.setRange(-1e6, 1e6)
        form.addRow("Centre X:", self.center_x_spin)

        self.center_y_spin = QDoubleSpinBox()
        self.center_y_spin.setDecimals(6)
        self.center_y_spin.setRange(-1e6, 1e6)
        form.addRow("Centre Y:", self.center_y_spin)

        params_group.setLayout(form)
        layout.addWidget(params_group)

        cursor_row = QHBoxLayout()
        self.cursor_btn = QPushButton("Use cursor position")
        self.cursor_btn.clicked.connect(self._on_cursor_clicked)
        cursor_row.addWidget(self.cursor_btn)
        cursor_row.addStretch()
        layout.addLayout(cursor_row)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.rotate_btn = QPushButton("Rotate")
        self.rotate_btn.clicked.connect(self._on_rotate_clicked)
        button_row.addWidget(self.rotate_btn)
        layout.addLayout(button_row)

        layout.addStretch()
        self.setLayout(layout)

        self._last_dataset_id: int | None = None
        self._init_from_dataset()

    def _init_from_dataset(self) -> None:
        stack = self.get_file_stack()
        if stack is None:
            self.dataset_info_label.setText("No dataset selected.")
            return
        self._update_dataset_summary(stack.current_state, sync_values=True)

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        if dataset is None:
            raise ValueError("No dataset available for rotation.")

        if self._last_dataset_id != id(dataset):
            self._update_dataset_summary(dataset, sync_values=False)

        angle = self._current_angle()
        center_x = self.center_x_spin.value()
        center_y = self.center_y_spin.value()
        rotated = rotate_dataset(dataset, angle_degrees=angle, center_x=center_x, center_y=center_y)
        return rotated, f"rotated_{angle:.2f}deg"

    def _on_cursor_clicked(self) -> None:
        stack = self.get_file_stack()
        if stack is None:
            QMessageBox.warning(self, "No dataset", "Select a dataset before using the cursor position.")
            return
        dataset = stack.current_state
        if self._last_dataset_id != id(dataset):
            self._update_dataset_summary(dataset, sync_values=False)

        cut_state: CursorState | None = self._get_context_value("cut_state")
        if cut_state is None:
            QMessageBox.information(
                self,
                "Cursor unavailable",
                "No cursor position is available. Drag the static red line in the plot to set it.",
            )
            return
        self.center_x_spin.setValue(float(cut_state.x_value))
        self.center_y_spin.setValue(float(cut_state.y_value))

    def _on_rotate_clicked(self) -> None:
        self._trigger_apply()

    def _update_dataset_summary(self, dataset: Dataset, sync_values: bool) -> None:
        x_vals = np.asarray(dataset.x_axis.values, dtype=float)
        y_vals = np.asarray(dataset.y_axis.values, dtype=float)
        if x_vals.size == 0 or y_vals.size == 0:
            self.dataset_info_label.setText("Dataset axes are empty; cannot determine bounds.")
            return

        x_min, x_max = float(np.nanmin(x_vals)), float(np.nanmax(x_vals))
        y_min, y_max = float(np.nanmin(y_vals)), float(np.nanmax(y_vals))
        self.dataset_info_label.setText(
            f"X range: [{x_min:.4g}, {x_max:.4g}] {dataset.x_axis.unit}\n"
            f"Y range: [{y_min:.4g}, {y_max:.4g}] {dataset.y_axis.unit}"
        )

        self.center_x_spin.blockSignals(True)
        self.center_y_spin.blockSignals(True)
        self.center_x_spin.setRange(min(x_min, x_max), max(x_min, x_max))
        self.center_y_spin.setRange(min(y_min, y_max), max(y_min, y_max))
        if sync_values or not np.isfinite(self.center_x_spin.value()):
            self.center_x_spin.setValue(float((x_min + x_max) / 2.0))
        if sync_values or not np.isfinite(self.center_y_spin.value()):
            self.center_y_spin.setValue(float((y_min + y_max) / 2.0))
        if sync_values:
            self._set_angle(0.0)
        self.center_x_spin.blockSignals(False)
        self.center_y_spin.blockSignals(False)
        self._last_dataset_id = id(dataset)

    def _current_angle(self) -> float:
        return float(self.angle_spin.value())

    def _set_angle(self, degrees: float) -> None:
        limited = np.clip(float(degrees), -360.0, 360.0)
        self.angle_spin.blockSignals(True)
        self.angle_spin.setValue(limited)
        self.angle_spin.blockSignals(False)
        self._on_angle_changed(limited)

    def _on_angle_changed(self, value: float) -> None:
        self.angle_preview.set_angle(float(value))
