import colorsys
import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import sys

if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.room_type_editor import RoomTypeEditorWidget
from src.gui.custom_polygon_type_editor import CustomPolygonTypeEditorWidget
from src.gui.object_type_editor import ObjectTypeEditorWidget
from src.core.config import ConfigManager


class TestRoomTypeEditor(unittest.TestCase):
    def setUp(self):
        self.editor = RoomTypeEditorWidget()

    def test_load_types_displays_name(self):
        """List items should show key (=name), with key stored in UserRole."""
        config = ConfigManager.instance()
        types = config.get_room_types()
        for i in range(self.editor.type_list.count()):
            item = self.editor.type_list.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            self.assertIn(key, types)
            self.assertEqual(item.text(), key)

    def test_on_item_clicked_sets_key_from_user_role(self):
        """Clicking an item should set current_key equal to display text (name=key)."""
        if self.editor.type_list.count() == 0:
            self.skipTest("No room types configured")
        item = self.editor.type_list.item(0)
        self.editor.on_item_clicked(item)
        expected_key = item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(self.editor.current_key, expected_key)
        self.assertEqual(self.editor.current_key, item.text())

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("Test Room", True))
    def test_add_type_with_dialog(self, mock_dialog):
        """Add button should create type with name as key."""
        config = ConfigManager.instance()
        # Ensure clean state
        if "Test Room" in config.get_room_types():
            config.delete_room_type("Test Room")
            self.editor.load_types()

        count_before = self.editor.type_list.count()
        types_before = set(config.get_room_types().keys())

        self.editor.add_type()

        self.assertEqual(self.editor.type_list.count(), count_before + 1)
        types_after = config.get_room_types()
        new_keys = set(types_after.keys()) - types_before
        self.assertEqual(len(new_keys), 1)
        new_key = new_keys.pop()
        self.assertEqual(new_key, "Test Room")

        # Clean up
        config.delete_room_type(new_key)

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("", False))
    def test_add_type_cancel_does_nothing(self, mock_dialog):
        """Cancelling the dialog should not create a type."""
        count_before = self.editor.type_list.count()
        self.editor.add_type()
        self.assertEqual(self.editor.type_list.count(), count_before)

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("   ", True))
    def test_add_type_empty_name_does_nothing(self, mock_dialog):
        """Empty/whitespace-only name should not create a type."""
        count_before = self.editor.type_list.count()
        self.editor.add_type()
        self.assertEqual(self.editor.type_list.count(), count_before)

    def test_on_name_finished_renames_type(self):
        """Finishing name edit should rename the type (key changes)."""
        if self.editor.type_list.count() == 0:
            self.skipTest("No room types configured")
        item = self.editor.type_list.item(0)
        self.editor.type_list.setCurrentItem(item)
        self.editor.on_item_clicked(item)

        original_key = self.editor.current_key
        new_name = "Renamed Room Test"
        self.editor.name_edit.setText(new_name)
        self.editor.on_name_finished()
        self.assertEqual(self.editor.current_key, new_name)
        self.assertEqual(item.text(), new_name)

        # Restore
        self.editor.name_edit.setText(original_key)
        self.editor.on_name_finished()
        self.assertEqual(self.editor.current_key, original_key)

    def test_generate_unique_color_avoids_existing(self):
        """Generated color hue should differ from all existing hues by at least min_hue_dist."""
        fill, border = self.editor._generate_unique_color()
        r, g, b = fill[0] / 255, fill[1] / 255, fill[2] / 255
        new_hue, _, _ = colorsys.rgb_to_hsv(r, g, b)

        config = ConfigManager.instance()
        types = config.get_room_types()
        min_hue_dist = 0.07
        for data in types.values():
            c = data.get("color", [128, 128, 128, 100])
            er, eg, eb = c[0] / 255, c[1] / 255, c[2] / 255
            eh, _, _ = colorsys.rgb_to_hsv(er, eg, eb)
            dist = min(abs(new_hue - eh), 1 - abs(new_hue - eh))
            self.assertGreaterEqual(dist, min_hue_dist,
                f"New hue {new_hue:.3f} too close to existing hue {eh:.3f} (dist={dist:.3f})")

    def test_generate_unique_color_valid_format(self):
        """Fill should be [R,G,B,A] and border should be [R,G,B], all in 0-255."""
        fill, border = self.editor._generate_unique_color()
        self.assertEqual(len(fill), 4)
        self.assertEqual(len(border), 3)
        for v in fill + border:
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 255)


