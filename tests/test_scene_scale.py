"""Tests for scene coordinate scale (meter-based sizing)."""

import pytest
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from src.gui.items import NodeItem, EdgeItem, RoomItem


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    """Create a QGraphicsScene for tests."""
    return QGraphicsScene()


class TestNodeItemScale:
    """Test NodeItem meter-scale sizing."""

    def test_node_default_radius(self, scene):
        """Test that NodeItem has correct default radius (meters)."""
        node = NodeItem(0, 0)
        scene.addItem(node)

        # Default radius should be 0.05 meters (5cm)
        rect = node.rect()
        radius = rect.width() / 2
        assert 0.04 <= radius <= 0.06, f"Node radius {radius} not in range [0.04, 0.06]"

    def test_node_pen_width(self, scene):
        """Test that NodeItem has correct pen width (meters)."""
        node = NodeItem(0, 0)
        scene.addItem(node)

        pen_width = node.pen().widthF()
        # Default pen width should be 0.01 meters (1cm)
        assert 0.005 <= pen_width <= 0.015, f"Node pen width {pen_width} not in range [0.005, 0.015]"

    def test_node_custom_radius(self, scene):
        """Test NodeItem with custom radius."""
        custom_radius = 0.1
        node = NodeItem(5, 5, radius=custom_radius)
        scene.addItem(node)

        rect = node.rect()
        radius = rect.width() / 2
        assert abs(radius - custom_radius) < 0.01

    def test_node_position(self, scene):
        """Test NodeItem position in scene coordinates."""
        x, y = 10.5, 20.3
        node = NodeItem(x, y)
        scene.addItem(node)

        pos = node.pos()
        assert abs(pos.x() - x) < 0.01
        assert abs(pos.y() - y) < 0.01


class TestEdgeItemScale:
    """Test EdgeItem meter-scale sizing."""

    def test_edge_default_width(self, scene):
        """Test that EdgeItem has correct default width (meters)."""
        node1 = NodeItem(0, 0)
        node2 = NodeItem(10, 0)
        scene.addItem(node1)
        scene.addItem(node2)

        edge = EdgeItem(node1, node2)
        scene.addItem(edge)

        pen_width = edge.pen().widthF()
        # Default wall width should be 0.02 meters (2cm)
        assert 0.015 <= pen_width <= 0.025, f"Edge width {pen_width} not in range [0.015, 0.025]"

    def test_edge_selected_width(self, scene):
        """Test that selected EdgeItem has correct width."""
        node1 = NodeItem(0, 0)
        node2 = NodeItem(10, 0)
        scene.addItem(node1)
        scene.addItem(node2)

        edge = EdgeItem(node1, node2)
        scene.addItem(edge)

        edge.setSelected(True)
        # Selected width should be slightly larger (0.03 meters)
        selected_width = edge.pen_selected.widthF()
        assert 0.025 <= selected_width <= 0.035, f"Selected edge width {selected_width} not in range [0.025, 0.035]"

    def test_edge_updates_with_nodes(self, scene):
        """Test that edge updates when nodes move."""
        node1 = NodeItem(0, 0)
        node2 = NodeItem(10, 0)
        scene.addItem(node1)
        scene.addItem(node2)

        edge = EdgeItem(node1, node2)
        scene.addItem(edge)

        initial_line = edge.line()
        assert abs(initial_line.length() - 10.0) < 0.1

        # Move node2
        node2.setPos(20, 0)
        updated_line = edge.line()
        assert abs(updated_line.length() - 20.0) < 0.1


