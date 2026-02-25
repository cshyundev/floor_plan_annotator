
import unittest
from unittest.mock import MagicMock, call
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import QPointF, Qt, QPoint
import sys

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.core.input_context import InputContext
from src.gui.tools import SelectTool, DrawWallTool, DrawRoomTool, DrawPolygonTool, DrawCustomPolygonTool, DrawObjectTool
from src.gui.items import NodeItem, RoomItem, CustomPolygonItem, ObjectItem
from src.core.undo_commands import AddItemCommand, MoveNodeCommand

class MockCanvas:
    def __init__(self):
        self.scene = QGraphicsScene()
        self.background_item = None
        self.status_message = MagicMock()
        self.push_command = MagicMock()
        self._next_room_id = 0
        self._next_custom_polygon_id = 0
        self._next_object_id = 0
        # Snap manager mock: pass-through by default
        self.snap_manager = MagicMock()
        self.snap_manager.snap_drawing_point = MagicMock(
            side_effect=lambda pos, **kw: pos
        )
        self.snap_manager.snap_drag_point = MagicMock(
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

    def next_object_id(self):
        oid = self._next_object_id
        self._next_object_id += 1
        return str(oid)

    def _is_within_bounds(self, pos):
        return True

    def mapFromScene(self, pos):
        return QPoint(int(pos.x()), int(pos.y()))


class TestTools(unittest.TestCase):
    def setUp(self):
        self.canvas = MockCanvas()

    def create_context(self, scene_pos, buttons=Qt.MouseButton.LeftButton):
        return InputContext(
            scene_pos=scene_pos,
            screen_pos=QPoint(int(scene_pos.x()), int(scene_pos.y())),
            buttons=buttons
        )

    def test_select_tool_move(self):
        tool = SelectTool(self.canvas)

        node = NodeItem(0, 0)
        self.canvas.scene.addItem(node)

        self.canvas.scene.items = unittest.mock.MagicMock(return_value=[node])

        ctx_press = self.create_context(QPointF(0, 0))
        tool.on_mouse_press(ctx_press)

        # SelectTool tracks the item that was clicked
        self.assertEqual(tool.moving_item, node)

        ctx_release = self.create_context(QPointF(100, 100))
        node.setPos(100, 100)
        tool.on_mouse_release(ctx_release)

        # SelectTool clears moving_item on release
        self.assertIsNone(tool.moving_item)
        # Note: MoveNodeCommand is pushed by NodeItem.mouseReleaseEvent (Qt event system),
        # not by SelectTool itself — so push_command is not called here.

    def test_room_tool_create(self):
        self.canvas.push_command.reset_mock()
        tool = DrawRoomTool(self.canvas)

        # Add Point 1
        ctx1 = self.create_context(QPointF(0, 0))
        tool.on_mouse_press(ctx1)
        tool.on_mouse_release(ctx1)

        # Add Point 2
        ctx2 = self.create_context(QPointF(10, 0))
        tool.on_mouse_press(ctx2)
        tool.on_mouse_release(ctx2)

        # Add Point 3
        ctx3 = self.create_context(QPointF(10, 10))
        tool.on_mouse_press(ctx3)
        tool.on_mouse_release(ctx3)

        # Finish (Right Click)
        ctx_finish = self.create_context(QPointF(0, 10), buttons=Qt.MouseButton.RightButton)

        with unittest.mock.patch('src.gui.room_type_popup.RoomTypePopup') as MockPopup:
            mock_popup = MagicMock()
            MockPopup.return_value = mock_popup
            mock_popup.exec.return_value = True
            mock_popup.get_selected_type.return_value = "living_room"
            tool.on_mouse_press(ctx_finish)

        self.assertEqual(self.canvas.push_command.call_count, 1)
        cmd = self.canvas.push_command.call_args[0][0]
        self.assertIsInstance(cmd, AddItemCommand)

    def test_draw_polygon_tool_is_base_of_draw_room_tool(self):
        """DrawRoomTool should be a subclass of DrawPolygonTool."""
        self.assertTrue(issubclass(DrawRoomTool, DrawPolygonTool))

    def test_draw_polygon_tool_adds_nodes(self):
        """DrawPolygonTool should track current_nodes as points are added."""
        tool = DrawRoomTool(self.canvas)

        for x in [0, 10, 20]:
            ctx = self.create_context(QPointF(x, 0))
            tool.on_mouse_press(ctx)
            tool.on_mouse_release(ctx)

        self.assertEqual(len(tool.current_nodes), 3)

    def test_draw_polygon_tool_cleanup(self):
        """cleanup() should remove temp nodes and edges from scene."""
        tool = DrawRoomTool(self.canvas)

        for x in [0, 10, 20]:
            ctx = self.create_context(QPointF(x, 0))
            tool.on_mouse_press(ctx)
            tool.on_mouse_release(ctx)

        self.assertEqual(len(tool.current_nodes), 3)

        tool.cleanup()

        self.assertEqual(len(tool.current_nodes), 0)
        self.assertEqual(len(tool.temp_edges), 0)

    def test_draw_polygon_tool_right_click_cancel(self):
        """Right click with < 3 nodes should cancel and clear."""
        tool = DrawRoomTool(self.canvas)

        # Add only 2 nodes
        for x in [0, 10]:
            ctx = self.create_context(QPointF(x, 0))
            tool.on_mouse_press(ctx)
            tool.on_mouse_release(ctx)

        self.assertEqual(len(tool.current_nodes), 2)

        ctx_right = self.create_context(QPointF(5, 5), buttons=Qt.MouseButton.RightButton)
        tool.on_mouse_press(ctx_right)

        self.assertEqual(len(tool.current_nodes), 0)

    def test_draw_polygon_tool_finish_polygon_raises_if_base(self):
        """DrawPolygonTool._finish_polygon() should raise NotImplementedError."""
        tool = DrawPolygonTool(self.canvas)
        with self.assertRaises(NotImplementedError):
            tool._finish_polygon()

    def test_draw_custom_polygon_tool_is_subclass(self):
        """DrawCustomPolygonTool should be a subclass of DrawPolygonTool."""
        self.assertTrue(issubclass(DrawCustomPolygonTool, DrawPolygonTool))

    def test_draw_custom_polygon_tool_creates_item(self):
        """DrawCustomPolygonTool should create a CustomPolygonItem on finish."""
        self.canvas.push_command.reset_mock()
        tool = DrawCustomPolygonTool(self.canvas)

        for x in [0, 10, 20]:
            ctx = self.create_context(QPointF(x, 0))
            tool.on_mouse_press(ctx)
            tool.on_mouse_release(ctx)

        ctx_finish = self.create_context(QPointF(0, 10), buttons=Qt.MouseButton.RightButton)

        with unittest.mock.patch('src.gui.custom_polygon_type_popup.CustomPolygonTypePopup') as MockPopup:
            mock_popup = MagicMock()
            MockPopup.return_value = mock_popup
            mock_popup.exec.return_value = True
            mock_popup.get_selected_type.return_value = "clean_zone"
            tool.on_mouse_press(ctx_finish)

        self.assertEqual(self.canvas.push_command.call_count, 1)
        cmd = self.canvas.push_command.call_args[0][0]
        self.assertIsInstance(cmd, AddItemCommand)
        # Verify a CustomPolygonItem is in the items list
        polygon_items = [i for i in cmd.items if isinstance(i, CustomPolygonItem)]
        self.assertEqual(len(polygon_items), 1)
        self.assertEqual(polygon_items[0].polygon_type, "clean_zone")

    def test_draw_object_tool_creates_item(self):
        """DrawObjectTool should create an ObjectItem after drag."""
        self.canvas.push_command.reset_mock()
        tool = DrawObjectTool(self.canvas)

        press_ctx = self.create_context(QPointF(0, 0))
        tool.on_mouse_press(press_ctx)

        move_ctx = self.create_context(QPointF(5, 5))
        tool.on_mouse_move(move_ctx)

        release_ctx = self.create_context(QPointF(5, 5))

        with unittest.mock.patch('src.gui.object_type_popup.ObjectTypePopup') as MockPopup:
            mock_popup = MagicMock()
            MockPopup.return_value = mock_popup
            mock_popup.exec.return_value = True
            mock_popup.get_selected_type.return_value = "furniture"
            tool.on_mouse_release(release_ctx)

        self.assertEqual(self.canvas.push_command.call_count, 1)
        cmd = self.canvas.push_command.call_args[0][0]
        self.assertIsInstance(cmd, AddItemCommand)
        obj_items = [i for i in cmd.items if isinstance(i, ObjectItem)]
        self.assertEqual(len(obj_items), 1)
        self.assertEqual(obj_items[0].object_type, "furniture")

    def test_draw_object_tool_cleanup(self):
        """DrawObjectTool.cleanup() should remove preview and reset state."""
        tool = DrawObjectTool(self.canvas)
        press_ctx = self.create_context(QPointF(0, 0))
        tool.on_mouse_press(press_ctx)
        self.assertIsNotNone(tool._preview_item)

        tool.cleanup()

        self.assertIsNone(tool._preview_item)
        self.assertEqual(tool._state, DrawObjectTool.IDLE)


class TestSelectToolCycling(unittest.TestCase):
    """Tests for SelectTool click-cycling through overlapping items."""

    def setUp(self):
        self.canvas = MockCanvas()

    def create_context(self, scene_pos, buttons=Qt.MouseButton.LeftButton):
        return InputContext(
            scene_pos=scene_pos,
            screen_pos=QPoint(int(scene_pos.x()), int(scene_pos.y())),
            buttons=buttons
        )

    def _make_room_at_origin(self):
        """Create a RoomItem covering the origin area."""
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        for n in nodes:
            self.canvas.scene.addItem(n)
        room = RoomItem(nodes, room_type="living_room", room_id="r0")
        self.canvas.scene.addItem(room)
        return room

    def _make_object_at_origin(self):
        """Create an ObjectItem covering the origin area."""
        obj = ObjectItem(
            center=QPointF(5, 5), width=10, height=10, angle=0,
            object_type="table", object_id="o0"
        )
        self.canvas.scene.addItem(obj)
        return obj

    def test_select_cycle_single_item(self):
        """Single item at click point — no cycling, normal select."""
        tool = SelectTool(self.canvas)
        obj = self._make_object_at_origin()

        self.canvas.scene.items = MagicMock(return_value=[obj])
        ctx = self.create_context(QPointF(5, 5))
        tool.on_mouse_press(ctx)

        self.assertTrue(obj.isSelected())
        self.assertEqual(len(tool._cycle_items), 1)

    def test_select_cycle_overlapping_items(self):
        """Repeated clicks at same position cycle through overlapping items."""
        tool = SelectTool(self.canvas)
        room = self._make_room_at_origin()
        obj = self._make_object_at_origin()

        # scene.items returns highest z first: ObjectItem(z=45), RoomItem(z=40)
        self.canvas.scene.items = MagicMock(return_value=[obj, room])

        pos = QPointF(5, 5)

        # First click — ObjectItem selected (topmost)
        tool.on_mouse_press(self.create_context(pos))
        self.assertTrue(obj.isSelected())
        self.assertFalse(room.isSelected())

        # Second click same position — RoomItem selected
        tool.on_mouse_press(self.create_context(pos))
        self.assertFalse(obj.isSelected())
        self.assertTrue(room.isSelected())

        # Third click — wraps back to ObjectItem
        tool.on_mouse_press(self.create_context(pos))
        self.assertTrue(obj.isSelected())
        self.assertFalse(room.isSelected())

    def test_select_cycle_resets_on_different_position(self):
        """Clicking a different position resets the cycle."""
        tool = SelectTool(self.canvas)
        room = self._make_room_at_origin()
        obj = self._make_object_at_origin()

        self.canvas.scene.items = MagicMock(return_value=[obj, room])

        # Click at (5,5) — select obj
        tool.on_mouse_press(self.create_context(QPointF(5, 5)))
        self.assertTrue(obj.isSelected())

        # Click at far position — cycle should reset
        self.canvas.scene.items = MagicMock(return_value=[room])
        tool.on_mouse_press(self.create_context(QPointF(100, 100)))
        self.assertTrue(room.isSelected())
        self.assertEqual(tool._cycle_index, 0)

    def test_select_cycle_node_priority(self):
        """NodeItem at click point takes priority over cycling."""
        tool = SelectTool(self.canvas)
        node = NodeItem(5, 5)
        self.canvas.scene.addItem(node)
        obj = self._make_object_at_origin()

        # Node is at top (z=100), then ObjectItem
        self.canvas.scene.items = MagicMock(return_value=[node, obj])

        tool.on_mouse_press(self.create_context(QPointF(5, 5)))
        self.assertEqual(tool.moving_item, node)
        self.assertEqual(len(tool._cycle_items), 0)

    def test_select_cycle_cleanup(self):
        """SelectTool.cleanup() resets cycle state."""
        tool = SelectTool(self.canvas)
        obj = self._make_object_at_origin()

        self.canvas.scene.items = MagicMock(return_value=[obj])
        tool.on_mouse_press(self.create_context(QPointF(5, 5)))
        self.assertEqual(len(tool._cycle_items), 1)

        tool.cleanup()
        self.assertEqual(len(tool._cycle_items), 0)
        self.assertIsNone(tool._last_click_scene_pos)
        self.assertIsNone(tool.moving_item)


class TestPolygonItemDrawingGuard(unittest.TestCase):
    """Tests for PolygonItem _is_drawing_tool_active() guard."""

    def setUp(self):
        self.canvas = MockCanvas()

    def _make_room_with_view(self):
        """Create a RoomItem attached to a scene with a mock view."""
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        for n in nodes:
            self.canvas.scene.addItem(n)
        room = RoomItem(nodes, room_type="living_room", room_id="r0")
        self.canvas.scene.addItem(room)
        return room

    def test_polygon_item_ignores_events_during_drawing_tool(self):
        """PolygonItem should report drawing tool active when allows_item_events=False."""
        room = self._make_room_with_view()

        # Use spec=[] to prevent MagicMock from auto-creating _passthrough attr
        mock_tool = MagicMock(spec=[])
        mock_tool.allows_item_events = False

        mock_view = MagicMock(spec=[])
        mock_view.current_tool = mock_tool

        with unittest.mock.patch.object(
            room.scene(), 'views', return_value=[mock_view]
        ):
            self.assertTrue(room._is_drawing_tool_active())

    def test_polygon_item_accepts_events_during_select_tool(self):
        """PolygonItem should report drawing tool NOT active when allows_item_events=True."""
        room = self._make_room_with_view()

        mock_tool = MagicMock(spec=[])
        mock_tool.allows_item_events = True

        mock_view = MagicMock(spec=[])
        mock_view.current_tool = mock_tool

        with unittest.mock.patch.object(
            room.scene(), 'views', return_value=[mock_view]
        ):
            self.assertFalse(room._is_drawing_tool_active())


if __name__ == "__main__":
    unittest.main()
