
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import QPointF, Qt, QPoint
from PyQt6.QtGui import QUndoStack
import sys
import numpy as np

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.core.input_context import InputContext
from src.core.undo_commands import AddItemCommand, DeleteItemCommand
from src.gui.items import NodeItem, EdgeItem, RoomItem, CustomPolygonItem
from src.gui.tools import DrawWallTool, DrawRoomTool, DrawCustomPolygonTool
from src.gui.canvas_2d import Canvas2D


class MockCanvas:
    def __init__(self):
        self.scene = QGraphicsScene()
        self.background_item = None
        self.status_message = MagicMock()
        self.push_command = MagicMock()
        self._next_room_id = 0
        self._next_custom_polygon_id = 0
        self.snap_manager = MagicMock()
        self.snap_manager.snap_drawing_point = MagicMock(
            side_effect=lambda pos, **kw: pos
        )
        self.snap_manager.clear_guides = MagicMock()

    def transform(self):
        return MagicMock()

    def set_tool(self, tool_name):
        pass

    def next_room_id(self):
        rid = self._next_room_id
        self._next_room_id += 1
        return str(rid)

    def next_custom_polygon_id(self):
        pid = self._next_custom_polygon_id
        self._next_custom_polygon_id += 1
        return str(pid)

    def _is_within_bounds(self, pos):
        return True

    def mapFromScene(self, pos):
        return QPoint(int(pos.x()), int(pos.y()))


def create_context(scene_pos, buttons=Qt.MouseButton.LeftButton):
    return InputContext(
        scene_pos=scene_pos,
        screen_pos=QPoint(int(scene_pos.x()), int(scene_pos.y())),
        buttons=buttons,
    )


class TestDrawPolygonNodeReuse(unittest.TestCase):
    """Tests for polygon drawing tools reusing existing NodeItems."""

    def setUp(self):
        self.canvas = MockCanvas()

    def _add_existing_node(self, x, y):
        """Add a NodeItem to the scene and return it."""
        node = NodeItem(x, y)
        self.canvas.scene.addItem(node)
        return node

    def _click(self, tool, x, y):
        """Simulate a full click (press + release) at (x, y)."""
        ctx = create_context(QPointF(x, y))
        tool.on_mouse_press(ctx)
        tool.on_mouse_release(ctx)

    def test_polygon_reuses_existing_node_at_first_click(self):
        """Clicking on an existing NodeItem should reuse it, not create a new one."""
        existing = self._add_existing_node(5, 5)
        tool = DrawRoomTool(self.canvas)

        self._click(tool, 5, 5)

        self.assertEqual(len(tool.current_nodes), 1)
        self.assertIs(tool.current_nodes[0], existing)
        self.assertIn(existing, tool._shared_nodes)
        # Scene should still have exactly 1 NodeItem (reused, not duplicated)
        nodes_in_scene = [i for i in self.canvas.scene.items() if isinstance(i, NodeItem)]
        self.assertEqual(len(nodes_in_scene), 1)

    def test_polygon_reuses_node_mid_draw(self):
        """Existing nodes can be reused at any point during polygon drawing."""
        existing_c = self._add_existing_node(10, 10)
        tool = DrawRoomTool(self.canvas)

        self._click(tool, 0, 0)   # New node A
        self._click(tool, 10, 0)  # New node B
        self._click(tool, 10, 10) # Reuse existing_c

        self.assertEqual(len(tool.current_nodes), 3)
        self.assertIs(tool.current_nodes[2], existing_c)
        self.assertEqual(tool._shared_nodes, {existing_c})

    def test_finish_polygon_excludes_shared_nodes_from_command(self):
        """AddItemCommand should only contain new nodes, not shared ones."""
        existing_a = self._add_existing_node(0, 0)
        existing_b = self._add_existing_node(10, 0)
        tool = DrawRoomTool(self.canvas)

        self._click(tool, 0, 0)   # Reuse A
        self._click(tool, 10, 0)  # Reuse B
        self._click(tool, 10, 10) # New C

        with patch('src.gui.type_popup.TypePopup') as MockPopup:
            mock_popup = MagicMock()
            MockPopup.return_value = mock_popup
            mock_popup.exec.return_value = True
            mock_popup.get_selected_type.return_value = "living_room"

            ctx_finish = create_context(QPointF(0, 0), buttons=Qt.MouseButton.RightButton)
            tool.on_mouse_press(ctx_finish)

        cmd = self.canvas.push_command.call_args[0][0]
        self.assertIsInstance(cmd, AddItemCommand)

        # Command items should contain: new node C + RoomItem (NOT existing_a, existing_b)
        node_items = [i for i in cmd.items if isinstance(i, NodeItem)]
        room_items = [i for i in cmd.items if isinstance(i, RoomItem)]
        self.assertEqual(len(node_items), 1)  # Only new node C
        self.assertIsNot(node_items[0], existing_a)
        self.assertIsNot(node_items[0], existing_b)
        self.assertEqual(len(room_items), 1)

    def test_cleanup_preserves_shared_nodes(self):
        """cleanup() should keep shared nodes in scene, only remove new nodes."""
        existing = self._add_existing_node(0, 0)
        tool = DrawRoomTool(self.canvas)

        self._click(tool, 0, 0)   # Reuse existing
        self._click(tool, 10, 0)  # New node

        new_node = tool.current_nodes[1]
        self.assertIsNot(new_node, existing)

        tool.cleanup()

        # Existing node should still be in the scene
        self.assertEqual(existing.scene(), self.canvas.scene)
        # New node should be removed
        self.assertIsNone(new_node.scene())
        self.assertEqual(len(tool.current_nodes), 0)
        self.assertEqual(len(tool._shared_nodes), 0)

    def test_no_shared_nodes_behavior_unchanged(self):
        """Without existing nodes, behavior is identical to before."""
        tool = DrawRoomTool(self.canvas)

        for x in [0, 10, 20]:
            self._click(tool, x, 0)

        self.assertEqual(len(tool.current_nodes), 3)
        self.assertEqual(len(tool._shared_nodes), 0)

        with patch('src.gui.type_popup.TypePopup') as MockPopup:
            mock_popup = MagicMock()
            MockPopup.return_value = mock_popup
            mock_popup.exec.return_value = True
            mock_popup.get_selected_type.return_value = "living_room"

            ctx_finish = create_context(QPointF(0, 0), buttons=Qt.MouseButton.RightButton)
            tool.on_mouse_press(ctx_finish)

        cmd = self.canvas.push_command.call_args[0][0]
        node_items = [i for i in cmd.items if isinstance(i, NodeItem)]
        self.assertEqual(len(node_items), 3)  # All nodes are new

    def test_custom_polygon_reuses_nodes(self):
        """DrawCustomPolygonTool should also reuse existing nodes."""
        existing = self._add_existing_node(0, 0)
        tool = DrawCustomPolygonTool(self.canvas)

        self._click(tool, 0, 0)   # Reuse existing
        self._click(tool, 10, 0)  # New
        self._click(tool, 10, 10) # New

        self.assertIs(tool.current_nodes[0], existing)
        self.assertIn(existing, tool._shared_nodes)

        with patch('src.gui.type_popup.TypePopup') as MockPopup:
            mock_popup = MagicMock()
            MockPopup.return_value = mock_popup
            mock_popup.exec.return_value = True
            mock_popup.get_selected_type.return_value = "clean_zone"

            ctx_finish = create_context(QPointF(0, 0), buttons=Qt.MouseButton.RightButton)
            tool.on_mouse_press(ctx_finish)

        cmd = self.canvas.push_command.call_args[0][0]
        node_items = [i for i in cmd.items if isinstance(i, NodeItem)]
        self.assertEqual(len(node_items), 2)  # Only new nodes (not existing)


