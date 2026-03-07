from PyQt6.QtWidgets import QDoubleSpinBox, QLabel

from src.gui.base_type_editor import BaseTypeEditorWidget


class ObjectTypeEditorWidget(BaseTypeEditorWidget):
    _dialog_title = "Add Object Type"
    _default_alpha = 150
    _default_color = [150, 200, 255, 150]
    _default_border = [80, 130, 200]
    _in_use_label = "object(s)"

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

    def _get_types(self):
        return self.config.get_object_types()

    def _get_type(self, key):
        return self.config.get_object_type(key)

    def _add_config_type(self, key, color, border):
        return self.config.add_object_type(key, color, border)

    def _update_config_type(self, key, **kwargs):
        return self.config.update_object_type(key, **kwargs)

    def _rename_config_type(self, old_key, new_key):
        return self.config.rename_object_type(old_key, new_key)

    def _update_items_type(self, old_key, new_key):
        if not self._scene:
            return
        from src.gui.items import ObjectItem
        for item in self._scene.items():
            if isinstance(item, ObjectItem) and item.object_type == old_key:
                item.object_type = new_key
                item.update_style()

    def _delete_config_type(self, key):
        self.config.delete_object_type(key)

    def _check_type_in_use(self, type_key):
        if not self._scene:
            return []
        from src.gui.items import ObjectItem
        return [
            item for item in self._scene.items()
            if isinstance(item, ObjectItem) and item.object_type == type_key
        ]

    def update_all(self):
        if not self._scene:
            return
        from src.gui.items import ObjectItem
        for item in self._scene.items():
            if isinstance(item, ObjectItem):
                item.update_style()
