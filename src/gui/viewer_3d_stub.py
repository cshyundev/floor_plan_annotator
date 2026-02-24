"""Stub Viewer3D for when Open3D is not available."""

import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QPoint

from src.core.config import ConfigManager


class Viewer3DStub(QWidget):
    """Stub 3D viewer that shows an error message when Open3D is not available."""

    def __init__(self):
        super().__init__()
        self.geometry = None
        config = ConfigManager.instance()
        self._bg_color = config.get_color("viewer_3d", "background")
        self._text_color = config.get_color("viewer_3d", "text")
        self._font_size = config.get_ui_value("viewer_3d", "font_size")

    def paintEvent(self, event):
        """Paint error message."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._bg_color)
        painter.setPen(self._text_color)
        font = QFont()
        font.setPointSize(self._font_size)
        painter.setFont(font)
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "3D Viewer Not Available\n\n"
            "Open3D is not properly installed or\n"
            "OpenGL support is missing.\n\n"
            "The 2D canvas works normally."
        )

    def load_geometry(self, file_path):
        """Stub method."""
        print(f"Viewer3D stub: cannot load {file_path} (Open3D not available)")

    def update_slice_plane(self, z_height):
        """Stub method."""
        pass

    def update_slice_dragging(self, z_height):
        """Stub method."""
        pass

    def update_slice_final(self, z_height):
        """Stub method."""
        pass

    def render_scene(self):
        """Stub method."""
        pass

    def add_room_geometry(self, room_id, mesh):
        pass

    def remove_room_geometry(self, room_id):
        pass

    def add_wall_geometry(self, wall_id, mesh):
        pass

    def remove_wall_geometry(self, wall_id):
        pass

    def add_custom_polygon_geometry(self, polygon_id, mesh):
        pass

    def remove_custom_polygon_geometry(self, polygon_id):
        pass

    def add_object_geometry(self, object_id, mesh):
        pass

    def remove_object_geometry(self, object_id):
        pass

    def set_geometry_visibility(self, visible):
        pass