class TestDeleteWithSharedNodes(unittest.TestCase):
    """Tests for deletion logic with shared nodes."""

    def setUp(self):
        self.canvas = Canvas2D()
        self.undo_stack = QUndoStack()
        self.canvas.set_undo_stack(self.undo_stack)
        # Set dummy background so _is_within_bounds works
        img = np.zeros((500, 500), dtype=np.uint8)
        self.canvas.update_background(img, (0.0, 0.0, 10.0, 10.0), 50.0)

    def _items(self):
        """Return scene items excluding background."""
        return [i for i in self.canvas.scene.items()
                if i != self.canvas.background_item]

    def _create_wall(self, x1, y1, x2, y2):
        """Create a wall (2 nodes + 1 edge) directly in the scene."""
        n1 = NodeItem(x1, y1)
        n2 = NodeItem(x2, y2)
        self.canvas.scene.addItem(n1)
        self.canvas.scene.addItem(n2)
        edge = EdgeItem(n1, n2)
        self.canvas.scene.addItem(edge)
        return n1, n2, edge

    def _create_room(self, nodes, room_type="living_room"):
        """Create a room from a list of NodeItem, adding new ones to scene."""
        for n in nodes:
            if n.scene() is None:
                self.canvas.scene.addItem(n)
        room = RoomItem(nodes, room_type=room_type, room_id=self.canvas.next_room_id())
        self.canvas.scene.addItem(room)
        return room

    def test_delete_polygon_preserves_shared_wall_nodes(self):
        """Deleting a room that shares nodes with a wall should preserve those nodes."""
        n_a, n_b, edge_ab = self._create_wall(0, 0, 5, 0)
        n_c = NodeItem(5, 5)
        n_d = NodeItem(0, 5)
        room = self._create_room([n_a, n_b, n_c, n_d])

        # Select room and delete
        room.setSelected(True)
        self.canvas.delete_selected_items()

        items = self._items()
        # Wall nodes A, B and edge_ab should survive
        self.assertIn(n_a, items)
        self.assertIn(n_b, items)
        self.assertIn(edge_ab, items)
        # Room, C, D should be gone
        self.assertNotIn(room, items)
        self.assertNotIn(n_c, items)
        self.assertNotIn(n_d, items)

    def test_delete_wall_preserves_shared_polygon_nodes(self):
        """Deleting a wall edge should preserve nodes shared with a room."""
        n_a, n_b, edge_ab = self._create_wall(0, 0, 5, 0)
        n_c = NodeItem(5, 5)
        room = self._create_room([n_a, n_b, n_c])

        # Select edge and delete
        edge_ab.setSelected(True)
        self.canvas.delete_selected_items()

        items = self._items()
        # Edge should be gone
        self.assertNotIn(edge_ab, items)
        # Nodes A, B should survive (room still references them)
        self.assertIn(n_a, items)
        self.assertIn(n_b, items)
        # Room should survive
        self.assertIn(room, items)

    def test_delete_isolated_polygon_removes_all_nodes(self):
        """Deleting a polygon with no shared nodes should remove all its nodes."""
        n1 = NodeItem(0, 0)
        n2 = NodeItem(5, 0)
        n3 = NodeItem(5, 5)
        room = self._create_room([n1, n2, n3])

        room.setSelected(True)
        self.canvas.delete_selected_items()

        items = self._items()
        self.assertNotIn(room, items)
        self.assertNotIn(n1, items)
        self.assertNotIn(n2, items)
        self.assertNotIn(n3, items)

    def test_undo_room_preserves_shared_nodes(self):
        """Undoing room creation should preserve shared nodes in the scene."""
        n_a, n_b, edge_ab = self._create_wall(0, 0, 5, 0)
        n_c = NodeItem(5, 5)
        self.canvas.scene.addItem(n_c)

        # Create room via AddItemCommand with only new nodes
        room = RoomItem([n_a, n_b, n_c], room_type="living_room", room_id="0")
        # Simulate what _finish_polygon does: only new nodes in command
        cmd = AddItemCommand(self.canvas.scene, [n_c, room], "Add Room")
        self.canvas.push_command(cmd)

        items_before_undo = self._items()
        self.assertIn(room, items_before_undo)

        # Undo
        self.undo_stack.undo()

        items = self._items()
        # Shared nodes A, B and wall edge should survive
        self.assertIn(n_a, items)
        self.assertIn(n_b, items)
        self.assertIn(edge_ab, items)
        # Room and new node C should be removed
        self.assertNotIn(room, items)
        self.assertNotIn(n_c, items)

        # Redo should restore room and C
        self.undo_stack.redo()
        items = self._items()
        self.assertIn(room, items)
        self.assertIn(n_c, items)


