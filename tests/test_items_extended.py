import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt, QPoint
from PyQt6.QtGui import QColor, QBrush, QPen
import sys

if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.items import NodeItem, EdgeItem, RoomItem, PolygonItem
from src.core.config import ConfigManager

class TestItemsExtended(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager.instance()

    def test_node_item_hover(self):
        node = NodeItem(0, 0)
        initial_scale = node.scale()

        with patch('PyQt6.QtWidgets.QGraphicsEllipseItem.hoverEnterEvent'):
            event = MagicMock()
            node.hoverEnterEvent(event)
            self.assertNotEqual(node.scale(), initial_scale)

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

        n1.setPos(0, 5)
        edge.update_line()
        self.assertEqual(edge.line().p1(), QPointF(0, 5))

    def test_edge_annotation_type(self):
        """EdgeItem must carry annotation_type = 'wall'."""
        self.assertEqual(EdgeItem.annotation_type, "wall")
        # Also verify on an instance
        n1, n2 = NodeItem(0, 0), NodeItem(1, 0)
        edge = EdgeItem(n1, n2)
        self.assertEqual(edge.annotation_type, "wall")

    def test_room_annotation_type(self):
        """RoomItem must carry annotation_type = 'room'."""
        self.assertEqual(RoomItem.annotation_type, "room")
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room")
        self.assertEqual(room.annotation_type, "room")

    def test_polygon_item_base_annotation_type(self):
        """PolygonItem base class should have annotation_type = 'polygon'."""
        self.assertEqual(PolygonItem.annotation_type, "polygon")

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

        with patch('PyQt6.QtWidgets.QMenu') as MockMenu:
            menu_instance = MockMenu.return_value

            actions = {}

            def add_action_side_effect(name):
                a = MagicMock()
                a.text.return_value = name
                actions[name] = a
                return a

            menu_instance.addAction.side_effect = add_action_side_effect

            with patch.object(self.config, 'get_room_types', return_value={
                "living_room": {"name": "Living Room", "color": "red"},
                "kitchen": {"name": "Kitchen", "color": "blue"}
            }):
                 from PyQt6.QtWidgets import QGraphicsScene
                 real_scene = QGraphicsScene()
                 real_scene.addItem(room)

                 view = MagicMock()
                 with patch.object(real_scene, 'views', return_value=[view]):
                     kitchen_action = MagicMock()
                     kitchen_action.text.return_value = "Kitchen"

                     def custom_add_action(name):
                         if name == "Kitchen":
                             return kitchen_action
                         return MagicMock()

                     menu_instance.addAction.side_effect = custom_add_action
                     menu_instance.exec.return_value = kitchen_action

                     event = MagicMock()
                     event.screenPos.return_value = QPointF(0, 0)

                     room.contextMenuEvent(event)

                     self.assertTrue(kitchen_action.triggered.connect.called)
                     callback = kitchen_action.triggered.connect.call_args[0][0]
                     callback()

                     view.push_command.assert_called()
                     cmd = view.push_command.call_args[0][0]
                     self.assertIn("Change Room Type", cmd.text())

    def test_room_rotation(self):
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room")

        xs = [n.pos().x() for n in nodes]
        ys = [n.pos().y() for n in nodes]
        c = QPointF(sum(xs)/len(xs), sum(ys)/len(ys))

        room._rotating = True
        room._centroid = c
        import math
        room._initial_angle = 0.0
        room._initial_node_positions = [n.pos() for n in nodes]

        event = MagicMock()
        event.scenePos.return_value = QPointF(c.x(), c.y() + 10)

        room.mouseMoveEvent(event)

        self.assertNotEqual(nodes[0].pos(), QPointF(0, 0))

if __name__ == "__main__":
    unittest.main()
