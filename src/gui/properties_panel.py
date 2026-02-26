from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
                             QComboBox, QStackedWidget, QDoubleSpinBox)
from PyQt6.QtCore import Qt, QPointF
from src.core.config import ConfigManager
from src.gui.items import RoomItem, CustomPolygonItem, ObjectItem, EdgeItem


class PropertiesPanel(QWidget):
    """Shows and edits properties of the currently selected annotation item."""

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.config = ConfigManager.instance()
        self._current_item = None
        self._updating = False
        self._init_ui()

    def _make_spinbox(self, min_val=-9999.0, max_val=9999.0, decimals=2, suffix=""):
        sb = QDoubleSpinBox()
        sb.setRange(min_val, max_val)
        sb.setDecimals(decimals)
        sb.setSingleStep(0.01)
        if suffix:
            sb.setSuffix(suffix)
        sb.setKeyboardTracking(False)
        return sb

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.header_label = QLabel("No Selection")
        self.header_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #4FC3F7; padding: 2px 0;"
        )
        layout.addWidget(self.header_label)

        self.stack = QStackedWidget()

        # Page 0: empty state
        empty = QLabel("Select an annotation to\nview its properties.")
        empty.setWordWrap(True)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setStyleSheet("color: #8890A0; padding: 12px 0;")
        self.stack.addWidget(empty)

        # Page 1: Object (OBB) properties — editable
        self._init_object_page()

        # Page 2: Wall properties — editable endpoints
        self._init_wall_page()

        # Page 3: Polygon (Room / CustomPolygon) — type + read-only vertex count
        self._init_polygon_page()

        self.stack.addWidget(self.form_widget_object)
        self.stack.addWidget(self.form_widget_wall)
        self.stack.addWidget(self.form_widget_polygon)

        layout.addWidget(self.stack)

    def _init_object_page(self):
        self.form_widget_object = QWidget()
        form = QFormLayout(self.form_widget_object)
        form.setContentsMargins(0, 4, 0, 0)

        self.obj_type_label = QLabel()
        form.addRow("Category:", self.obj_type_label)

        self.obj_id_label = QLabel()
        form.addRow("ID:", self.obj_id_label)

        self.obj_subtype_combo = QComboBox()
        self.obj_subtype_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Type:", self.obj_subtype_combo)

        self.obj_cx = self._make_spinbox(suffix=" m")
        self.obj_cx.valueChanged.connect(self._on_object_edited)
        form.addRow("Center X:", self.obj_cx)

        self.obj_cy = self._make_spinbox(suffix=" m")
        self.obj_cy.valueChanged.connect(self._on_object_edited)
        form.addRow("Center Y:", self.obj_cy)

        self.obj_w = self._make_spinbox(min_val=0.01, suffix=" m")
        self.obj_w.valueChanged.connect(self._on_object_edited)
        form.addRow("Width:", self.obj_w)

        self.obj_h = self._make_spinbox(min_val=0.01, suffix=" m")
        self.obj_h.valueChanged.connect(self._on_object_edited)
        form.addRow("Height:", self.obj_h)

        self.obj_angle = self._make_spinbox(min_val=-360.0, max_val=360.0, decimals=1, suffix="\u00b0")
        self.obj_angle.valueChanged.connect(self._on_object_edited)
        form.addRow("Angle:", self.obj_angle)

        separator_3d = QLabel("3D Properties")
        separator_3d.setStyleSheet("font-weight: bold; color: #8890A0; margin-top: 8px;")
        form.addRow(separator_3d)

        self.obj_elevation = self._make_spinbox(min_val=-10.0, max_val=10.0, suffix=" m")
        self.obj_elevation.valueChanged.connect(self._on_object_3d_edited)
        form.addRow("Elevation:", self.obj_elevation)

        self.obj_height_3d = self._make_spinbox(min_val=0.01, max_val=10.0, suffix=" m")
        self.obj_height_3d.valueChanged.connect(self._on_object_3d_edited)
        form.addRow("3D Height:", self.obj_height_3d)

    def _init_wall_page(self):
        self.form_widget_wall = QWidget()
        form = QFormLayout(self.form_widget_wall)
        form.setContentsMargins(0, 4, 0, 0)

        self.wall_type_label = QLabel()
        form.addRow("Category:", self.wall_type_label)

        self.wall_id_label = QLabel()
        form.addRow("ID:", self.wall_id_label)

        self.wall_sx = self._make_spinbox(suffix=" m")
        self.wall_sx.valueChanged.connect(self._on_wall_edited)
        form.addRow("Start X:", self.wall_sx)

        self.wall_sy = self._make_spinbox(suffix=" m")
        self.wall_sy.valueChanged.connect(self._on_wall_edited)
        form.addRow("Start Y:", self.wall_sy)

        self.wall_ex = self._make_spinbox(suffix=" m")
        self.wall_ex.valueChanged.connect(self._on_wall_edited)
        form.addRow("End X:", self.wall_ex)

        self.wall_ey = self._make_spinbox(suffix=" m")
        self.wall_ey.valueChanged.connect(self._on_wall_edited)
        form.addRow("End Y:", self.wall_ey)

    def _init_polygon_page(self):
        self.form_widget_polygon = QWidget()
        form = QFormLayout(self.form_widget_polygon)
        form.setContentsMargins(0, 4, 0, 0)

        self.poly_type_label = QLabel()
        form.addRow("Category:", self.poly_type_label)

        self.poly_id_label = QLabel()
        form.addRow("ID:", self.poly_id_label)

        self.poly_subtype_combo = QComboBox()
        self.poly_subtype_combo.currentIndexChanged.connect(self._on_poly_type_changed)
        form.addRow("Type:", self.poly_subtype_combo)

        self.poly_info_label = QLabel()
        self.poly_info_label.setStyleSheet("color: #8890A0;")
        form.addRow("Vertices:", self.poly_info_label)

    # ── Scene connection ──

    def connect_scene(self, scene):
        scene.selectionChanged.connect(self._on_selection_changed)

    # ── Selection handling ──

    def _on_selection_changed(self):
        selected = self.canvas.scene.selectedItems()
        annotations = [
            item for item in selected
            if isinstance(item, (RoomItem, CustomPolygonItem, ObjectItem, EdgeItem))
        ]

        if len(annotations) == 1:
            self._show_item(annotations[0])
        elif len(annotations) > 1:
            self._show_multi_selection(annotations)
        else:
            self._show_empty()

    def _show_empty(self):
        self._current_item = None
        self.header_label.setText("No Selection")
        self.stack.setCurrentIndex(0)

    def _show_multi_selection(self, items):
        self._current_item = None
        self.header_label.setText(f"{len(items)} items selected")
        self.stack.setCurrentIndex(0)

    def _show_item(self, item):
        self._current_item = item
        self._updating = True

        if isinstance(item, ObjectItem):
            self.header_label.setText("Object")
            self.obj_type_label.setText("Object (OBB)")
            self.obj_id_label.setText(item.object_id or "?")
            self._populate_combo(self.obj_subtype_combo, "object", item.object_type)
            self.obj_cx.setValue(item.center.x())
            self.obj_cy.setValue(item.center.y())
            self.obj_w.setValue(item.width)
            self.obj_h.setValue(item.height)
            self.obj_angle.setValue(item.angle)
            self.obj_elevation.setValue(item.elevation)
            self.obj_height_3d.setValue(item.height_3d)
            self.stack.setCurrentIndex(1)

        elif isinstance(item, EdgeItem):
            self.header_label.setText("Wall")
            self.wall_type_label.setText("Wall")
            self.wall_id_label.setText(item.edge_id or "?")
            self.wall_sx.setValue(item.start_node.pos().x())
            self.wall_sy.setValue(item.start_node.pos().y())
            self.wall_ex.setValue(item.end_node.pos().x())
            self.wall_ey.setValue(item.end_node.pos().y())
            self.stack.setCurrentIndex(2)

        elif isinstance(item, (RoomItem, CustomPolygonItem)):
            if isinstance(item, RoomItem):
                self.header_label.setText("Room")
                self.poly_type_label.setText("Room")
                self.poly_id_label.setText(item.room_id or "?")
                self._populate_combo(self.poly_subtype_combo, "room", item.room_type)
            else:
                self.header_label.setText("Custom Polygon")
                self.poly_type_label.setText("Custom Polygon")
                self.poly_id_label.setText(item.polygon_id or "?")
                self._populate_combo(self.poly_subtype_combo, "custom_polygon", item.polygon_type)
            self.poly_info_label.setText(str(len(item.nodes)))
            self.stack.setCurrentIndex(3)

        self._updating = False

    # ── Type combo helpers ──

    def _populate_combo(self, combo, category, current_type):
        combo.blockSignals(True)
        combo.clear()
        combo.setEnabled(True)

        if category == "room":
            types = self.config.get_room_types()
        elif category == "custom_polygon":
            types = self.config.get_custom_polygon_types()
        elif category == "object":
            types = self.config.get_object_types()
        else:
            combo.blockSignals(False)
            return

        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))
        current_index = 0
        for i, key in enumerate(sorted_keys):
            combo.addItem(types[key].get("name", key), key)
            if key == current_type:
                current_index = i

        combo.setCurrentIndex(current_index)
        combo.blockSignals(False)

    def _on_type_changed(self, index):
        """Object type combo changed."""
        if self._updating or self._current_item is None or index < 0:
            return
        new_type_key = self.obj_subtype_combo.currentData()
        if new_type_key and isinstance(self._current_item, ObjectItem):
            self._current_item.change_type(new_type_key)

    def _on_poly_type_changed(self, index):
        """Room / CustomPolygon type combo changed."""
        if self._updating or self._current_item is None or index < 0:
            return
        new_type_key = self.poly_subtype_combo.currentData()
        if new_type_key and hasattr(self._current_item, 'change_type'):
            self._current_item.change_type(new_type_key)

    # ── Editable property handlers ──

    def _on_object_edited(self):
        """Apply edited OBB values with undo support."""
        if self._updating or self._current_item is None:
            return
        if not isinstance(self._current_item, ObjectItem):
            return

        item = self._current_item
        old_state = (QPointF(item.center), item.width, item.height, item.angle)

        new_center = QPointF(self.obj_cx.value(), self.obj_cy.value())
        new_w = self.obj_w.value()
        new_h = self.obj_h.value()
        new_angle = self.obj_angle.value()
        new_state = (new_center, new_w, new_h, new_angle)

        if old_state == new_state:
            return

        from src.core.undo_commands import TransformObjectCommand
        cmd = TransformObjectCommand(item, old_state, new_state)
        self.canvas.push_command(cmd)

    def _on_object_3d_edited(self):
        """Apply edited 3D property values with undo support."""
        if self._updating or self._current_item is None:
            return
        if not isinstance(self._current_item, ObjectItem):
            return

        item = self._current_item
        old_elev = item.elevation
        old_h3d = item.height_3d
        new_elev = self.obj_elevation.value()
        new_h3d = self.obj_height_3d.value()

        if old_elev == new_elev and old_h3d == new_h3d:
            return

        from src.core.undo_commands import ChangeObject3DPropertiesCommand
        cmd = ChangeObject3DPropertiesCommand(item, old_elev, old_h3d, new_elev, new_h3d)
        self.canvas.push_command(cmd)

    def _on_wall_edited(self):
        """Apply edited wall endpoint positions with undo support."""
        if self._updating or self._current_item is None:
            return
        if not isinstance(self._current_item, EdgeItem):
            return

        item = self._current_item
        start_node = item.start_node
        end_node = item.end_node

        old_positions = [QPointF(start_node.pos()), QPointF(end_node.pos())]
        new_positions = [
            QPointF(self.wall_sx.value(), self.wall_sy.value()),
            QPointF(self.wall_ex.value(), self.wall_ey.value()),
        ]

        if old_positions == new_positions:
            return

        from src.core.undo_commands import MoveNodesCommand
        cmd = MoveNodesCommand([start_node, end_node], old_positions, new_positions)
        self.canvas.push_command(cmd)
