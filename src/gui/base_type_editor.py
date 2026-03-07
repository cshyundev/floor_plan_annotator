import colorsys
import random

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
                             QPushButton, QLineEdit, QColorDialog, QFormLayout, QMessageBox,
                             QInputDialog)
from PyQt6.QtGui import QColor, QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal
from src.core.config import ConfigManager


class BaseTypeEditorWidget(QWidget):
    """Base class for annotation type editor widgets (Room, CustomPolygon, Object)."""

    config_changed = pyqtSignal()

    # Subclasses must define these class attributes
    _dialog_title: str = ""
    _default_alpha: int = 100
    _default_color: list = [200, 200, 200, 100]
    _default_border: list = [100, 100, 100]
    _in_use_label: str = "item(s)"

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
        self.name_edit.editingFinished.connect(self.on_name_finished)
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
        types = self._get_types()
        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))
        for key in sorted_keys:
            item = QListWidgetItem(key)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.type_list.addItem(item)

    def on_item_clicked(self, item):
        self.current_key = item.data(Qt.ItemDataRole.UserRole)
        self.form_widget.setEnabled(True)
        self.del_btn.setEnabled(True)

        data = self._get_type(self.current_key)
        if data:
            self.name_edit.blockSignals(True)
            self.name_edit.setText(self.current_key)
            self.name_edit.blockSignals(False)
            self.update_color_btn(self.color_btn, data.get("color", self._default_color))
            self.update_color_btn(self.border_btn, data.get("border", self._default_border))

    def update_color_btn(self, btn, rgba):
        color = QColor(*rgba)
        pixmap = QPixmap(16, 16)
        pixmap.fill(color)
        btn.setIcon(QIcon(pixmap))
        btn.setText(f"{rgba}")

    def on_name_finished(self):
        if not self.current_key:
            return
        new_name = self.name_edit.text().strip()
        if not new_name or new_name == self.current_key:
            self.name_edit.setText(self.current_key)
            return
        if new_name in self._get_types():
            QMessageBox.warning(self, "Duplicate Name",
                                f"Type '{new_name}' already exists.")
            self.name_edit.setText(self.current_key)
            return
        old_key = self.current_key
        if self._rename_config_type(old_key, new_name):
            self._update_items_type(old_key, new_name)
            self.current_key = new_name
            current_item = self.type_list.currentItem()
            if current_item:
                current_item.setText(new_name)
                current_item.setData(Qt.ItemDataRole.UserRole, new_name)
            self.config_changed.emit()

    def pick_color(self):
        if not self.current_key:
            return
        data = self._get_type(self.current_key)
        curr = data.get("color", self._default_color)
        color = QColorDialog.getColor(
            QColor(*curr), self, "Select Fill Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            rgba = [color.red(), color.green(), color.blue(), color.alpha()]
            self._update_config_type(self.current_key, color=rgba)
            self.update_color_btn(self.color_btn, rgba)
            self.config_changed.emit()

    def pick_border(self):
        if not self.current_key:
            return
        data = self._get_type(self.current_key)
        curr = data.get("border", self._default_border)
        if len(curr) == 3:
            curr = curr + [255]
        color = QColorDialog.getColor(QColor(*curr), self, "Select Border Color")
        if color.isValid():
            rgb = [color.red(), color.green(), color.blue()]
            self._update_config_type(self.current_key, border=rgb)
            self.update_color_btn(self.border_btn, rgb)
            self.config_changed.emit()

    def _generate_unique_color(self, alpha=None):
        if alpha is None:
            alpha = self._default_alpha
        types = self._get_types()
        existing_hues = []
        for data in types.values():
            c = data.get("color", [128, 128, 128, 100])
            r, g, b = c[0] / 255, c[1] / 255, c[2] / 255
            h, _, _ = colorsys.rgb_to_hsv(r, g, b)
            existing_hues.append(h)

        min_hue_dist = 0.07
        h = random.random()
        for _ in range(50):
            if all(min(abs(h - eh), 1 - abs(h - eh)) >= min_hue_dist for eh in existing_hues):
                break
            h = random.random()

        s = random.uniform(0.4, 0.7)
        v = random.uniform(0.75, 0.95)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        fill = [int(r * 255), int(g * 255), int(b * 255), alpha]

        rb, gb, bb = colorsys.hsv_to_rgb(h, min(s + 0.3, 1.0), max(v - 0.25, 0.4))
        border = [int(rb * 255), int(gb * 255), int(bb * 255)]
        return fill, border

    def add_type(self):
        name, ok = QInputDialog.getText(self, self._dialog_title, "Name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        key = name

        if key in self._get_types():
            QMessageBox.warning(self, "Duplicate Name",
                                f"Type '{key}' already exists.")
            return

        color, border = self._generate_unique_color()

        if self._add_config_type(key, color, border):
            self.load_types()
            for i in range(self.type_list.count()):
                item = self.type_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == key:
                    self.type_list.setCurrentItem(item)
                    self.on_item_clicked(item)
                    break
            self.config_changed.emit()

    def delete_type(self):
        if not self.current_key:
            return

        in_use = self._check_type_in_use(self.current_key)
        if in_use:
            reply = QMessageBox.warning(
                self, "Type In Use",
                f"Type '{self.current_key}' is used by {len(in_use)} {self._in_use_label}.\n"
                "These will show default styling.\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._delete_config_type(self.current_key)
        self.load_types()
        self.current_key = None
        self.form_widget.setEnabled(False)
        self.del_btn.setEnabled(False)
        self.name_edit.clear()
        self.color_btn.setIcon(QIcon())
        self.border_btn.setIcon(QIcon())
        self.config_changed.emit()

    # --- Abstract interface: subclasses must implement ---

    def _get_types(self):
        raise NotImplementedError

    def _get_type(self, key):
        raise NotImplementedError

    def _add_config_type(self, key, color, border):
        raise NotImplementedError

    def _update_config_type(self, key, **kwargs):
        raise NotImplementedError

    def _rename_config_type(self, old_key, new_key):
        raise NotImplementedError

    def _update_items_type(self, old_key, new_key):
        raise NotImplementedError

    def _delete_config_type(self, key):
        raise NotImplementedError

    def _check_type_in_use(self, type_key):
        raise NotImplementedError

    def update_all(self):
        raise NotImplementedError
