"""Coordinate system selection widget for the right dock panel."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QDoubleSpinBox,
    QFormLayout,
)
from PyQt6.QtCore import pyqtSignal

from src.core.coordinate_system import CoordinateSystem


class CoordinateSystemWidget(QWidget):
    """Widget for selecting and configuring the coordinate system.

    Emits coordinate_system_changed when the user modifies any setting.
    """

    coordinate_system_changed = pyqtSignal(CoordinateSystem)

    _PRESET_LABELS = [
        ("ros", "ROS (Z-up)"),
        ("opencv", "OpenCV (Y-down)"),
        ("opengl", "OpenGL (Y-up)"),
    ]

    def __init__(self):
        super().__init__()
        self._suppress_signals = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Preset selector
        preset_layout = QFormLayout()
        self.preset_combo = QComboBox()
        for _, label in self._PRESET_LABELS:
            self.preset_combo.addItem(label)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addRow("Preset:", self.preset_combo)
        layout.addLayout(preset_layout)

        # Floor level
        floor_layout = QFormLayout()
        self.floor_spin = QDoubleSpinBox()
        self.floor_spin.setRange(-1000.0, 1000.0)
        self.floor_spin.setDecimals(3)
        self.floor_spin.setSingleStep(0.1)
        self.floor_spin.setSuffix(" m")
        self.floor_spin.setValue(0.0)
        self.floor_spin.valueChanged.connect(self._on_floor_changed)
        floor_layout.addRow("Floor Level:", self.floor_spin)
        layout.addLayout(floor_layout)

        layout.addStretch()

    def _on_preset_changed(self, index: int):
        if self._suppress_signals:
            return
        preset_key = self._PRESET_LABELS[index][0]
        cs = CoordinateSystem.from_preset(preset_key)
        cs.floor_level = self.floor_spin.value()
        self.coordinate_system_changed.emit(cs)

    def _on_floor_changed(self, value: float):
        if self._suppress_signals:
            return
        cs = self.current_coordinate_system()
        self.coordinate_system_changed.emit(cs)

    def current_coordinate_system(self) -> CoordinateSystem:
        """Return the currently configured CoordinateSystem."""
        preset_key = self._PRESET_LABELS[self.preset_combo.currentIndex()][0]
        cs = CoordinateSystem.from_preset(preset_key)
        cs.floor_level = self.floor_spin.value()
        return cs

    def set_coordinate_system(self, cs: CoordinateSystem):
        """Set the widget state to match a CoordinateSystem (e.g., from loaded project)."""
        self._suppress_signals = True

        matched_preset = cs.to_preset_name() or "ros"
        idx = next(i for i, (k, _) in enumerate(self._PRESET_LABELS) if k == matched_preset)
        self.preset_combo.setCurrentIndex(idx)
        self.floor_spin.setValue(cs.floor_level)

        self._suppress_signals = False
