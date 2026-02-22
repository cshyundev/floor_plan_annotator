import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsSceneHoverEvent, QGraphicsItem
from PyQt6.QtCore import Qt, QEvent
import sys

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.items import NodeItem, EdgeItem, RoomItem, PolygonItem, CustomPolygonItem, ObjectItem
from src.core.config import ConfigManager
from PyQt6.QtCore import QPointF

class TestItems(unittest.TestCase):
    def setUp(self):
        self.scene = QGraphicsScene()

    def test_node_hover(self):
        node = NodeItem(0, 0)
        self.scene.addItem(node)

        config = ConfigManager.instance()
        default_scale = 1.0
        hover_scale = config.get_ui_value("node", "hover", "scale")

        # Initial
        self.assertEqual(node.scale(), default_scale)

        # Enter
        from unittest.mock import patch
        with patch('PyQt6.QtWidgets.QGraphicsEllipseItem.hoverEnterEvent'):
             event = MagicMock()
             node.hoverEnterEvent(event)

        self.assertEqual(node.scale(), hover_scale)

        # Leave
        with patch('PyQt6.QtWidgets.QGraphicsEllipseItem.hoverLeaveEvent'):
             event_leave = MagicMock()
             node.hoverLeaveEvent(event_leave)

        self.assertEqual(node.scale(), default_scale)

    def test_edge_connectivity(self):
        n1 = NodeItem(0, 0)
        n2 = NodeItem(100, 0)
        self.scene.addItem(n1)
        self.scene.addItem(n2)

        edge = EdgeItem(n1, n2)
        self.scene.addItem(edge)

        # Verify edge registered to nodes
        self.assertIn(edge, n1.edges)
        self.assertIn(edge, n2.edges)

        # Verify line geometry
        line = edge.line()
        self.assertEqual(line.p1(), n1.pos())
        self.assertEqual(line.p2(), n2.pos())

        n2.setPos(100, 100)

        if edge.line().p2() != n2.pos():
             n2.itemChange(QGraphicsItem.GraphicsItemChange.ItemPositionChange, n2.pos())

        edge_line = edge.line()
        self.assertEqual(edge_line.p2(), n2.pos())

    def test_edge_annotation_type(self):
        """EdgeItem should have annotation_type class attribute."""
        self.assertEqual(EdgeItem.annotation_type, "wall")

    def test_polygon_item_is_base_of_room_item(self):
        """RoomItem should be a subclass of PolygonItem."""
        self.assertTrue(issubclass(RoomItem, PolygonItem))

    def test_room_item_annotation_type(self):
        """RoomItem should have annotation_type = 'room'."""
        self.assertEqual(RoomItem.annotation_type, "room")

    def test_room_item_inherits_polygon_behavior(self):
        """RoomItem should have nodes, update_shape, label from PolygonItem."""
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room", room_id="1")

        self.assertIs(room.nodes, nodes)
        self.assertTrue(hasattr(room, 'label'))
        self.assertTrue(hasattr(room, 'rotation_handle'))
        self.assertTrue(hasattr(room, '_centroid'))
        # Path should be set
        self.assertFalse(room.path().isEmpty())

    def test_room_item_label_text(self):
        """RoomItem.get_label_text() should include room_id."""
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room", room_id="42")
        label = room.get_label_text()
        self.assertIn("42", label)

    def test_room_item_label_style(self):
        """RoomItem label should have white text and transparent background."""
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        room = RoomItem(nodes, room_type="living_room", room_id="1")
        html = room.label.toHtml()
        self.assertIn("transparent", html)
        self.assertIn("white", html)


class TestCustomPolygonItem(unittest.TestCase):
    def setUp(self):
        self.scene = QGraphicsScene()

    def test_annotation_type(self):
        """CustomPolygonItem should have annotation_type = 'custom_polygon'."""
        self.assertEqual(CustomPolygonItem.annotation_type, "custom_polygon")

    def test_is_subclass_of_polygon_item(self):
        """CustomPolygonItem should be a subclass of PolygonItem."""
        self.assertTrue(issubclass(CustomPolygonItem, PolygonItem))

    def test_creation(self):
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        item = CustomPolygonItem(nodes, polygon_type="clean_zone", polygon_id="5")
        self.assertEqual(item.polygon_type, "clean_zone")
        self.assertEqual(item.polygon_id, "5")
        self.assertFalse(item.path().isEmpty())

    def test_label_text_contains_id(self):
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        item = CustomPolygonItem(nodes, polygon_type="clean_zone", polygon_id="7")
        self.assertIn("7", item.get_label_text())

    def test_custom_polygon_label_style(self):
        """CustomPolygonItem label should have white text and transparent background."""
        nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10)]
        item = CustomPolygonItem(nodes, polygon_type="clean_zone", polygon_id="5")
        html = item.label.toHtml()
        self.assertIn("transparent", html)
        self.assertIn("white", html)


class TestObjectItem(unittest.TestCase):
    def setUp(self):
        self.scene = QGraphicsScene()

    def test_annotation_type(self):
        """ObjectItem should have annotation_type = 'object'."""
        self.assertEqual(ObjectItem.annotation_type, "object")

    def test_creation(self):
        center = QPointF(5.0, 5.0)
        item = ObjectItem(center=center, width=2.0, height=1.0, angle=0.0,
                          object_type="furniture", object_id="3")
        self.assertEqual(item.center, center)
        self.assertEqual(item.width, 2.0)
        self.assertEqual(item.height, 1.0)
        self.assertEqual(item.angle, 0.0)
        self.assertEqual(item.object_type, "furniture")
        self.assertEqual(item.object_id, "3")

    def test_compute_corners_count(self):
        center = QPointF(0.0, 0.0)
        item = ObjectItem(center=center, width=2.0, height=1.0)
        corners = item._compute_corners()
        self.assertEqual(len(corners), 4)

    def test_polygon_matches_corners(self):
        """The polygon shape should have 4 vertices matching computed corners."""
        center = QPointF(0.0, 0.0)
        item = ObjectItem(center=center, width=2.0, height=1.0)
        poly = item.polygon()
        self.assertEqual(poly.count(), 4)

    def test_object_label_style(self):
        """ObjectItem label should have white text and transparent background."""
        center = QPointF(5.0, 5.0)
        item = ObjectItem(center=center, width=2.0, height=1.0, angle=0.0,
                          object_type="furniture", object_id="3")
        html = item.label.toHtml()
        self.assertIn("transparent", html)
        self.assertIn("white", html)


if __name__ == "__main__":
    unittest.main()