class TestRoomItemScale:
    """Test RoomItem meter-scale sizing."""

    def test_room_edge_width(self, scene):
        """Test that RoomItem has correct edge width (meters)."""
        nodes = [
            NodeItem(0, 0),
            NodeItem(10, 0),
            NodeItem(10, 10),
            NodeItem(0, 10)
        ]
        for node in nodes:
            scene.addItem(node)

        room = RoomItem(nodes)
        scene.addItem(room)

        pen_width = room.pen().widthF()
        # Room edge width should be 0.02 meters (2cm)
        assert 0.015 <= pen_width <= 0.025, f"Room edge width {pen_width} not in range [0.015, 0.025]"

    def test_room_rotation_handle_size(self, scene):
        """Test that rotation handle has correct size (meters)."""
        nodes = [
            NodeItem(0, 0),
            NodeItem(10, 0),
            NodeItem(10, 10),
            NodeItem(0, 10)
        ]
        for node in nodes:
            scene.addItem(node)

        room = RoomItem(nodes)
        scene.addItem(room)

        handle_rect = room.rotation_handle.rect()
        handle_size = handle_rect.width()
        # Handle size should be 0.1 meters (10cm)
        assert 0.08 <= handle_size <= 0.12, f"Rotation handle size {handle_size} not in range [0.08, 0.12]"

    def test_room_centroid_calculation(self, scene):
        """Test that room centroid is calculated correctly."""
        nodes = [
            NodeItem(0, 0),
            NodeItem(10, 0),
            NodeItem(10, 10),
            NodeItem(0, 10)
        ]
        for node in nodes:
            scene.addItem(node)

        room = RoomItem(nodes)
        scene.addItem(room)

        centroid = room._centroid
        # Centroid of square should be at (5, 5)
        assert abs(centroid.x() - 5.0) < 0.1
        assert abs(centroid.y() - 5.0) < 0.1

    def test_room_updates_with_nodes(self, scene):
        """Test that room updates when nodes move."""
        nodes = [
            NodeItem(0, 0),
            NodeItem(10, 0),
            NodeItem(10, 10),
            NodeItem(0, 10)
        ]
        for node in nodes:
            scene.addItem(node)

        room = RoomItem(nodes)
        scene.addItem(room)

        initial_centroid = room._centroid

        # Move all nodes
        for node in nodes:
            node.setPos(node.pos().x() + 5, node.pos().y() + 5)

        # Centroid should have moved by (5, 5)
        assert abs(room._centroid.x() - initial_centroid.x() - 5.0) < 0.1
        assert abs(room._centroid.y() - initial_centroid.y() - 5.0) < 0.1

    def test_room_label_scale(self, scene):
        """Test that room label has appropriate scale for scene coordinates."""
        nodes = [
            NodeItem(0, 0),
            NodeItem(10, 0),
            NodeItem(10, 10),
            NodeItem(0, 10)
        ]
        for node in nodes:
            scene.addItem(node)

        room = RoomItem(nodes)
        scene.addItem(room)

        label_scale = room.label.scale()
        # Label should be very small (< 0.1) to match meter-scale scene
        assert 0.001 <= label_scale <= 0.1, f"Label scale {label_scale} not in range [0.001, 0.1]"


class TestConfigFallbackValues:
    """Test that fallback values are correct when config is missing."""

    def test_node_fallback_values(self, scene):
        """Test NodeItem fallback values are in meter scale."""
        # Even without config, fallback should be meter-scale
        node = NodeItem(0, 0)
        rect = node.rect()
        radius = rect.width() / 2

        # Fallback radius should be small (meter scale, not pixel scale)
        assert radius < 1.0, f"Fallback radius {radius} too large (should be < 1.0 meter)"
        assert radius > 0.01, f"Fallback radius {radius} too small (should be > 0.01 meter)"

    def test_edge_fallback_values(self, scene):
        """Test EdgeItem fallback values are in meter scale."""
        node1 = NodeItem(0, 0)
        node2 = NodeItem(10, 0)
        scene.addItem(node1)
        scene.addItem(node2)

        edge = EdgeItem(node1, node2)
        pen_width = edge.pen().widthF()

        # Fallback width should be small (meter scale)
        assert pen_width < 0.5, f"Fallback width {pen_width} too large (should be < 0.5 meter)"
        assert pen_width > 0.001, f"Fallback width {pen_width} too small (should be > 0.001 meter)"
