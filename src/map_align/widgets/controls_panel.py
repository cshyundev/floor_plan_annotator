"""Controls panel for map alignment parameters."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QDoubleSpinBox, QCheckBox, QFrame,
)
from PyQt6.QtCore import pyqtSignal

from src.core.config import ConfigManager


class ControlsPanel(QWidget):
    """Parameter controls for alignment tool.

    Signals:
        transform_changed: A transform spinbox value changed.
    """

    transform_changed = pyqtSignal()
    color_mode_changed = pyqtSignal(bool)  # True = legend colors

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigManager.instance()
        self.setFixedWidth(self._config.get_ui_value("map_align", "ui", "panel_width"))
        self._updating = False  # guard against signal loops
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ─── Transform (6DOF) ───
        tf_group = QGroupBox("Transform")
        tf_layout = QVBoxLayout(tf_group)

        t_step = self._config.get_ui_value("map_align", "step_sizes", "translate_default")
        r_step = self._config.get_ui_value("map_align", "step_sizes", "rotate_default")

        self.spin_tx = self._make_translation_spin("TX:", tf_layout, t_step)
        self.spin_ty = self._make_translation_spin("TY:", tf_layout, t_step)
        self.spin_tz = self._make_translation_spin("TZ:", tf_layout, t_step)
        self.spin_roll = self._make_rotation_spin("Roll:", tf_layout, r_step)
        self.spin_pitch = self._make_rotation_spin("Pitch:", tf_layout, r_step)
        self.spin_yaw = self._make_rotation_spin("Yaw:", tf_layout, r_step)

        layout.addWidget(tf_group)

        # ─── Display (legend + color toggle) ───
        display_group = QGroupBox("Display")
        display_layout = QVBoxLayout(display_group)

        ref_color = self._config.get_color("map_align", "reference")
        src_color = self._config.get_color("map_align", "source")

        for color, label_text in [(ref_color, "Reference"), (src_color, "Source")]:
            row = QHBoxLayout()
            swatch = QFrame()
            swatch.setFixedSize(16, 16)
            swatch.setStyleSheet(
                f"background-color: rgb({color.red()},{color.green()},{color.blue()});"
                " border: 1px solid #555;"
            )
            row.addWidget(swatch)
            row.addWidget(QLabel(label_text))
            row.addStretch()
            display_layout.addLayout(row)

        self._chk_legend = QCheckBox("Legend Colors")
        self._chk_legend.setChecked(True)
        self._chk_legend.toggled.connect(self.color_mode_changed.emit)
        display_layout.addWidget(self._chk_legend)

        layout.addWidget(display_group)

        # ─── Keyboard shortcuts reference ───
        help_group = QGroupBox("Shortcuts")
        help_layout = QVBoxLayout(help_group)
        shortcuts = [
            (["LMB drag"], "Orbit camera"),
            (["MMB drag"], "Pan camera"),
            (["Scroll"], "Zoom"),
            (["Shift", "Scroll"], "Yaw"),
            (["Ctrl", "Scroll"], "TZ"),
            (["Arrows"], "TX / TY"),
            (["PgUp", "PgDn"], "TZ"),
            (["[", "]"], "Yaw"),
            (["Shift", "[", "]"], "Roll"),
            (["Ctrl", "[", "]"], "Pitch"),
            (["R"], "Auto Align"),
            (["F"], "Fit view"),
        ]
        for keys, desc in shortcuts:
            help_layout.addLayout(self._make_shortcut_row(keys, desc))

        layout.addWidget(help_group)
        layout.addStretch()

    # ─── Helpers ───

    def _make_translation_spin(self, label_text: str, parent_layout: QVBoxLayout, step: float) -> QDoubleSpinBox:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setFixedWidth(40)
        row.addWidget(label)
        spin = QDoubleSpinBox()
        spin.setRange(-100.0, 100.0)
        spin.setValue(0.0)
        spin.setSuffix(" m")
        spin.setDecimals(3)
        spin.setSingleStep(step)
        spin.valueChanged.connect(self._on_transform_spin_changed)
        row.addWidget(spin)
        parent_layout.addLayout(row)
        return spin

    def _make_rotation_spin(self, label_text: str, parent_layout: QVBoxLayout, step: float) -> QDoubleSpinBox:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setFixedWidth(40)
        row.addWidget(label)
        spin = QDoubleSpinBox()
        spin.setRange(-180.0, 180.0)
        spin.setValue(0.0)
        spin.setSuffix("°")
        spin.setDecimals(1)
        spin.setSingleStep(step)
        spin.valueChanged.connect(self._on_transform_spin_changed)
        row.addWidget(spin)
        parent_layout.addLayout(row)
        return spin

    @staticmethod
    def _make_key_label(text: str) -> QLabel:
        """Create a keyboard-key styled label."""
        label = QLabel(text)
        label.setStyleSheet(
            "background-color: #e8e8e8; color: #333; border: 1px solid #aaa;"
            " border-radius: 3px; padding: 1px 5px;"
            " font-family: monospace; font-size: 11px;"
        )
        return label

    @staticmethod
    def _make_shortcut_row(keys: list[str], description: str) -> QHBoxLayout:
        """Create a row with key labels and a description."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 1, 0, 1)
        for i, k in enumerate(keys):
            if i > 0:
                plus = QLabel(" ")
                plus.setFixedWidth(4)
                row.addWidget(plus)
            row.addWidget(ControlsPanel._make_key_label(k))
        desc_label = QLabel(description)
        desc_label.setStyleSheet("padding-left: 6px; font-size: 11px;")
        row.addWidget(desc_label)
        row.addStretch()
        return row

    def _on_transform_spin_changed(self):
        if not self._updating:
            self.transform_changed.emit()

    # ─── Public API ───

    def get_transform_values(self) -> dict[str, float]:
        """Return current transform values from spinboxes."""
        return {
            "tx": self.spin_tx.value(),
            "ty": self.spin_ty.value(),
            "tz": self.spin_tz.value(),
            "roll_deg": self.spin_roll.value(),
            "pitch_deg": self.spin_pitch.value(),
            "yaw_deg": self.spin_yaw.value(),
        }

    def is_legend_colors(self) -> bool:
        """Return whether legend color mode is active."""
        return self._chk_legend.isChecked()

    def set_transform_values(
        self, tx: float, ty: float, tz: float,
        roll_deg: float, pitch_deg: float, yaw_deg: float,
    ) -> None:
        """Set spinbox values without emitting transform_changed."""
        self._updating = True
        self.spin_tx.setValue(tx)
        self.spin_ty.setValue(ty)
        self.spin_tz.setValue(tz)
        self.spin_roll.setValue(roll_deg)
        self.spin_pitch.setValue(pitch_deg)
        self.spin_yaw.setValue(yaw_deg)
        self._updating = False
