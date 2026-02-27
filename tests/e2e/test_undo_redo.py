"""E2E tests for undo/redo chains across multiple operations."""
import pytest

from src.gui.items import EdgeItem, RoomItem, ObjectItem
from tests.conftest import draw_wall, draw_room, draw_object, items_of_type


@pytest.mark.e2e
class TestUndoRedo:

    def test_multi_step_undo_redo(self, canvas, undo_stack):
        """Create wall + room + object, undo all, redo all."""
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)
        draw_room(canvas, [(1, 2), (4, 2), (2.5, 4)])
        draw_object(canvas, 6.0, 6.0, 8.0, 7.0)

        assert len(items_of_type(canvas, EdgeItem)) >= 1
        assert len(items_of_type(canvas, RoomItem)) == 1
        assert len(items_of_type(canvas, ObjectItem)) == 1

        # Undo object
        undo_stack.undo()
        assert len(items_of_type(canvas, ObjectItem)) == 0
        assert len(items_of_type(canvas, RoomItem)) == 1

        # Undo room
        undo_stack.undo()
        assert len(items_of_type(canvas, RoomItem)) == 0

        # Redo room
        undo_stack.redo()
        assert len(items_of_type(canvas, RoomItem)) == 1

        # Redo object
        undo_stack.redo()
        assert len(items_of_type(canvas, ObjectItem)) == 1

    def test_undo_all_restores_empty_scene(self, canvas, undo_stack):
        """Undo everything to reach clean scene."""
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)
        draw_room(canvas, [(1, 2), (4, 2), (2.5, 4)])

        while undo_stack.canUndo():
            undo_stack.undo()

        assert len(items_of_type(canvas, EdgeItem)) == 0
        assert len(items_of_type(canvas, RoomItem)) == 0

    def test_new_action_clears_redo(self, canvas, undo_stack):
        """After undo, a new action clears redo history."""
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)
        draw_wall(canvas, 1.0, 3.0, 5.0, 3.0)

        undo_stack.undo()
        assert undo_stack.canRedo()

        # New action should clear redo
        draw_wall(canvas, 1.0, 5.0, 5.0, 5.0)
        assert not undo_stack.canRedo()