class TestNodeSharingRoundtrip(unittest.TestCase):
    """Test save/load preserves node sharing."""

    def setUp(self):
        self.canvas = Canvas2D()
        self.undo_stack = QUndoStack()
        self.canvas.set_undo_stack(self.undo_stack)

    def test_save_load_preserves_sharing(self):
        """After save/load, coincident points should share a single NodeItem."""
        # Create wall A(1,1)-B(5,1)
        n_a = NodeItem(1, 1)
        n_b = NodeItem(5, 1)
        self.canvas.scene.addItem(n_a)
        self.canvas.scene.addItem(n_b)
        edge = EdgeItem(n_a, n_b)
        self.canvas.scene.addItem(edge)

        # Create room sharing A, B + new C(5,5)
        n_c = NodeItem(5, 5)
        self.canvas.scene.addItem(n_c)
        room = RoomItem([n_a, n_b, n_c], room_type="living_room", room_id="0")
        self.canvas.scene.addItem(room)

        # Save
        data = self.canvas.save_to_data()
        self.assertEqual(len(data.walls), 1)
        self.assertEqual(len(data.rooms), 1)

        # Load (clears scene and reconstructs)
        self.canvas.load_from_data(data)

        # Count NodeItems in scene
        items = list(self.canvas.scene.items())
        node_items = [i for i in items if isinstance(i, NodeItem)]
        room_items = [i for i in items if isinstance(i, RoomItem)]
        edge_items = [i for i in items if isinstance(i, EdgeItem)]

        # Should have 3 unique nodes (A, B, C) — not 5 (2 wall + 3 room)
        self.assertEqual(len(node_items), 3)
        self.assertEqual(len(room_items), 1)

        # Room's node at (1,1) should be the same object as wall's node at (1,1)
        loaded_room = room_items[0]
        room_node_positions = {(round(n.pos().x(), 4), round(n.pos().y(), 4)) for n in loaded_room.nodes}
        self.assertIn((1.0, 1.0), room_node_positions)
        self.assertIn((5.0, 1.0), room_node_positions)

        # Verify shared node: wall edge start/end should be same object as room nodes
        for e in edge_items:
            if not getattr(e, 'is_boundary_edge', False):
                # This is the wall edge
                wall_nodes = {e.start_node, e.end_node}
                shared_with_room = wall_nodes & set(loaded_room.nodes)
                self.assertEqual(len(shared_with_room), 2)


if __name__ == "__main__":
    unittest.main()
