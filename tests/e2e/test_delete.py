"""E2E tests for item deletion."""
import pytest
from PyQt6.QtCore import Qt

from src.gui.items import RoomItem, ObjectItem
from tests.conftest import (
    draw_room, draw_object, items_of_type, select_item, press_key,
)


@pytest.mark.e2e
class TestDeleteItems:

    def test_delete_selected_room(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)])
        room = items_of_type(canvas, RoomItem)[0]

        select_item(canvas, room)
        canvas.delete_selected_items()

        assert len(items_of_type(canvas, RoomItem)) == 0

    def test_delete_room_undo(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)])
        room = items_of_type(canvas, RoomItem)[0]

        select_item(canvas, room)
        canvas.delete_selected_items()
        assert len(items_of_type(canvas, RoomItem)) == 0

        undo_stack.undo()
        assert len(items_of_type(canvas, RoomItem)) == 1

    def test_delete_object(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 4.0, 3.0)
        obj = items_of_type(canvas, ObjectItem)[0]

        select_item(canvas, obj)
        canvas.delete_selected_items()

        assert len(items_of_type(canvas, ObjectItem)) == 0

    def test_delete_via_keyboard(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)])
        room = items_of_type(canvas, RoomItem)[0]
        select_item(canvas, room)

        press_key(canvas, Qt.Key.Key_Delete)

        assert len(items_of_type(canvas, RoomItem)) == 0

    def test_delete_nothing_selected_noop(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)])
        canvas.scene.clearSelection()

        initial_count = undo_stack.count()
        canvas.delete_selected_items()
        assert undo_stack.count() == initial_count
