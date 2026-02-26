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
        """Handle mouse wheel event for zooming or 3D property adjustment.

        Ctrl + Wheel: Adjust selected object's 3D Height (±0.1m)
        Ctrl + Shift + Wheel: Adjust selected object's Elevation (±0.1m)
        Otherwise: Normal zoom behavior.

        Args:
            event: QWheelEvent
        """
        modifiers = event.modifiers()
        ctrl_held = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

        if ctrl_held:
            if self._handle_object_3d_wheel(event):
                return

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

    def _handle_object_3d_wheel(self, event):
        """Adjust selected object's 3D properties via Ctrl+Wheel.

        Returns:
            True if handled, False if no single ObjectItem selected.
        """
        from src.gui.items import ObjectItem
        from src.core.undo_commands import ChangeObject3DPropertiesCommand

        selected = [
            item for item in self.canvas.scene.selectedItems()
            if isinstance(item, ObjectItem)
        ]
        if len(selected) != 1:
            return False

        item = selected[0]
        step = 0.1
        delta = step if event.angleDelta().y() > 0 else -step

        old_elev = item.elevation
        old_h3d = item.height_3d

        shift_held = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if shift_held:
            new_elev = round(old_elev + delta, 2)
            new_h3d = old_h3d
            self.canvas.status_message.emit(f"Elevation: {new_elev:.2f} m")
        else:
            new_elev = old_elev
            new_h3d = max(0.01, round(old_h3d + delta, 2))
            self.canvas.status_message.emit(f"3D Height: {new_h3d:.2f} m")

        if new_elev != old_elev or new_h3d != old_h3d:
            cmd = ChangeObject3DPropertiesCommand(
                item, old_elev, old_h3d, new_elev, new_h3d
            )
            self.canvas.push_command(cmd)

        return True

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
