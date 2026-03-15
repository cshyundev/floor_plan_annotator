from PyQt6.QtWidgets import QDoubleSpinBox, QLabel

from src.gui.base_type_editor import BaseTypeEditorWidget


class ObjectTypeEditorWidget(BaseTypeEditorWidget):
    _dialog_title = "Add Object Type"
    _default_alpha = 150
    _default_color = [150, 200, 255, 150]
    _default_border = [80, 130, 200]
    _in_use_label = "object(s)"
    _config_prefix = "object"
    _item_class_path = "src.gui.items.object_item.ObjectItem"
    _type_attr = "object_type"
    _has_overlay = False

    def init_ui(self):
        super().init_ui()
        form = self.form_widget.layout()

        separator = QLabel("3D Defaults")
        separator.setStyleSheet("font-weight: bold; color: #8890A0; margin-top: 4px;")
        form.addRow(separator)

        self.elev_spin = QDoubleSpinBox()
        self.elev_spin.setRange(-10.0, 10.0)
        self.elev_spin.setDecimals(2)
        self.elev_spin.setSingleStep(0.1)
        self.elev_spin.setSuffix(" m")
        self.elev_spin.setKeyboardTracking(False)
        self.elev_spin.valueChanged.connect(self._on_elevation_changed)
        form.addRow("Elevation:", self.elev_spin)

        self.h3d_spin = QDoubleSpinBox()
        self.h3d_spin.setRange(0.01, 10.0)
        self.h3d_spin.setDecimals(2)
        self.h3d_spin.setSingleStep(0.1)
        self.h3d_spin.setSuffix(" m")
        self.h3d_spin.setKeyboardTracking(False)
        self.h3d_spin.valueChanged.connect(self._on_height_3d_changed)
        form.addRow("3D Height:", self.h3d_spin)

    def on_item_clicked(self, item):
        super().on_item_clicked(item)
        data = self._get_type(self.current_key)
        if data:
            self.elev_spin.blockSignals(True)
            self.elev_spin.setValue(data.get("default_elevation", 0.0))
            self.elev_spin.blockSignals(False)
            self.h3d_spin.blockSignals(True)
            self.h3d_spin.setValue(data.get("default_3d_height", 0.5))
            self.h3d_spin.blockSignals(False)

    def _on_elevation_changed(self, value):
        if self.current_key:
            self._update_config_type(self.current_key, default_elevation=value)
            self.config_changed.emit()

    def _on_height_3d_changed(self, value):
        if self.current_key:
            self._update_config_type(self.current_key, default_3d_height=value)
            self.config_changed.emit()
