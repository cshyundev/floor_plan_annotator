"""E2E tests for room drawing workflow."""
import pytest

from src.gui.items import NodeItem, RoomItem
from tests.conftest import draw_room, items_of_type


@pytest.mark.e2e
class TestDrawRooms:

    def test_triangle_room(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)], room_type="kitchen")

        rooms = items_of_type(canvas, RoomItem)
        assert len(rooms) == 1
        assert rooms[0].room_type == "kitchen"
        assert rooms[0].room_id == "0"

    def test_rectangle_room(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (5, 4), (1, 4)])

        rooms = items_of_type(canvas, RoomItem)
        assert len(rooms) == 1
        assert len(rooms[0].nodes) == 4

    def test_room_creates_correct_node_count(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)])

        nodes = items_of_type(canvas, NodeItem)
        assert len(nodes) == 3

    def test_sequential_room_ids(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (3, 1), (2, 3)])
        draw_room(canvas, [(5, 1), (7, 1), (6, 3)])

        rooms = items_of_type(canvas, RoomItem)
        ids = sorted([r.room_id for r in rooms])
        assert ids == ["0", "1"]

    def test_room_undo(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)])
        assert len(items_of_type(canvas, RoomItem)) == 1

        undo_stack.undo()
        assert len(items_of_type(canvas, RoomItem)) == 0

    def test_room_undo_redo(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)], room_type="bedroom")
        undo_stack.undo()
        assert len(items_of_type(canvas, RoomItem)) == 0

        undo_stack.redo()
        rooms = items_of_type(canvas, RoomItem)
        assert len(rooms) == 1
        assert rooms[0].room_type == "bedroom"

    def test_room_label_text(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)], room_type="kitchen")
        room = items_of_type(canvas, RoomItem)[0]
        label = room.get_label_text()
        assert "0" in label
