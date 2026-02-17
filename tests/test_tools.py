
import unittest
from unittest.mock import MagicMock, call
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtCore import QPointF, Qt, QPoint
import sys

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.core.input_context import InputContext
from src.gui.tools import SelectTool, DrawWallTool, DrawRoomTool
from src.gui.items import NodeItem, RoomItem
from src.core.undo_commands import AddItemCommand, MoveNodeCommand

class MockCanvas:
    def __init__(self):
        self.scene = QGraphicsScene()
        self.background_item = None
        self.status_message = MagicMock()
        self.push_command = MagicMock()
        self._next_room_id = 0

    def transform(self):
        return MagicMock()

    def set_tool(self, tool_name):
        pass

    def next_room_id(self):
        rid = self._next_room_id
        self._next_room_id += 1
        return str(rid)

class TestTools(unittest.TestCase):
    def setUp(self):
        self.canvas = MockCanvas()
        
    def create_context(self, scene_pos, buttons=Qt.MouseButton.LeftButton):
        # We need to make sure buttons are set correctly for tools that check them.
        # DrawRectTool checks for LeftButton in mouseMove/Release?
        # Actually standard practice is press sets button, move/release might typically track buttons.
        return InputContext(
            scene_pos=scene_pos,
            screen_pos=QPoint(int(scene_pos.x()), int(scene_pos.y())),
            buttons=buttons
        )

    def test_select_tool_move(self):
        tool = SelectTool(self.canvas)
        
        # Add a node
        node = NodeItem(0, 0)
        self.canvas.scene.addItem(node)
        
        # We can patch scene.items directly on the instance
        # Note: In PyQt/PySide some methods are not easily monkeypatched on instance if they are C++ slots
        # But usually straightforward assignment works for python access.
        
        # Force items return
        # scene.items(pos) needs to return list
        self.canvas.scene.items = unittest.mock.MagicMock(return_value=[node])
            
        # Select (Press)
        ctx_press = self.create_context(QPointF(0, 0))
        tool.on_mouse_press(ctx_press)
        
        # Verify selection
        # Note: SelectTool might employ specific logic interacting with QGraphicsScene
        # In a mock environment without full event loop, selection logic relies on item.setSelected
        # We assume tool calls item.setSelected(True)
        # But we verify internal state 'moving_item'
        
        self.assertEqual(tool.moving_item, node)
        
        # Move (Release at different pos)
        ctx_release = self.create_context(QPointF(100, 100))
        
        # Simulate manual move since no event loop
        node.setPos(100, 100) 
        tool.on_mouse_release(ctx_release)
    
        # Verify Command Pushed
        # If start_pos != end_pos, it should push command.
        self.assertEqual(self.canvas.push_command.call_count, 1)

    def test_room_tool_create(self):
        self.canvas.push_command.reset_mock() # Reset count
        tool = DrawRoomTool(self.canvas)
        
        # Add Point 1 (Click)
        ctx1 = self.create_context(QPointF(0, 0))
        tool.on_mouse_press(ctx1)
        
        # Add Point 2
        ctx2 = self.create_context(QPointF(10, 0))
        tool.on_mouse_press(ctx2)
        
        # Add Point 3
        ctx3 = self.create_context(QPointF(10, 10))
        tool.on_mouse_press(ctx3)
        
        # Finish (Right Click)
        # MouseRelease or MousePress? DrawRoomTool uses RightButton MouseRelease or MousePress?
        # Looking at code (Step 22): "elif context.buttons == Qt.MouseButton.RightButton:" in on_mouse_press
        # Wait, if on_mouse_press catches RightButton, that's fine.
        
        ctx_finish = self.create_context(QPointF(0, 10), buttons=Qt.MouseButton.RightButton)
        
        # Patch RoomTypePopup to return a valid type without UI
        mock_popup = MagicMock()
        mock_popup.exec.return_value = True
        mock_popup.get_selected_type.return_value = "living_room"
        with unittest.mock.patch('src.gui.room_type_popup.RoomTypePopup', return_value=mock_popup):
            tool.on_mouse_press(ctx_finish)
             
        # Verify Command Pushed (Add Room)
        # Logic: 3 points added, right click finishes.
        
        self.assertEqual(self.canvas.push_command.call_count, 1)
        cmd = self.canvas.push_command.call_args[0][0]
        self.assertIsInstance(cmd, AddItemCommand)

if __name__ == "__main__":
    unittest.main()
