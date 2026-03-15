from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton
from PyQt6.QtGui import QColor, QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize


class TypePopup(QDialog):
    """Generic popup dialog for selecting an annotation type with colored icons."""

    def __init__(self, parent, types_getter: callable, default_color: list):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._selected_key = None
        self._init_ui(types_getter, default_color)

    def _init_ui(self, types_getter, default_color):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        types = types_getter()
        sorted_keys = sorted(types.keys(), key=lambda k: types[k].get("index", 0))

        for key in sorted_keys:
            t_data = types[key]
            btn = QPushButton(key)

            c = t_data.get("color", default_color)
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(*c))
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(QSize(16, 16))

            btn.setStyleSheet("text-align: left; padding-left: 4px;")
            btn.clicked.connect(lambda checked, k=key: self._on_select(k))
            layout.addWidget(btn)

    def _on_select(self, key):
        self._selected_key = key
        self.accept()

    def get_selected_type(self):
        return self._selected_key
