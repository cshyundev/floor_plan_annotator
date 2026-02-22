from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                             QPushButton, QLineEdit, QColorDialog, QFormLayout, QMessageBox)
from PyQt6.QtGui import QColor, QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from src.core.config import ConfigManager


class CustomPolygonTypeEditorWidget(QWidget):
    config_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = ConfigManager.instance()
        self.current_key = None
        self._scene = None
        self.init_ui()
        self.load_types()

    def set_scene(self, scene):
        self._scene = scene

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.type_list = QListWidget()
        self.type_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.type_list)

        self.form_widget = QWidget()
        form_layout = QFormLayout(self.form_widget)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_name_changed)
        form_layout.addRow("Name:", self.name_edit)

        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self.pick_color)
        form_layout.addRow("Color:", self.color_btn)

        self.border_btn = QPushButton()
        self.border_btn.clicked.connect(self.pick_border)
        form_layout.addRow("Border:", self.border_btn)

        layout.addWidget(self.form_widget)
        self.form_widget.setEnabled(False)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.add_type)
        btn_layout.addWidget(self.add_btn)

        self.del_btn = QPushButton("Delete")
        self.del_btn.clicked.connect(self.delete_type)
        self.del_btn.setEnabled(False)
        btn_layout.addWidget(self.del_btn)

        layout.addLayout(btn_layout)

    def load_types(self):
        self.type_list.clear()
        types = self.config.get_custom_polygon_types()
        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))
        for key in sorted_keys:
            self.type_list.addItem(key)

    def on_item_clicked(self, item):
        self.current_key = item.text()
        self.form_widget.setEnabled(True)
        self.del_btn.setEnabled(True)

        data = self.config.get_custom_polygon_type(self.current_key)
        if data:
            self.name_edit.blockSignals(True)
            self.name_edit.setText(data.get("name", ""))
            self.name_edit.blockSignals(False)
            self.update_color_btn(self.color_btn, data.get("color", [100, 220, 100, 100]))
            self.update_color_btn(self.border_btn, data.get("border", [50, 160, 50]))

    def update_color_btn(self, btn, rgba):
        color = QColor(*rgba)
        pixmap = QPixmap(16, 16)
        pixmap.fill(color)
        btn.setIcon(QIcon(pixmap))
        btn.setText(f"{rgba}")

    def on_name_changed(self, text):
        if self.current_key:
            self.config.update_custom_polygon_type(self.current_key, name=text)
            self.config_changed.emit()

    def pick_color(self):
        if not self.current_key:
            return
        data = self.config.get_custom_polygon_type(self.current_key)
        curr = data.get("color", [100, 220, 100, 100])
        color = QColorDialog.getColor(
            QColor(*curr), self, "Select Fill Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            rgba = [color.red(), color.green(), color.blue(), color.alpha()]
            self.config.update_custom_polygon_type(self.current_key, color=rgba)
            self.update_color_btn(self.color_btn, rgba)
            self.config_changed.emit()

    def pick_border(self):
        if not self.current_key:
            return
        data = self.config.get_custom_polygon_type(self.current_key)
        curr = data.get("border", [50, 160, 50])
        if len(curr) == 3:
            curr = curr + [255]
        color = QColorDialog.getColor(QColor(*curr), self, "Select Border Color")
        if color.isValid():
            rgb = [color.red(), color.green(), color.blue()]
            self.config.update_custom_polygon_type(self.current_key, border=rgb)
            self.update_color_btn(self.border_btn, rgb)
            self.config_changed.emit()

    def add_type(self):
        import uuid
        key = f"cpoly_{uuid.uuid4().hex[:4]}"
        name = "New Zone"
        color = [100, 220, 100, 100]
        border = [50, 160, 50]

        if self.config.add_custom_polygon_type(key, name, color, border):
            self.load_types()
            items = self.type_list.findItems(key, Qt.MatchFlag.MatchExactly)
            if items:
                self.type_list.setCurrentItem(items[0])
                self.on_item_clicked(items[0])
            self.config_changed.emit()

    def delete_type(self):
        if not self.current_key:
            return

        in_use = self._check_type_in_use(self.current_key)
        if in_use:
            reply = QMessageBox.warning(
                self, "Type In Use",
                f"Type '{self.current_key}' is used by {len(in_use)} polygon(s).\n"
                "These will show default styling.\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.config.delete_custom_polygon_type(self.current_key)
        self.load_types()
        self.current_key = None
        self.form_widget.setEnabled(False)
        self.del_btn.setEnabled(False)
        self.name_edit.clear()
        self.color_btn.setIcon(QIcon())
        self.border_btn.setIcon(QIcon())
        self.config_changed.emit()

    def _check_type_in_use(self, type_key):
        if not self._scene:
            return []
        from src.gui.items import CustomPolygonItem
        return [
            item for item in self._scene.items()
            if isinstance(item, CustomPolygonItem) and item.polygon_type == type_key
        ]

    def update_all(self):
        """Refresh all CustomPolygonItems in scene."""
        if not self._scene:
            return
        from src.gui.items import CustomPolygonItem
        for item in self._scene.items():
            if isinstance(item, CustomPolygonItem):
                item.update_style()
                item.update_overlay()
