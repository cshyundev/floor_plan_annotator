
import unittest
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt, QPoint
from PyQt6.QtGui import QUndoStack
import sys

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.canvas_2d import Canvas2D
from src.core.input_context import InputContext
from src.gui.items import NodeItem, EdgeItem


def _set_dummy_background(canvas):
    """Set a large dummy background so _is_within_bounds() returns True."""
    img = np.zeros((500, 500), dtype=np.uint8)
    canvas.update_background(img, (0.0, 0.0, 10.0, 10.0), 50.0)


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas2D()
        self.undo_stack = QUndoStack()
        self.canvas.set_undo_stack(self.undo_stack)
        _set_dummy_background(self.canvas)

    def create_context(self, x, y, buttons=Qt.MouseButton.LeftButton):
        return InputContext(
            scene_pos=QPointF(x, y),
            screen_pos=QPoint(int(x), int(y)),
            buttons=buttons
        )

    def _annotation_items(self):
        """Return scene items excluding background."""
        return [i for i in self.canvas.scene.items()
                if i != self.canvas.background_item]

    def test_draw_wall_flow(self):
        # 1. Select Wall Tool
        self.canvas.set_tool("wall")

        # 2. Click (Start) — coordinates must be within background bounds (0-10m)
        ctx1 = self.create_context(1, 1)
        self.canvas.wall_tool.on_mouse_press(ctx1)

        # Verify node added
        items = self._annotation_items()
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], NodeItem)
        node1 = items[0]

        # 3. Click (End)
        ctx2 = self.create_context(5, 1)
        self.canvas.wall_tool.on_mouse_press(ctx2)

        # Verify edge and node added
        items = self._annotation_items()
        self.assertEqual(len(items), 3)  # Node1, Edge, Node2

        # 4. Undo
        self.undo_stack.undo()
        items_after = self._annotation_items()
        self.assertEqual(len(items_after), 1)
        self.assertEqual(items_after[0], node1)

        # 5. Redo
        self.undo_stack.redo()
        self.assertEqual(len(self._annotation_items()), 3)

    def test_select_move_undo_flow(self):
        """Test node drag via NodeItem's own mouse events (not SelectTool).

        NodeItem handles drag internally: mousePressEvent saves start pos,
        Qt handles the drag, mouseReleaseEvent pushes MoveNodeCommand.
        SelectTool just sets allows_item_events=True to let this happen.
        """
        # Setup scene with one node
        node = NodeItem(50, 50)
        self.canvas.scene.addItem(node)
        self.canvas.set_tool("select")

        # Simulate NodeItem's own drag mechanism
        node._drag_start_pos = node.pos()  # mousePressEvent sets this
        node.setPos(150, 150)              # Qt drag moves the item

        # mouseReleaseEvent pushes MoveNodeCommand via views[0].push_command
        from src.core.undo_commands import MoveNodeCommand
        cmd = MoveNodeCommand(node, QPointF(50, 50), QPointF(150, 150))
        self.canvas.push_command(cmd)

        # Verify Undo Stack has command
        self.assertEqual(self.undo_stack.count(), 1)

        # Undo
        self.undo_stack.undo()
        self.assertEqual(node.pos(), QPointF(50, 50))

        # Redo
        self.undo_stack.redo()
        self.assertEqual(node.pos(), QPointF(150, 150))


if __name__ == "__main__":
    unittest.main()
