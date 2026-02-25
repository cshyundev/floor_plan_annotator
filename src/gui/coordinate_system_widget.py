"""Coordinate system selection widget for the right dock panel."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QDoubleSpinBox,
    QLabel, QFormLayout, QCheckBox, QGroupBox,
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
        ("custom", "Custom..."),
    ]

    _AXIS_LABELS = ["X (0)", "Y (1)", "Z (2)"]

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

        # Custom settings group (hidden by default)
        self.custom_group = QGroupBox("Custom Axes")
        custom_layout = QFormLayout(self.custom_group)

        self.up_axis_combo = QComboBox()
        for label in self._AXIS_LABELS:
            self.up_axis_combo.addItem(label)
        self.up_axis_combo.setCurrentIndex(2)  # Z default
        custom_layout.addRow("Up Axis:", self.up_axis_combo)

        self.up_dir_combo = QComboBox()
        self.up_dir_combo.addItems(["+1 (positive up)", "-1 (negative up)"])
        custom_layout.addRow("Up Direction:", self.up_dir_combo)

        self.floor_h_combo = QComboBox()
        for label in self._AXIS_LABELS:
            self.floor_h_combo.addItem(label)
        self.floor_h_combo.setCurrentIndex(0)  # X default
        custom_layout.addRow("Floor H Axis:", self.floor_h_combo)

        self.floor_v_combo = QComboBox()
        for label in self._AXIS_LABELS:
            self.floor_v_combo.addItem(label)
        self.floor_v_combo.setCurrentIndex(1)  # Y default
        custom_layout.addRow("Floor V Axis:", self.floor_v_combo)

        self.flip_v_check = QCheckBox("Flip V axis in projection")
        self.flip_v_check.setChecked(True)
        custom_layout.addRow(self.flip_v_check)

        self.custom_group.setVisible(False)
        layout.addWidget(self.custom_group)

        # Connect custom controls
        for ctrl in (self.up_axis_combo, self.up_dir_combo,
                     self.floor_h_combo, self.floor_v_combo):
            ctrl.currentIndexChanged.connect(self._on_custom_changed)
        self.flip_v_check.toggled.connect(self._on_custom_changed)

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
        is_custom = (preset_key == "custom")
        self.custom_group.setVisible(is_custom)

        if not is_custom:
            cs = CoordinateSystem.from_preset(preset_key)
            cs.floor_level = self.floor_spin.value()
            self._update_custom_controls(cs)
            self.coordinate_system_changed.emit(cs)

    def _on_custom_changed(self, _=None):
        if self._suppress_signals:
            return
        cs = self._build_from_controls()
        self.coordinate_system_changed.emit(cs)

    def _on_floor_changed(self, value: float):
        if self._suppress_signals:
            return
        cs = self.current_coordinate_system()
        self.coordinate_system_changed.emit(cs)

    def _build_from_controls(self) -> CoordinateSystem:
        up_axis = self.up_axis_combo.currentIndex()
        up_dir = 1 if self.up_dir_combo.currentIndex() == 0 else -1
        fh = self.floor_h_combo.currentIndex()
        fv = self.floor_v_combo.currentIndex()
        return CoordinateSystem(
            up_axis=up_axis,
            up_direction=up_dir,
            floor_axes=(fh, fv),
            floor_level=self.floor_spin.value(),
            flip_floor_v=self.flip_v_check.isChecked(),
        )

    def _update_custom_controls(self, cs: CoordinateSystem):
        """Sync custom control values to match a CoordinateSystem (no signals)."""
        self._suppress_signals = True
        self.up_axis_combo.setCurrentIndex(cs.up_axis)
        self.up_dir_combo.setCurrentIndex(0 if cs.up_direction == 1 else 1)
        self.floor_h_combo.setCurrentIndex(cs.floor_axes[0])
        self.floor_v_combo.setCurrentIndex(cs.floor_axes[1])
        self.flip_v_check.setChecked(cs.flip_floor_v)
        self._suppress_signals = False

    def current_coordinate_system(self) -> CoordinateSystem:
        """Return the currently configured CoordinateSystem."""
        preset_key = self._PRESET_LABELS[self.preset_combo.currentIndex()][0]
        if preset_key == "custom":
            return self._build_from_controls()
        cs = CoordinateSystem.from_preset(preset_key)
        cs.floor_level = self.floor_spin.value()
        return cs

    def set_coordinate_system(self, cs: CoordinateSystem):
        """Set the widget state to match a CoordinateSystem (e.g., from loaded project)."""
        self._suppress_signals = True

        # Try to find matching preset
        matched_preset = None
        for key in ("ros", "opencv", "opengl"):
            preset = CoordinateSystem.from_preset(key)
            if (cs.up_axis == preset.up_axis
                    and cs.up_direction == preset.up_direction
                    and cs.floor_axes == preset.floor_axes
                    and cs.flip_floor_v == preset.flip_floor_v):
                matched_preset = key
                break

        if matched_preset:
            idx = next(i for i, (k, _) in enumerate(self._PRESET_LABELS) if k == matched_preset)
            self.preset_combo.setCurrentIndex(idx)
            self.custom_group.setVisible(False)
        else:
            idx = next(i for i, (k, _) in enumerate(self._PRESET_LABELS) if k == "custom")
            self.preset_combo.setCurrentIndex(idx)
            self.custom_group.setVisible(True)

        self._update_custom_controls(cs)
        self.floor_spin.setValue(cs.floor_level)
        self._suppress_signals = False
