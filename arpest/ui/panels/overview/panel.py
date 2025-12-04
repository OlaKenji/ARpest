"""Overview panel with file catalog and visualization controls."""

from __future__ import annotations

from typing import Callable, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from ....models import FileStack
from .widgets.file_catalog import FileCatalogWidget


class OverviewPanel(QWidget):
    """Right-side overview tab with catalog, metadata, and display controls."""

    def __init__(
        self,
        *,
        file_stacks: List[FileStack],
        on_load_clicked: Callable[[], None],
        on_remove_clicked: Callable[[], None],
        on_combine_clicked: Callable[[], None],
        on_file_selected: Callable[[int], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.file_catalog = FileCatalogWidget(file_stacks)
        self.file_catalog.file_selected.connect(on_file_selected)

        self.meta_text = QLabel()
        self.meta_text.setWordWrap(True)
        self.data_text = QLabel()
        self.data_text.setWordWrap(True)

        self.colormap_combo = QComboBox()
        self.color_scale_slider = QSlider(Qt.Horizontal)
        self.vmin_input = QLineEdit()
        self.vmax_input = QLineEdit()
        self.integration_slider = QSlider(Qt.Horizontal)
        self.integration_value_label = QLabel()

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Button row
        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        load_button = QPushButton("Load Data")
        load_button.setToolTip("Load additional data into this catalog")
        load_button.clicked.connect(on_load_clicked)
        button_row.addWidget(load_button)

        remove_button = QPushButton("Remove Data")
        remove_button.setToolTip("Remove selected datasets from the catalog")
        remove_button.clicked.connect(on_remove_clicked)
        button_row.addWidget(remove_button)

        combine_button = QPushButton("Combine Data")
        combine_button.setToolTip("Average selected datasets (needs ≥ 2 selections)")
        combine_button.clicked.connect(on_combine_clicked)
        button_row.addWidget(combine_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        layout.addWidget(self._label("Loaded Files:"))
        self.file_catalog.setMaximumHeight(200)
        self.file_catalog.setMinimumWidth(250)
        layout.addWidget(self.file_catalog)

        layout.addWidget(self._label("Metadata:", top_margin=True))
        self.meta_text.setStyleSheet("font-size: 10px; padding: 5px; background: #f9f9f9;")
        layout.addWidget(self.meta_text)

        layout.addWidget(self._label("Data Info:", top_margin=True))
        self.data_text.setStyleSheet("font-size: 10px; padding: 5px; background: #f9f9f9;")
        layout.addWidget(self.data_text)

        layout.addWidget(self._label("Colour Map:", top_margin=True))
        layout.addWidget(self.colormap_combo)

        layout.addWidget(self._label("Colour Scale:", top_margin=True))
        slider_row = QHBoxLayout()
        slider_row.setSpacing(6)
        self.color_scale_slider.setRange(1, 100)
        slider_row.addWidget(self.color_scale_slider)
        layout.addLayout(slider_row)

        manual_row = QHBoxLayout()
        self.vmin_input.setPlaceholderText("vmin")
        self.vmin_input.setFixedWidth(80)
        manual_row.addWidget(QLabel("Min:"))
        manual_row.addWidget(self.vmin_input)

        self.vmax_input.setPlaceholderText("vmax")
        self.vmax_input.setFixedWidth(80)
        manual_row.addWidget(QLabel("Max:"))
        manual_row.addWidget(self.vmax_input)
        manual_row.addStretch()
        layout.addLayout(manual_row)

        layout.addWidget(self._label("Integration Range:", top_margin=True))
        integration_row = QHBoxLayout()
        self.integration_slider.setRange(1, 15)
        integration_row.addWidget(self.integration_slider)
        integration_row.addWidget(self.integration_value_label)
        integration_row.addStretch()
        layout.addLayout(integration_row)

        layout.addStretch()

    def _label(self, text: str, *, top_margin: bool = False) -> QLabel:
        label = QLabel(text)
        style = "font-weight: bold; font-size: 12px;"
        if top_margin:
            style += " margin-top: 10px;"
        label.setStyleSheet(style)
        return label

    def refresh_catalog(self) -> None:
        self.file_catalog.refresh()

    def select_index(self, index: int) -> None:
        self.file_catalog.select_index(index)

    def update_metadata(self, meta_text: str, data_text: str) -> None:
        self.meta_text.setText(meta_text)
        self.data_text.setText(data_text)
