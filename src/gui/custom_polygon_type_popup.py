from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton
from PyQt6.QtGui import QColor, QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize
from src.core.config import ConfigManager


class CustomPolygonTypePopup(QDialog):
    """Popup dialog for selecting a custom polygon type."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._selected_key = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        config = ConfigManager.instance()
        types = config.get_custom_polygon_types()
        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))

        for key in sorted_keys:
            t_data = types[key]
            btn = QPushButton(key)

            c = t_data.get("color", [100, 220, 100, 100])
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(*c))
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(QSize(16, 16))

            btn.clicked.connect(lambda checked, k=key: self._on_select(k))
            layout.addWidget(btn)

    def _on_select(self, key):
        self._selected_key = key
        self.accept()

    def get_selected_type(self):
        return self._selected_key
