"""Stub Viewer3D for when Open3D is not available."""

import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QPoint


class Viewer3DStub(QWidget):
    """Stub 3D viewer that shows an error message when Open3D is not available."""

    def __init__(self):
        super().__init__()
        self.geometry = None

    def paintEvent(self, event):
        """Paint error message."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        painter.setPen(QColor(150, 150, 150))
        font = QFont()
        font.setPointSize(12)
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

    def render_scene(self):
        """Stub method."""
        pass
