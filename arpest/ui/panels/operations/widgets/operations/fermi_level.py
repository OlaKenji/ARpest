"""UI widget for Fermi level correction."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt5.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ......core.loaders import BaseLoader
from ......models import Dataset
from ......operations.fermi import (
    DEFAULT_WORK_FUNCTION,
    correct_fermi_level_2d,
    correct_fermi_level_3d_same,
    correct_fermi_level_3d,
)
from ......utils.session import SESSION_FILE_EXTENSION, load_session
from .base import OperationWidget

class FermiLevelCorrectionWidget(OperationWidget):
    """Align the dataset Fermi level using a gold reference measurement."""

    title = "Fermi Level Correction"
    category = "Operate"
    description = (
        "Load a gold reference, fit the Fermi edge for each EDC, and shift the current dataset accordingly."
    )

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        desc = QLabel("Correct the Fermi level by fitting the Fermi level of a reference.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        reference_group = QGroupBox("Reference measurement")
        reference_layout = QVBoxLayout()
        self.reference_path_label = QLabel("No reference file loaded.")
        self.reference_path_label.setWordWrap(True)
        reference_layout.addWidget(self.reference_path_label)

        controls_row = QHBoxLayout()
        load_btn = QPushButton("Select gold reference…")
        load_btn.clicked.connect(self._on_load_reference_clicked)
        controls_row.addWidget(load_btn)
        controls_row.addStretch()
        reference_layout.addLayout(controls_row)

        self.reference_meta_label = QLabel("")
        self.reference_meta_label.setWordWrap(True)
        reference_layout.addWidget(self.reference_meta_label)

        reference_group.setLayout(reference_layout)
        layout.addWidget(reference_group)

        fit_group = QGroupBox("Fitting options")
        fit_layout = QVBoxLayout()

        stride_row = QHBoxLayout()
        stride_row.addWidget(QLabel("Average every"))
        self._fit_stride_spin = QSpinBox()
        self._fit_stride_spin.setRange(1, 10000)
        self._fit_stride_spin.setValue(1)
        self._fit_stride_spin.setToolTip("Number of neighboring EDCs to average for each Fermi fit.")
        stride_row.addWidget(self._fit_stride_spin)
        stride_row.addWidget(QLabel("EDCs"))
        stride_row.addStretch()
        fit_layout.addLayout(stride_row)

        order_row = QHBoxLayout()
        order_row.addWidget(QLabel("Polynomial order"))
        self._poly_order_spin = QSpinBox()
        self._poly_order_spin.setRange(0, 6)
        self._poly_order_spin.setValue(3)
        self._poly_order_spin.setToolTip("Degree for interpolating EF between fitted EDCs.")
        order_row.addWidget(self._poly_order_spin)
        order_row.addStretch()
        fit_layout.addLayout(order_row)

        guess_row = QHBoxLayout()
        self._fermi_guess_label = QLabel()
        self._fermi_guess_label.setWordWrap(True)
        guess_row.addWidget(self._fermi_guess_label, stretch=1)
        set_guess_btn = QPushButton("Set Fermi level…")
        set_guess_btn.clicked.connect(self._on_set_fermi_guess_clicked)
        guess_row.addWidget(set_guess_btn)
        reset_guess_btn = QPushButton("Reset")
        reset_guess_btn.clicked.connect(self._on_reset_fermi_guess_clicked)
        guess_row.addWidget(reset_guess_btn)
        fit_layout.addLayout(guess_row)

        fit_group.setLayout(fit_layout)
        layout.addWidget(fit_group)

        self.compat_label = QLabel("")
        self.compat_label.setWordWrap(True)
        layout.addWidget(self.compat_label)

        apply_btn = QPushButton("Apply Fermi correction")
        apply_btn.clicked.connect(self._trigger_apply)
        layout.addWidget(apply_btn)

        layout.addStretch()
        self.setLayout(layout)

        self._reference_dataset: Dataset | None = None
        self._reference_path: Path | None = None
        self._last_reference_dir: Path | None = None
        self._initial_fermi_guess: float | None = None
        self._update_fermi_guess_label()

    # ------------------------------------------------------------------ Helpers
    def _on_load_reference_clicked(self) -> None:
        """Load a gold reference file using available loaders."""
        loaders = self._available_loaders()
        if not loaders:
            self.reference_meta_label.setText("No loaders available.")
            return

        start_dir = self._start_path()
        if self._last_reference_dir is not None:
            start_dir = str(self._last_reference_dir)

        filter_entries = []
        all_exts: list[str] = []
        for loader in loaders:
            exts = " ".join(f"*{ext}" for ext in loader.extensions)
            filter_entries.append(f"{loader.name} ({exts})")
            all_exts.extend(loader.extensions)

        all_exts.append(SESSION_FILE_EXTENSION)
        filter_entries.insert(0, f"All supported ({' '.join(f'*{ext}' for ext in set(all_exts))})")
        filter_entries.insert(1, f"Saved datasets (*{SESSION_FILE_EXTENSION})")
        filter_entries.append("All files (*.*)")
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select gold reference",
            start_dir,
            ";;".join(filter_entries),
        )
        if not filename:
            return

        path = Path(filename)
        try:
            dataset = self._load_reference_dataset(path, loaders)
        except ValueError as exc:
            self.reference_meta_label.setText(str(exc))
            return

        self._reference_dataset = dataset
        self._reference_path = path
        self._last_reference_dir = path.parent
        self.reference_path_label.setText(f"Reference: {path.name}")
        self.reference_meta_label.setText(
            f"{dataset.ndim}D dataset with {dataset.shape} grid"
        )

    def _available_loaders(self) -> list[BaseLoader]:
        loaders = self._get_context_value("available_loaders")
        if isinstance(loaders, list):
            return loaders
        return []

    def _start_path(self) -> str:
        path = self._get_context_value("start_path")
        if isinstance(path, (str, Path)):
            return str(path)
        return str(Path.home())

    def _load_reference_dataset(self, path: Path, loaders: Iterable[BaseLoader]) -> Dataset:
        if path.suffix == SESSION_FILE_EXTENSION:
            return self._load_session_reference(path)

        for loader in loaders:
            try:
                if loader.can_load(path):
                    return loader.load(path)
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError(f"Failed to load {path.name} with {loader.name}: {exc}") from exc
        raise ValueError(f"No loader available for {path.name}")

    def _load_session_reference(self, path: Path) -> Dataset:
        """Return the active dataset stored inside a saved session file."""
        try:
            session = load_session(path)
        except Exception as exc:
            raise ValueError(f"Could not read {path.name}: {exc}") from exc

        if not session.tabs:
            raise ValueError("Session does not contain any datasets.")

        tab_state = session.tabs[0]
        if not tab_state.file_stacks:
            raise ValueError("Session does not contain any file stacks.")

        stack_index = max(0, min(tab_state.current_index, len(tab_state.file_stacks) - 1))
        file_stack = tab_state.file_stacks[stack_index]
        if not file_stack.states:
            dataset = file_stack.raw_data
        else:
            state_index = max(0, min(file_stack.current_index, len(file_stack.states) - 1))
            dataset = file_stack.states[state_index]

        return dataset

    # ------------------------------------------------------------------ Operation logic
    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        if self._reference_dataset is None:
            raise ValueError("Load a gold reference before running the correction.")

        options = {
            "initial_fermi_guess": self._initial_fermi_guess,
            "fit_stride": self._fit_stride_spin.value(),
            "poly_order": self._poly_order_spin.value(),
        }

        if dataset.is_2d:
            if not self._reference_dataset.is_2d:
                raise ValueError("Fermi correction currently supports 2D datasets only.")
            corrected_dataset, _ = correct_fermi_level_2d(
                dataset,
                self._reference_dataset,
                **options,
            )
            return corrected_dataset, "Fermi level corrected"
        elif dataset.is_3d:
            if self._reference_dataset.is_2d:
                'apply the same EF correction for all scan angles'
                corrected_dataset, _ = correct_fermi_level_3d_same(
                    dataset,
                    self._reference_dataset,
                    **options,
                )
                return corrected_dataset, "Fermi level corrected"
            elif self._reference_dataset.is_3d:
                'fit each scan angle and correct'
                corrected_dataset, _ = correct_fermi_level_3d(dataset, self._reference_dataset)
                return corrected_dataset, "Fermi level corrected"
        raise ValueError("Unsupported dataset dimensionality for Fermi correction.")

    # ------------------------------------------------------------------ EF guess helpers
    def _on_set_fermi_guess_clicked(self) -> None:
        """Prompt user for a manual initial EF guess."""
        default_guess = self._initial_fermi_guess
        if default_guess is None:
            default_guess = self._suggest_fermi_guess()

        value, ok = QInputDialog.getDouble(
            self,
            "Set Fermi level",
            "Initial Fermi level guess (eV):",
            value=default_guess,
            decimals=3,
        )
        if ok:
            self._initial_fermi_guess = value
            self._update_fermi_guess_label()

    def _on_reset_fermi_guess_clicked(self) -> None:
        """Clear manual EF override."""
        self._initial_fermi_guess = None
        self._update_fermi_guess_label()

    def _suggest_fermi_guess(self) -> float:
        """Estimate a reasonable EF starting point for the prompt."""
        file_stack = self.get_file_stack()
        dataset = file_stack.current_state if file_stack is not None else None
        photon_energy = getattr(getattr(dataset, "measurement", None), "photon_energy", None)
        if photon_energy is not None:
            return float(photon_energy - DEFAULT_WORK_FUNCTION)
        return 0.0

    def _update_fermi_guess_label(self) -> None:
        """Update the label summarizing the active initial EF guess."""
        if self._initial_fermi_guess is None:
            self._fermi_guess_label.setText(
                "Initial EF guess: Auto (uses photon energy minus work function when available)."
            )
        else:
            self._fermi_guess_label.setText(f"Initial EF guess: {self._initial_fermi_guess:.3f} eV")
