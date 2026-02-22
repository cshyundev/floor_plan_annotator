from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox
from src.gui.room_type_editor import RoomTypeEditorWidget
from src.gui.custom_polygon_type_editor import CustomPolygonTypeEditorWidget
from src.gui.object_type_editor import ObjectTypeEditorWidget


class TypeEditorDialog(QDialog):
    """Dialog wrapping the three annotation type editor widgets."""

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Annotation Types")
        self.resize(450, 500)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        self.room_editor = RoomTypeEditorWidget()
        self.room_editor.set_scene(canvas.scene)
        self.room_editor.config_changed.connect(canvas.update_all_rooms)
        self.tabs.addTab(self.room_editor, "Room Types")

        self.custom_polygon_editor = CustomPolygonTypeEditorWidget()
        self.custom_polygon_editor.set_scene(canvas.scene)
        self.custom_polygon_editor.config_changed.connect(canvas.update_all_custom_polygons)
        self.tabs.addTab(self.custom_polygon_editor, "Polygon Types")

        self.object_editor = ObjectTypeEditorWidget()
        self.object_editor.set_scene(canvas.scene)
        self.object_editor.config_changed.connect(canvas.update_all_objects)
        self.tabs.addTab(self.object_editor, "Object Types")

        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
