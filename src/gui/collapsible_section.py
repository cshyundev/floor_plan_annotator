from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QSizePolicy
from PyQt6.QtCore import Qt


class CollapsibleSection(QWidget):
    """A collapsible section with a toggle header and child content."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setText(f"  {title}")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toggle_btn.setStyleSheet(
            "QToolButton { border: none; padding: 6px 8px; "
            "background-color: #2A2E38; font-weight: bold; font-size: 11px; "
            "color: #E0E4EC; text-align: left; }"
            "QToolButton:hover { background-color: #323844; }"
        )
        self.toggle_btn.toggled.connect(self._toggle)
        self._layout.addWidget(self.toggle_btn)

        self.content = QWidget()
        self._layout.addWidget(self.content)

    def set_content_layout(self, layout):
        self.content.setLayout(layout)

    def _toggle(self, checked):
        self.content.setVisible(checked)
        self.toggle_btn.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
