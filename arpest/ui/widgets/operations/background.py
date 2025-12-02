"""UI widget for subtracting EDC/MDC background curves."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .base import OperationWidget
from ....models import Dataset
from ....operations.background import subtract_background


class BackgroundOperationWidget(OperationWidget):
    title = "Background operations"
    category = "Background"
    description = "Subtract EDC/MDC curves or their minimum-based baselines."

    _modes = ["EDC", "MDC", "EDC_min", "MDC_min"]

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(6)

        desc = QLabel(
            "Cycle the background mode between EDC/MDC (average curves) or EDC/MDC min baselines, "
            "then press subtract to remove it from the dataset. For 3D data each scan is handled independently."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self._mode_index = 0
        self.mode_button = QPushButton(self._mode_label())
        self.mode_button.clicked.connect(self._cycle_mode)
        layout.addWidget(self.mode_button)

        min_row = QHBoxLayout()
        min_row.addWidget(QLabel("Min points:"))
        self.min_points_spin = QSpinBox()
        self.min_points_spin.setRange(1, 500)
        self.min_points_spin.setSingleStep(1)
        self.min_points_spin.setValue(5)
        self.min_points_spin.setFixedWidth(70)
        min_row.addWidget(self.min_points_spin)
        min_row.addStretch()
        layout.addLayout(min_row)
        self._update_min_points_enabled()

        subtract_btn = QPushButton("Subtract")
        subtract_btn.clicked.connect(self._trigger_apply)
        layout.addWidget(subtract_btn)

        layout.addStretch()
        self.setLayout(layout)
        self.setMaximumWidth(360)

    def _mode_label(self) -> str:
        return f"Mode: {self._modes[self._mode_index]}"

    def _current_mode(self) -> str:
        return self._modes[self._mode_index]

    def _cycle_mode(self) -> None:
        self._mode_index = (self._mode_index + 1) % len(self._modes)
        self.mode_button.setText(self._mode_label())
        self._update_min_points_enabled()

    def _update_min_points_enabled(self) -> None:
        use_min = "min" in self._current_mode().lower()
        self.min_points_spin.setEnabled(use_min)

    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        mode = self._current_mode()
        min_points = int(self.min_points_spin.value())
        edc_curves = self._get_context_value("current_edc_curves")
        mdc_curves = self._get_context_value("current_mdc_curves")
        result = subtract_background(
            dataset,
            mode,
            min_points=min_points,
            edc_curves=edc_curves,
            mdc_curves=mdc_curves,
        )
        label = f"background {mode.lower()}"
        return result, label
