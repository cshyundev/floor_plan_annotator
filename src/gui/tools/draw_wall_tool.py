from PyQt6.QtCore import Qt

from src.core.input_context import InputContext
from src.core.undo_commands import AddItemCommand
from src.gui.items.nodes import NodeItem, EdgeItem
from src.gui.tools.base import Tool


class DrawWallTool(Tool):
    annotation_type = "wall"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.current_start_node = None

    def on_mouse_press(self, context: InputContext):
        if not self.canvas._is_within_bounds(context.scene_pos):
            return
        if context.buttons == Qt.MouseButton.LeftButton:
            pos = context.scene_pos
            clicked_node = self.find_node_at(pos)

            if not self.current_start_node:
                self._handle_first_click(pos, clicked_node)
            else:
                self._handle_second_click(pos, clicked_node)

    def _handle_first_click(self, pos, clicked_node):
        """Handle first click: start wall drawing."""
        if clicked_node:
            self.current_start_node = clicked_node
        else:
            self.current_start_node = NodeItem(pos.x(), pos.y())
            cmd = AddItemCommand(
                self.scene,
                [self.current_start_node],
                self.config.get_string("tools", "wall", "add_node_cmd")
            )
            self.canvas.push_command(cmd)
        self.canvas.status_message.emit(self.config.get_string("tools", "wall", "started"))

    def _handle_second_click(self, pos, clicked_node):
        """Handle second click: complete wall segment and prepare for next."""
        end_node = clicked_node
        new_items = []

        if not end_node:
            end_node = NodeItem(pos.x(), pos.y())
            new_items.append(end_node)

        if end_node != self.current_start_node:
            edge = EdgeItem(self.current_start_node, end_node)
            new_items.append(edge)

            if new_items:
                cmd = AddItemCommand(
                    self.scene,
                    new_items,
                    self.config.get_string("tools", "wall", "add_wall_cmd")
                )
                self.canvas.push_command(cmd)
                self.canvas.status_message.emit(self.config.get_string("tools", "wall", "segment_added"))

        self.current_start_node = end_node

    def on_mouse_release(self, context: InputContext):
        if context.buttons == Qt.MouseButton.RightButton:
             self.current_start_node = None
             self.canvas.status_message.emit(self.config.get_string("tools", "wall", "finished"))
