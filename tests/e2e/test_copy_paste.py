"""E2E tests for copy/paste workflow."""
import pytest

from src.gui.items import RoomItem, ObjectItem
from tests.conftest import draw_room, draw_object, items_of_type, select_item


@pytest.mark.e2e
class TestCopyPaste:

    def test_copy_paste_room(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (3, 1), (2, 3)])
        room = items_of_type(canvas, RoomItem)[0]

        select_item(canvas, room)
        canvas.copy_selection()
        canvas.paste_clipboard()

        rooms = items_of_type(canvas, RoomItem)
        assert len(rooms) == 2
        ids = {r.room_id for r in rooms}
        assert len(ids) == 2  # different IDs

    def test_copy_paste_object(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 4.0, 3.0, object_type="appliance")
        obj = items_of_type(canvas, ObjectItem)[0]

        select_item(canvas, obj)
        canvas.copy_selection()
        canvas.paste_clipboard()

        objects = items_of_type(canvas, ObjectItem)
        assert len(objects) == 2

    def test_paste_is_undoable(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (3, 1), (2, 3)])
        room = items_of_type(canvas, RoomItem)[0]
        select_item(canvas, room)
        canvas.copy_selection()
        canvas.paste_clipboard()

        assert len(items_of_type(canvas, RoomItem)) == 2

        undo_stack.undo()
        assert len(items_of_type(canvas, RoomItem)) == 1

    def test_paste_empty_clipboard_noop(self, canvas, undo_stack):
        initial_count = undo_stack.count()
        canvas.paste_clipboard()
        assert undo_stack.count() == initial_count
