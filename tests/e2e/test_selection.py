"""E2E tests for selection and move workflows."""
import pytest
from PyQt6.QtCore import QPointF

from src.gui.items import NodeItem, RoomItem, ObjectItem
from src.core.undo_commands import MoveNodeCommand
from tests.conftest import (
    draw_wall, draw_room, draw_object, items_of_type, select_item,
)


@pytest.mark.e2e
class TestSelection:

    def test_select_tool_is_default(self, canvas):
        from src.gui.tools.select_tool import SelectTool
        assert isinstance(canvas.current_tool, SelectTool)

    def test_select_room(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)])
        room = items_of_type(canvas, RoomItem)[0]

        select_item(canvas, room)
        assert room.isSelected()
        assert len(canvas.scene.selectedItems()) == 1

    def test_clear_selection(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)])
        room = items_of_type(canvas, RoomItem)[0]
        select_item(canvas, room)

        canvas.scene.clearSelection()
        assert not room.isSelected()
        assert len(canvas.scene.selectedItems()) == 0

    def test_node_move_via_command(self, canvas, undo_stack):
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)
        nodes = items_of_type(canvas, NodeItem)
        node = nodes[0]
        original_pos = QPointF(node.pos())
        new_pos = QPointF(2.0, 3.0)

        cmd = MoveNodeCommand(node, original_pos, new_pos)
        canvas.push_command(cmd)
        assert node.pos() == new_pos

        undo_stack.undo()
        assert node.pos() == original_pos

        undo_stack.redo()
        assert node.pos() == new_pos

    def test_select_object(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 4.0, 3.0)
        obj = items_of_type(canvas, ObjectItem)[0]

        select_item(canvas, obj)
        assert obj.isSelected()