class TestCustomPolygonTypeEditor(unittest.TestCase):
    def setUp(self):
        self.editor = CustomPolygonTypeEditorWidget()

    def test_load_types_displays_name(self):
        config = ConfigManager.instance()
        types = config.get_custom_polygon_types()
        for i in range(self.editor.type_list.count()):
            item = self.editor.type_list.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            self.assertIn(key, types)
            self.assertEqual(item.text(), key)

    def test_on_item_clicked_sets_key_from_user_role(self):
        if self.editor.type_list.count() == 0:
            self.skipTest("No custom polygon types configured")
        item = self.editor.type_list.item(0)
        self.editor.on_item_clicked(item)
        expected_key = item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(self.editor.current_key, expected_key)

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("Test Zone", True))
    def test_add_type_with_dialog(self, mock_dialog):
        config = ConfigManager.instance()
        if "Test Zone" in config.get_custom_polygon_types():
            config.delete_custom_polygon_type("Test Zone")
            self.editor.load_types()

        count_before = self.editor.type_list.count()
        types_before = set(config.get_custom_polygon_types().keys())

        self.editor.add_type()

        self.assertEqual(self.editor.type_list.count(), count_before + 1)
        types_after = config.get_custom_polygon_types()
        new_keys = set(types_after.keys()) - types_before
        self.assertEqual(len(new_keys), 1)
        new_key = new_keys.pop()
        self.assertEqual(new_key, "Test Zone")

        config.delete_custom_polygon_type(new_key)

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("", False))
    def test_add_type_cancel_does_nothing(self, mock_dialog):
        count_before = self.editor.type_list.count()
        self.editor.add_type()
        self.assertEqual(self.editor.type_list.count(), count_before)

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("  ", True))
    def test_add_type_empty_name_does_nothing(self, mock_dialog):
        count_before = self.editor.type_list.count()
        self.editor.add_type()
        self.assertEqual(self.editor.type_list.count(), count_before)

    def test_on_name_finished_renames_type(self):
        if self.editor.type_list.count() == 0:
            self.skipTest("No custom polygon types configured")
        item = self.editor.type_list.item(0)
        self.editor.type_list.setCurrentItem(item)
        self.editor.on_item_clicked(item)

        original_key = self.editor.current_key
        new_name = "Renamed Zone Test"
        self.editor.name_edit.setText(new_name)
        self.editor.on_name_finished()
        self.assertEqual(self.editor.current_key, new_name)
        self.assertEqual(item.text(), new_name)

        # Restore
        self.editor.name_edit.setText(original_key)
        self.editor.on_name_finished()
        self.assertEqual(self.editor.current_key, original_key)

    def test_generate_unique_color_valid_format(self):
        fill, border = self.editor._generate_unique_color()
        self.assertEqual(len(fill), 4)
        self.assertEqual(len(border), 3)
        for v in fill + border:
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 255)


class TestObjectTypeEditor(unittest.TestCase):
    def setUp(self):
        self.editor = ObjectTypeEditorWidget()

    def test_load_types_displays_name(self):
        config = ConfigManager.instance()
        types = config.get_object_types()
        for i in range(self.editor.type_list.count()):
            item = self.editor.type_list.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            self.assertIn(key, types)
            self.assertEqual(item.text(), key)

    def test_on_item_clicked_sets_key_from_user_role(self):
        if self.editor.type_list.count() == 0:
            self.skipTest("No object types configured")
        item = self.editor.type_list.item(0)
        self.editor.on_item_clicked(item)
        expected_key = item.data(Qt.ItemDataRole.UserRole)
        self.assertEqual(self.editor.current_key, expected_key)

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("Test Object", True))
    def test_add_type_with_dialog(self, mock_dialog):
        config = ConfigManager.instance()
        if "Test Object" in config.get_object_types():
            config.delete_object_type("Test Object")
            self.editor.load_types()

        count_before = self.editor.type_list.count()
        types_before = set(config.get_object_types().keys())

        self.editor.add_type()

        self.assertEqual(self.editor.type_list.count(), count_before + 1)
        types_after = config.get_object_types()
        new_keys = set(types_after.keys()) - types_before
        self.assertEqual(len(new_keys), 1)
        new_key = new_keys.pop()
        self.assertEqual(new_key, "Test Object")

        config.delete_object_type(new_key)

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("", False))
    def test_add_type_cancel_does_nothing(self, mock_dialog):
        count_before = self.editor.type_list.count()
        self.editor.add_type()
        self.assertEqual(self.editor.type_list.count(), count_before)

    @patch("src.gui.base_type_editor.QInputDialog.getText", return_value=("   ", True))
    def test_add_type_empty_name_does_nothing(self, mock_dialog):
        count_before = self.editor.type_list.count()
        self.editor.add_type()
        self.assertEqual(self.editor.type_list.count(), count_before)

    def test_on_name_finished_renames_type(self):
        if self.editor.type_list.count() == 0:
            self.skipTest("No object types configured")
        item = self.editor.type_list.item(0)
        self.editor.type_list.setCurrentItem(item)
        self.editor.on_item_clicked(item)

        original_key = self.editor.current_key
        new_name = "Renamed Object Test"
        self.editor.name_edit.setText(new_name)
        self.editor.on_name_finished()
        self.assertEqual(self.editor.current_key, new_name)
        self.assertEqual(item.text(), new_name)

        # Restore
        self.editor.name_edit.setText(original_key)
        self.editor.on_name_finished()
        self.assertEqual(self.editor.current_key, original_key)

    def test_generate_unique_color_valid_format(self):
        fill, border = self.editor._generate_unique_color()
        self.assertEqual(len(fill), 4)
        self.assertEqual(len(border), 3)
        for v in fill + border:
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 255)

    def test_generate_unique_color_default_alpha(self):
        """Object types should default to alpha=150."""
        fill, _ = self.editor._generate_unique_color()
        self.assertEqual(fill[3], 150)


if __name__ == "__main__":
    unittest.main()
