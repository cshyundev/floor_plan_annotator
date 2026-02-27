"""E2E tests for object (OBB) drawing workflow."""
import pytest
from unittest.mock import patch

from src.gui.items import ObjectItem
from tests.conftest import draw_object, items_of_type, make_context


@pytest.mark.e2e
class TestDrawObjects:

    def test_draw_object_creates_item(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 4.0, 3.0, object_type="furniture")

        objects = items_of_type(canvas, ObjectItem)
        assert len(objects) == 1
        assert objects[0].object_type == "furniture"
        assert objects[0].object_id == "0"

    def test_object_geometry(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 6.0, 4.0)

        obj = items_of_type(canvas, ObjectItem)[0]
        assert abs(obj.center.x() - 4.0) < 0.1
        assert abs(obj.center.y() - 3.0) < 0.1
        assert abs(obj.width - 4.0) < 0.1
        assert abs(obj.height - 2.0) < 0.1

    def test_object_undo(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 4.0, 3.0)
        assert len(items_of_type(canvas, ObjectItem)) == 1

        undo_stack.undo()
        assert len(items_of_type(canvas, ObjectItem)) == 0

    def test_object_undo_redo(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 4.0, 3.0, object_type="appliance")
        undo_stack.undo()
        undo_stack.redo()

        objects = items_of_type(canvas, ObjectItem)
        assert len(objects) == 1
        assert objects[0].object_type == "appliance"

    def test_too_small_drag_cancelled(self, canvas, undo_stack):
        """Near-zero drag does not create an object."""
        canvas.set_tool("object")
        tool = canvas.tool_manager.object_tool

        tool.on_mouse_press(make_context(2.0, 2.0))
        tool.on_mouse_release(make_context(2.005, 2.005))
        canvas.set_tool("select")

        assert len(items_of_type(canvas, ObjectItem)) == 0

    def test_sequential_object_ids(self, canvas, undo_stack):
        draw_object(canvas, 1.0, 1.0, 2.0, 2.0)
        draw_object(canvas, 3.0, 3.0, 4.0, 4.0)

        objects = items_of_type(canvas, ObjectItem)
        ids = sorted([o.object_id for o in objects])
        assert ids == ["0", "1"]
