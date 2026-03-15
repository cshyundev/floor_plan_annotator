from src.gui.base_type_editor import BaseTypeEditorWidget


class CustomPolygonTypeEditorWidget(BaseTypeEditorWidget):
    _dialog_title = "Add Custom Polygon Type"
    _default_alpha = 100
    _default_color = [100, 220, 100, 100]
    _default_border = [50, 160, 50]
    _in_use_label = "polygon(s)"
    _config_prefix = "custom_polygon"
    _item_class_path = "src.gui.items.custom_polygon_item.CustomPolygonItem"
    _type_attr = "polygon_type"
    _has_overlay = True
