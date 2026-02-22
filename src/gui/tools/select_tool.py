from src.core.input_context import InputContext
from src.gui.items.nodes import NodeItem, EdgeItem
from src.gui.items.room_item import RoomItem
from src.gui.items.custom_polygon_item import CustomPolygonItem
from src.gui.items.object_item import ObjectItem
from src.gui.tools.base import Tool


class SelectTool(Tool):
    allows_item_events = True  # SelectTool allows items to handle their own mouse events

    _CYCLE_PIXEL_TOLERANCE = 5  # pixels — threshold for "same position" detection

    _SELECTABLE_TYPES = (EdgeItem, RoomItem, CustomPolygonItem, ObjectItem)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.moving_item = None
        self.start_pos = None
        self._cycle_items = []
        self._cycle_index = 0
        self._last_click_scene_pos = None

    def _reset_cycle(self):
        self._cycle_items = []
        self._cycle_index = 0
        self._last_click_scene_pos = None

    def _same_position(self, new_pos, last_pos):
        """Check if new_pos is within pixel tolerance of last_pos."""
        new_screen = self.canvas.mapFromScene(new_pos)
        last_screen = self.canvas.mapFromScene(last_pos)
        dx = new_screen.x() - last_screen.x()
        dy = new_screen.y() - last_screen.y()
        return (dx * dx + dy * dy) <= (self._CYCLE_PIXEL_TOLERANCE ** 2)

    def on_mouse_press(self, context: InputContext):
        pos = context.scene_pos

        # Build candidate list: annotation items only, no children
        all_items = self.scene.items(pos)
        candidates = [
            i for i in all_items
            if isinstance(i, (NodeItem, *self._SELECTABLE_TYPES))
            and i.parentItem() is None
            and i != self.canvas.background_item
        ]

        # NodeItem takes priority — handle node move
        if candidates and isinstance(candidates[0], NodeItem):
            self.moving_item = candidates[0]
            self.start_pos = candidates[0].pos()
            self.canvas.status_message.emit(
                self.config.get_string("tools", "select", "moving"))
            self._reset_cycle()
            return

        # Filter to only selectable annotation types (no NodeItem)
        candidates = [i for i in candidates if isinstance(i, self._SELECTABLE_TYPES)]

        # Nothing at click point
        if not candidates:
            self.scene.clearSelection()
            self.canvas.status_message.emit(
                self.config.get_string("tools", "select", "cleared"))
            self._reset_cycle()
            return

        # Determine if this is a cycle click (same position as last click)
        is_cycle = (
            self._last_click_scene_pos is not None
            and self._cycle_items
            and self._same_position(pos, self._last_click_scene_pos)
            and self._cycle_items == candidates
        )

        if is_cycle:
            self._cycle_index = (self._cycle_index + 1) % len(self._cycle_items)
        else:
            self._cycle_items = candidates
            self._cycle_index = 0
            self._last_click_scene_pos = pos

        # Select the item at current cycle index
        self.scene.clearSelection()
        item = self._cycle_items[self._cycle_index]
        item.setSelected(True)

        if len(self._cycle_items) > 1:
            msg = self.config.get_string("tools", "select", "cycling")
            self.canvas.status_message.emit(
                msg.format(index=self._cycle_index + 1,
                           total=len(self._cycle_items)))
        else:
            self.canvas.status_message.emit(
                self.config.get_string("tools", "select", "selected"))

    def on_mouse_move(self, context: InputContext):
        if self.moving_item:
             pass

    def on_mouse_release(self, context: InputContext):
        self.moving_item = None
        self.start_pos = None

    def cleanup(self):
        self._reset_cycle()
        self.moving_item = None
        self.start_pos = None
