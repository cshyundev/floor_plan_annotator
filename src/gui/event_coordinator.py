"""Event coordination for Canvas2D."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from src.core.config import ConfigManager


class EventCoordinator:
    """Coordinates mouse and keyboard events, delegating to appropriate handlers."""

    def __init__(self, canvas):
        """Initialize event coordinator.

        Args:
            canvas: Canvas2D instance
        """
        self.canvas = canvas
        self._config = ConfigManager.instance()

    def handle_mouse_press(self, event):
        """Handle mouse press event.

        Args:
            event: QMouseEvent
        """
        context = self.canvas._create_input_context(event)
        if self.canvas.current_tool:
            self.canvas.current_tool.on_mouse_press(context)

    def handle_mouse_move(self, event):
        """Handle mouse move event.

        Args:
            event: QMouseEvent
        """
        context = self.canvas._create_input_context(event)
        if self.canvas.current_tool:
            self.canvas.current_tool.on_mouse_move(context)

    def handle_mouse_release(self, event):
        """Handle mouse release event.

        Args:
            event: QMouseEvent
        """
        context = self.canvas._create_input_context(event)
        if self.canvas.current_tool:
            self.canvas.current_tool.on_mouse_release(context)

    def handle_wheel(self, event):
        """Handle mouse wheel event for zooming.

        Args:
            event: QWheelEvent
        """
        from src.core.config import ConfigManager

        zoom_in = event.angleDelta().y() > 0
        factor = 1.1 if zoom_in else 0.9

        # Get current zoom level (transform matrix scale)
        current_zoom = self.canvas.transform().m11()

        # Get min/max zoom from config
        config = ConfigManager.instance()
        min_zoom = config.get_ui_value("canvas", "min_zoom")
        max_zoom = config.get_ui_value("canvas", "max_zoom")

        # Calculate new zoom level
        new_zoom = current_zoom * factor

        # Check bounds and apply zoom only if within limits
        if min_zoom <= new_zoom <= max_zoom:
            self.canvas.scale(factor, factor)

    def handle_key_press(self, event):
        """Handle keyboard event.

        Args:
            event: QKeyEvent

        Returns:
            bool: True if event was handled, False otherwise
        """
        # Check for copy
        if self._is_copy_event(event):
            self.canvas.copy_selection()
            return True

        # Check for paste
        if self._is_paste_event(event):
            self.canvas.paste_clipboard()
            return True

        # Check for delete
        if self._is_delete_event(event):
            self.canvas.delete_selected_items()
            return True

        return False

    def _is_copy_event(self, event):
        """Check if event is a copy command."""
        return (event.matches(QKeySequence.StandardKey.Copy) or
                (event.modifiers() & Qt.KeyboardModifier.ControlModifier and
                 event.key() == Qt.Key.Key_C))

    def _is_paste_event(self, event):
        """Check if event is a paste command."""
        return (event.matches(QKeySequence.StandardKey.Paste) or
                (event.modifiers() & Qt.KeyboardModifier.ControlModifier and
                 event.key() == Qt.Key.Key_V))

    def _is_delete_event(self, event):
        """Check if event is a delete command."""
        delete_keys = self._config.get_shortcut("tools", "delete") or ["Delete", "Backspace"]

        key_map = {
            "Delete": Qt.Key.Key_Delete,
            "Backspace": Qt.Key.Key_Backspace,
        }

        for k_name in delete_keys:
            if k_name in key_map and event.key() == key_map[k_name]:
                return True

        return False
