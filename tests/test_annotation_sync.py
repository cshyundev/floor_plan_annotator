import unittest
from unittest.mock import MagicMock, call

from src.core.annotation_sync import AnnotationSync3D


class TestAnnotationSyncVisibility(unittest.TestCase):
    """Tests for category visibility toggling in AnnotationSync3D."""

    def setUp(self):
        self.viewer = MagicMock()
        self.processor = MagicMock()
        self.config = MagicMock()
        self.sync = AnnotationSync3D(self.viewer, self.processor, self.config)

    def test_initial_hidden_categories_empty(self):
        """All categories should be visible by default."""
        self.assertEqual(self.sync._hidden_categories, set())

    def test_hide_room_category(self):
        """Hiding room category should remove all room geometries from viewer."""
        mesh1 = MagicMock()
        mesh2 = MagicMock()
        self.sync.room_geometries = {"r1": mesh1, "r2": mesh2}

        self.sync.set_category_visibility("room", False)

        self.assertIn("room", self.sync._hidden_categories)
        self.viewer.remove_room_geometry.assert_any_call("r1")
        self.viewer.remove_room_geometry.assert_any_call("r2")

    def test_show_room_category(self):
        """Showing hidden room category should re-add all room geometries to viewer."""
        mesh1 = MagicMock()
        self.sync.room_geometries = {"r1": mesh1}
        self.sync._hidden_categories.add("room")

        self.sync.set_category_visibility("room", True)

        self.assertNotIn("room", self.sync._hidden_categories)
        self.viewer.add_room_geometry.assert_called_with("r1", mesh1)

    def test_hide_wall_category(self):
        """Hiding wall category should remove all wall geometries from viewer."""
        mesh = MagicMock()
        self.sync.wall_geometries = {"w1": mesh}

        self.sync.set_category_visibility("wall", False)

        self.assertIn("wall", self.sync._hidden_categories)
        self.viewer.remove_wall_geometry.assert_called_with("w1")

    def test_hide_custom_polygon_category(self):
        """Hiding custom_polygon category should remove geometries from viewer."""
        mesh = MagicMock()
        self.sync.custom_polygon_geometries = {"cp1": mesh}

        self.sync.set_category_visibility("custom_polygon", False)

        self.assertIn("custom_polygon", self.sync._hidden_categories)
        self.viewer.remove_custom_polygon_geometry.assert_called_with("cp1")

    def test_hide_object_category(self):
        """Hiding object category should remove geometries from viewer."""
        mesh = MagicMock()
        self.sync.object_geometries = {"o1": mesh}

        self.sync.set_category_visibility("object", False)

        self.assertIn("object", self.sync._hidden_categories)
        self.viewer.remove_object_geometry.assert_called_with("o1")

    def test_hidden_category_skips_viewer_add_on_sync(self):
        """When room category is hidden, sync_room_annotation should store mesh but not add to viewer."""
        self.sync._hidden_categories.add("room")
        self.config.get_ui_value.return_value = True

        room_item = MagicMock()
        room_item.nodes = [MagicMock(), MagicMock(), MagicMock()]
        for i, node in enumerate(room_item.nodes):
            node.pos.return_value = MagicMock(x=lambda i=i: float(i), y=lambda i=i: float(i))
        room_item.room_type = "living_room"
        room_item.room_id = "test_1"

        room_type_conf = {"color": [200, 200, 200, 100]}
        self.config.get_room_type.return_value = room_type_conf

        self.sync.sync_room_annotation(room_item)

        # Geometry should be stored
        self.assertIn("test_1", self.sync.room_geometries)
        # But NOT added to viewer
        self.viewer.add_room_geometry.assert_not_called()


if __name__ == "__main__":
    unittest.main()
