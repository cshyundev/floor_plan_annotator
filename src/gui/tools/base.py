from src.core.config import ConfigManager
from src.core.input_context import InputContext


class Tool:
    """Base class for all drawing tools."""

    # When False, ObjectItem (and other interactive items) will ignore
    # mouse events so that drawing tools don't conflict with item interaction.
    allows_item_events = False

    def __init__(self, canvas):
        self.canvas = canvas
        self.scene = canvas.scene
        self._config = None

    @property
    def config(self):
        """Get the ConfigManager instance."""
        if self._config is None:
            self._config = ConfigManager.instance()
        return self._config

    def on_mouse_press(self, context: InputContext): pass
    def on_mouse_move(self, context: InputContext): pass
    def on_mouse_release(self, context: InputContext): pass

    def find_node_at(self, pos, tolerance=None):
        """Find a NodeItem at the given position within tolerance.

        Args:
            pos: QPointF position to search
            tolerance: Distance tolerance (uses config default if None)

        Returns:
            NodeItem if found, None otherwise
        """
        if tolerance is None:
            tolerance = self.config.get_ui_value("node", "snap_tolerance")

        from src.gui.items.nodes import NodeItem
        items = self.scene.items(pos)
        for item in items:
            if isinstance(item, NodeItem):
                return item
        return None
