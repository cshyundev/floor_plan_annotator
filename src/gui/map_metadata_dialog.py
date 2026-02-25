"""Dialog for manual input of ROS2 occupancy grid metadata."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox,
    QSpinBox, QDialogButtonBox, QLabel,
)

from src.model.data import MapMetadata


class MapMetadataDialog(QDialog):
    """Dialog for manually entering occupancy grid metadata.

    Used as a fallback when no .yaml metadata file is found
    alongside the occupancy grid image.
    """

    def __init__(self, parent=None, metadata: MapMetadata | None = None):
        super().__init__(parent)
        self.setWindowTitle("Map Metadata")
        self.setMinimumWidth(350)

        self._metadata = metadata or MapMetadata()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Enter the occupancy grid metadata.\n"
            "These values are typically found in the map .yaml file."
        ))

        form = QFormLayout()

        self.resolution_spin = QDoubleSpinBox()
        self.resolution_spin.setRange(0.001, 10.0)
        self.resolution_spin.setDecimals(4)
        self.resolution_spin.setSingleStep(0.01)
        self.resolution_spin.setSuffix(" m/px")
        self.resolution_spin.setValue(self._metadata.resolution)
        form.addRow("Resolution:", self.resolution_spin)

        self.origin_x_spin = QDoubleSpinBox()
        self.origin_x_spin.setRange(-10000.0, 10000.0)
        self.origin_x_spin.setDecimals(3)
        self.origin_x_spin.setSuffix(" m")
        self.origin_x_spin.setValue(self._metadata.origin_x)
        form.addRow("Origin X:", self.origin_x_spin)

        self.origin_y_spin = QDoubleSpinBox()
        self.origin_y_spin.setRange(-10000.0, 10000.0)
        self.origin_y_spin.setDecimals(3)
        self.origin_y_spin.setSuffix(" m")
        self.origin_y_spin.setValue(self._metadata.origin_y)
        form.addRow("Origin Y:", self.origin_y_spin)

        self.negate_spin = QSpinBox()
        self.negate_spin.setRange(0, 1)
        self.negate_spin.setValue(self._metadata.negate)
        form.addRow("Negate:", self.negate_spin)

        self.occupied_thresh_spin = QDoubleSpinBox()
        self.occupied_thresh_spin.setRange(0.0, 1.0)
        self.occupied_thresh_spin.setDecimals(3)
        self.occupied_thresh_spin.setSingleStep(0.05)
        self.occupied_thresh_spin.setValue(self._metadata.occupied_thresh)
        form.addRow("Occupied Threshold:", self.occupied_thresh_spin)

        self.free_thresh_spin = QDoubleSpinBox()
        self.free_thresh_spin.setRange(0.0, 1.0)
        self.free_thresh_spin.setDecimals(3)
        self.free_thresh_spin.setSingleStep(0.05)
        self.free_thresh_spin.setValue(self._metadata.free_thresh)
        form.addRow("Free Threshold:", self.free_thresh_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_metadata(self) -> MapMetadata:
        """Return the metadata from the dialog fields."""
        self._metadata.resolution = self.resolution_spin.value()
        self._metadata.origin_x = self.origin_x_spin.value()
        self._metadata.origin_y = self.origin_y_spin.value()
        self._metadata.negate = self.negate_spin.value()
        self._metadata.occupied_thresh = self.occupied_thresh_spin.value()
        self._metadata.free_thresh = self.free_thresh_spin.value()
        return self._metadata
