"""Fermi level correction operation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QHBoxLayout,
    QFileDialog,
    QComboBox,
    QWidget,
)

from ..core.loaders import BaseLoader
from ..models import Axis, AxisType, Dataset
from .base import OperationWidget
from ..utils.functions.fermi_dirac_ditribution import fit_fermi_dirac

class FermiLevelCorrectionWidget(OperationWidget):
    """Align the dataset Fermi level using a gold reference measurement."""

    title = "Fermi Level Correction"
    category = "Alignment"
    description = (
        "Load a gold reference, fit the Fermi edge for each EDC, and shift the current dataset accordingly."
    )

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(8)

        desc = QLabel("Correct the Fermi level by fitting the Fermi level of a reference.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        reference_group = QGroupBox('')
        reference_layout = QVBoxLayout()
        self.reference_path_label = QLabel("No reference file loaded.")
        self.reference_path_label.setWordWrap(True)
        reference_layout.addWidget(self.reference_path_label)

        controls_row = QHBoxLayout()
        load_btn = QPushButton("Gold please?")
        load_btn.clicked.connect(self._on_load_reference_clicked)
        controls_row.addWidget(load_btn)
        controls_row.addStretch()
        reference_layout.addLayout(controls_row)

        self.reference_meta_label = QLabel("")
        self.reference_meta_label.setWordWrap(True)
        reference_layout.addWidget(self.reference_meta_label)

        reference_group.setLayout(reference_layout)
        layout.addWidget(reference_group)

        mode_layout = QVBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Global shift (single offset)", "global")
        mode_layout.addWidget(self.mode_combo)

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

    # ------------------------------------------------------------------ Helpers
    def _on_load_reference_clicked(self) -> None:
        """Load a gold reference file using available loaders."""
        loaders = self._available_loaders()
        if not loaders:
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

        filter_entries.insert(0, f"All supported ({' '.join(f'*{ext}' for ext in set(all_exts))})")
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
        for loader in loaders:
            try:
                if loader.can_load(path):
                    return loader.load(path)
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError(f"Failed to load {path.name} with {loader.name}: {exc}") from exc
        raise ValueError(f"No loader available for {path.name}")

    # ------------------------------------------------------------------ Operation logic
    def _apply_operation(self, dataset: Dataset) -> tuple[Dataset, str]:
        if self._reference_dataset is None:
            raise ValueError("Load a gold reference before running the correction.")

        if dataset.is_2d:
            return self._apply_2d(dataset)
        elif dataset.is_3d:
            return self._apply_3d(dataset)

    def _apply_3d(self, dataset: Dataset) -> tuple[Dataset, str]:
        if self._reference_dataset.is_2d:
            'apply the same EF correction for all scan angles'
            pass
        elif self._reference_dataset.is_2d:
            'fit fermi level for each scan angle, and correct for it'
            pass

    def _apply_2d(self, dataset: Dataset) -> tuple[Dataset, str]:
        if not self._reference_dataset.is_2d:
            raise ValueError("The uploaded Gold is not 2D?")

        gold = self._reference_dataset.intensity
        n_pixels, n_energies = gold.shape
        energies = self._reference_dataset.x_axis.values
        dataset_intensity = dataset.intensity

        if dataset_intensity.shape[0] != n_pixels:
            raise ValueError("Reference and dataset must have the same number of EDC pixels.")

        new_dataset = dataset.copy()

        W = 4.38#work function [eV]
        hv = new_dataset.measurement.photon_energy
        e_0 = hv - W#initial guess of fermi level
        temperature = new_dataset.measurement.temperature

        params = []
        functions = []
        for i,edc in enumerate(gold):
            lenght = int(len(edc)*0.75)
            p, res_func = fit_fermi_dirac(energies[lenght:-1], edc[lenght:-1], e_0, T = temperature)
            params.append(p)
            e_0 = p[0]#update teh guess
            functions.append(res_func)

        # Prepare the results
        params = np.array(params)
        fermi_levels = params[:,0]#np.clip(params[:,0],90.37,90.45)
        sigmas = params[:,1]
        slopes = params[:,2]
        offsets = params[:,3]
        
        corrected_intensity, corrected_axis = self._apply_edc_shifts(dataset_intensity,new_dataset.x_axis.values,fermi_levels)

        new_dataset.intensity = corrected_intensity
        new_dataset.x_axis.values = corrected_axis
        new_dataset.validate()

        return new_dataset, "Fermi level corrected"              
    
    def _apply_edc_shifts(
        self,
        intensity: np.ndarray,
        energies: np.ndarray,
        fermi_levels: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Shift each EDC independently and resample onto a common axis."""
        if intensity.shape[0] != len(fermi_levels):
            raise ValueError("Number of fermi entries does not match dataset rows.")

        energies = np.asarray(energies, dtype=float)
        if energies.ndim != 1 or energies.size < 2:
            raise ValueError("Energy axis must contain at least two points.")

        spacing = np.diff(energies)
        valid_spacing = np.abs(spacing[spacing != 0])
        step = float(np.median(valid_spacing)) if valid_spacing.size else 1.0

        shifted_min = float(energies.min() - np.max(fermi_levels))
        shifted_max = float(energies.max() - np.min(fermi_levels))
        if shifted_max <= shifted_min:
            shifted_max = shifted_min + step

        num_points = int(np.ceil((shifted_max - shifted_min) / step)) + 1
        target_axis = shifted_min + np.arange(num_points) * step

        corrected = np.full((intensity.shape[0], num_points), np.nan, dtype=float)
        ascending = energies[0] < energies[-1]

        for idx, (curve, ef) in enumerate(zip(intensity, fermi_levels)):
            xp = energies - ef
            yp = curve
            if not ascending:
                xp = xp[::-1]
                yp = yp[::-1]
            corrected[idx] = np.interp(
                target_axis,
                xp,
                yp,
                left=np.nan,
                right=np.nan,
            )

        return corrected, target_axis
