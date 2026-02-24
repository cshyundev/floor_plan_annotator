from src.gui.base_type_editor import BaseTypeEditorWidget


class CustomPolygonTypeEditorWidget(BaseTypeEditorWidget):
    _dialog_title = "Add Custom Polygon Type"
    _key_prefix = "cpoly_"
    _default_alpha = 100
    _default_color = [100, 220, 100, 100]
    _default_border = [50, 160, 50]
    _in_use_label = "polygon(s)"

    def _get_types(self):
        return self.config.get_custom_polygon_types()

    def _get_type(self, key):
        return self.config.get_custom_polygon_type(key)

    def _add_config_type(self, key, name, color, border):
        return self.config.add_custom_polygon_type(key, name, color, border)

    def _update_config_type(self, key, **kwargs):
        return self.config.update_custom_polygon_type(key, **kwargs)

    def _delete_config_type(self, key):
        self.config.delete_custom_polygon_type(key)

    def _check_type_in_use(self, type_key):
        if not self._scene:
            return []
        from src.gui.items import CustomPolygonItem
        return [
            item for item in self._scene.items()
            if isinstance(item, CustomPolygonItem) and item.polygon_type == type_key
        ]

    def update_all(self):
        if not self._scene:
            return
        from src.gui.items import CustomPolygonItem
        for item in self._scene.items():
            if isinstance(item, CustomPolygonItem):
                item.update_style()
                item.update_overlay()
