from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout,
                             QCheckBox, QSpinBox, QDialogButtonBox, QGroupBox)
from PyQt6.QtCore import QSettings


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)

        # Auto-save group
        group = QGroupBox("Auto-save")
        form = QFormLayout(group)

        self._autosave_enabled = QCheckBox()
        form.addRow("Enable auto-save:", self._autosave_enabled)

        self._autosave_interval = QSpinBox()
        self._autosave_interval.setRange(1, 60)
        self._autosave_interval.setSuffix(" min")
        form.addRow("Interval:", self._autosave_interval)

        layout.addWidget(group)

        # SpinBox enabled state follows checkbox
        self._autosave_enabled.toggled.connect(self._autosave_interval.setEnabled)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_settings()

    def _load_settings(self):
        s = QSettings()
        enabled = s.value("autosave/enabled", defaultValue=True, type=bool)
        interval = s.value("autosave/interval_minutes", defaultValue=5, type=int)
        self._autosave_enabled.setChecked(enabled)
        self._autosave_interval.setValue(interval)
        self._autosave_interval.setEnabled(enabled)

    def save_settings(self):
        s = QSettings()
        s.setValue("autosave/enabled", self._autosave_enabled.isChecked())
        s.setValue("autosave/interval_minutes", self._autosave_interval.value())
