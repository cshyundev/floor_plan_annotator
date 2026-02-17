import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt, QPoint
from PyQt6.QtGui import QColor, QBrush, QPen
import sys

if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.items import NodeItem, EdgeItem, RoomItem
from src.core.config import ConfigManager

class TestItemsExtended(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager.instance()
        
    def test_node_item_hover(self):
        node = NodeItem(0, 0)
        initial_scale = node.scale()
        
        # Patch super().hoverEnterEvent to avoid C++ instantiation issues
        with patch('PyQt6.QtWidgets.QGraphicsEllipseItem.hoverEnterEvent'):
            # Simulate hover enter
            # We can use a bare MagicMock now since super() is patched
            event = MagicMock()
            node.hoverEnterEvent(event)
            self.assertNotEqual(node.scale(), initial_scale)
            
            # Simulate hover leave
            with patch('PyQt6.QtWidgets.QGraphicsEllipseItem.hoverLeaveEvent'):
                node.hoverLeaveEvent(event)
                self.assertEqual(node.scale(), initial_scale)

    def test_edge_update(self):
        n1 = NodeItem(0, 0)
        n2 = NodeItem(10, 0)
        edge = EdgeItem(n1, n2)
        
        line = edge.line()
        self.assertEqual(line.p1(), QPointF(0, 0))
        self.assertEqual(line.p2(), QPointF(10, 0))
        
        # Move node
        n1.setPos(0, 5)
        edge.update_line()
        self.assertEqual(edge.line().p1(), QPointF(0, 5))

    def test_room_item_style(self):
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room")
        
        brush = room.brush()
        
        room.room_type = "kitchen"
        room.update_style()
        
        path = room.path()
        self.assertFalse(path.isEmpty())
        
    def test_room_context_menu(self):
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room")
        
        # Mock QMenu
        with patch('PyQt6.QtWidgets.QMenu') as MockMenu:
            menu_instance = MockMenu.return_value
            
            # Setup actions
            # contextMenuEvent calls menu.addAction(name). return QAction.
            # We need to capture these actions so we can return one of them from exec.
            
            actions = {} # name -> mock_action
            
            def add_action_side_effect(name):
                a = MagicMock()
                a.text.return_value = name
                actions[name] = a
                return a
            
            menu_instance.addAction.side_effect = add_action_side_effect
            
            # Mock ConfigManager
            with patch.object(self.config, 'get_room_types', return_value={
                "living_room": {"name": "Living Room", "color": "red"},
                "kitchen": {"name": "Kitchen", "color": "blue"}
            }):
                 # Setup Scen and View
                 from PyQt6.QtWidgets import QGraphicsScene
                 real_scene = QGraphicsScene()
                 real_scene.addItem(room)
                 
                 view = MagicMock()
                 with patch.object(real_scene, 'views', return_value=[view]):
                     # Trigger
                     
                     # Check logic:
                     # It iterates sorted keys.
                     # "kitchen" (Kitchen), "living_room" (Living Room).
                     
                     # We want to select "Kitchen".
                     # So exec should return the action corresponding to "Kitchen".
                     
                     # However, addAction side effect happens DURING execution of contextMenuEvent.
                     # So we can't pre-populate return_value of exec with the EXACT object returned by addAction unless...
                     # we use a known object.
                     
                     kitchen_action = MagicMock()
                     kitchen_action.text.return_value = "Kitchen"
                     
                     # Override side effect to strict mapping if needed, or just return kitchen_action when "Kitchen" is passed
                     def custom_add_action(name):
                         if name == "Kitchen":
                             return kitchen_action
                         return MagicMock()
                     
                     menu_instance.addAction.side_effect = custom_add_action
                     menu_instance.exec.return_value = kitchen_action
                     
                     event = MagicMock()
                     event.screenPos.return_value = QPointF(0, 0)
                     
                     room.contextMenuEvent(event)
                     
                     # Manually trigger the callback
                     # access connect call
                     # kitchen_action.triggered.connect(callback)
                     # verify connect was called
                     self.assertTrue(kitchen_action.triggered.connect.called)
                     callback = kitchen_action.triggered.connect.call_args[0][0]
                     callback()
                     
                     view.push_command.assert_called()
                     # Verify command type?
                     cmd = view.push_command.call_args[0][0]
                     self.assertIn("Change Room Type", cmd.text())

    def test_room_rotation(self):
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room")
        
        # Determine centroid manually
        xs = [n.pos().x() for n in nodes]
        ys = [n.pos().y() for n in nodes]
        c = QPointF(sum(xs)/len(xs), sum(ys)/len(ys))
        # Mock event for rotation
        # mouseMoveEvent with _rotating = True
        
        room._rotating = True
        room._centroid = c
        import math
        # initial angle
        # In mousePress, it calculates initial angle from press pos.
        # Let's say we pressed at (10, 5) relative to centroid?
        # Let's simulate valid state manually.
        room._initial_angle = 0.0
        room._initial_node_positions = [n.pos() for n in nodes]
        
        # Move mouse to 90 degrees (0, 1) direction from centroid?
        # Centroid of (0,0), (10,0), (10,10) is (6.66, 3.33) roughly.
        
        event = MagicMock()
        # New pos that forms 90 degrees diff?
        # Just ensure loop runs.
        event.scenePos.return_value = QPointF(c.x(), c.y() + 10) 
        
        room.mouseMoveEvent(event)
        
        # Nodes should have moved
        # Just check one node moved
        self.assertNotEqual(nodes[0].pos(), QPointF(0, 0))

if __name__ == "__main__":
    unittest.main()
