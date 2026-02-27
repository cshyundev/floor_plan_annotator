"""E2E tests for annotation type management."""
import pytest

from src.gui.items import RoomItem, ObjectItem, CustomPolygonItem
from src.core.undo_commands import (
    ChangeRoomTypeCommand,
    ChangeObjectTypeCommand,
    ChangeCustomPolygonTypeCommand,
)
from tests.conftest import draw_room, draw_object, draw_custom_polygon, items_of_type


@pytest.mark.e2e
class TestTypeManagement:

    def test_change_room_type(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)], room_type="living_room")
        room = items_of_type(canvas, RoomItem)[0]
        assert room.room_type == "living_room"

        cmd = ChangeRoomTypeCommand(room, "living_room", "kitchen")
        canvas.push_command(cmd)
        assert room.room_type == "kitchen"

    def test_change_room_type_undo(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)], room_type="bedroom")
        room = items_of_type(canvas, RoomItem)[0]

        cmd = ChangeRoomTypeCommand(room, "bedroom", "bathroom")
        canvas.push_command(cmd)
        assert room.room_type == "bathroom"

        undo_stack.undo()
        assert room.room_type == "bedroom"

    def test_change_object_type(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 4.0, 3.0, object_type="furniture")
        obj = items_of_type(canvas, ObjectItem)[0]

        cmd = ChangeObjectTypeCommand(obj, "furniture", "appliance")
        canvas.push_command(cmd)
        assert obj.object_type == "appliance"

    def test_change_object_type_undo(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 4.0, 3.0, object_type="obstacle")
        obj = items_of_type(canvas, ObjectItem)[0]

        cmd = ChangeObjectTypeCommand(obj, "obstacle", "furniture")
        canvas.push_command(cmd)
        assert obj.object_type == "furniture"

        undo_stack.undo()
        assert obj.object_type == "obstacle"

    def test_change_custom_polygon_type(self, canvas, undo_stack):
        draw_custom_polygon(canvas, [(1, 1), (4, 1), (4, 3), (1, 3)], polygon_type="clean_zone")
        polygon = items_of_type(canvas, CustomPolygonItem)[0]

        cmd = ChangeCustomPolygonTypeCommand(polygon, "clean_zone", "danger_zone")
        canvas.push_command(cmd)
        assert polygon.polygon_type == "danger_zone"

    def test_change_custom_polygon_type_undo(self, canvas, undo_stack):
        draw_custom_polygon(canvas, [(1, 1), (4, 1), (4, 3), (1, 3)], polygon_type="clean_zone")
        polygon = items_of_type(canvas, CustomPolygonItem)[0]

        cmd = ChangeCustomPolygonTypeCommand(polygon, "clean_zone", "danger_zone")
        canvas.push_command(cmd)
        assert polygon.polygon_type == "danger_zone"

        undo_stack.undo()
        assert polygon.polygon_type == "clean_zone"
