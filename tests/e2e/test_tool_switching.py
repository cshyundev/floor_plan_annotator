"""E2E tests for tool switching."""
import pytest

from src.gui.tools.select_tool import SelectTool
from src.gui.tools.draw_wall_tool import DrawWallTool
from src.gui.tools.draw_polygon_tool import DrawRoomTool, DrawCustomPolygonTool
from src.gui.tools.draw_object_tool import DrawObjectTool
from tests.conftest import make_context


@pytest.mark.e2e
class TestToolSwitching:

    def test_default_is_select(self, canvas):
        assert isinstance(canvas.current_tool, SelectTool)

    def test_switch_to_wall(self, canvas):
        canvas.set_tool("wall")
        assert isinstance(canvas.current_tool, DrawWallTool)

    def test_switch_to_room(self, canvas):
        canvas.set_tool("room")
        assert isinstance(canvas.current_tool, DrawRoomTool)

    def test_switch_to_custom_polygon(self, canvas):
        canvas.set_tool("custom_polygon")
        assert isinstance(canvas.current_tool, DrawCustomPolygonTool)

    def test_switch_to_object(self, canvas):
        canvas.set_tool("object")
        assert isinstance(canvas.current_tool, DrawObjectTool)

    def test_switch_back_to_select(self, canvas):
        canvas.set_tool("wall")
        canvas.set_tool("select")
        assert isinstance(canvas.current_tool, SelectTool)

    def test_tool_changed_signal(self, canvas, qtbot):
        with qtbot.waitSignal(canvas.tool_changed, timeout=1000) as blocker:
            canvas.set_tool("wall")
        assert blocker.args == ["wall"]

    def test_switch_mid_drawing_cleans_up(self, canvas):
        """Switching tools mid-drawing cleans up temporary state."""
        canvas.set_tool("room")
        tool = canvas.tool_manager.room_tool

        # Add 2 nodes
        ctx1 = make_context(1, 1)
        tool.on_mouse_press(ctx1)
        tool.on_mouse_release(ctx1)
        ctx2 = make_context(3, 1)
        tool.on_mouse_press(ctx2)
        tool.on_mouse_release(ctx2)

        assert len(tool.current_nodes) == 2

        # Switching should cleanup
        canvas.set_tool("select")
        assert len(tool.current_nodes) == 0
