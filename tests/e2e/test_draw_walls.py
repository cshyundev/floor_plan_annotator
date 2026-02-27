"""E2E tests for wall drawing workflow."""
import pytest
from PyQt6.QtCore import Qt

from src.gui.items import NodeItem, EdgeItem
from tests.conftest import draw_wall, items_of_type, make_context


@pytest.mark.e2e
class TestDrawWalls:

    def test_single_wall_creates_nodes_and_edge(self, canvas, undo_stack):
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)

        nodes = items_of_type(canvas, NodeItem)
        edges = items_of_type(canvas, EdgeItem)
        assert len(nodes) == 2
        assert len(edges) == 1
        assert edges[0].start_node in nodes
        assert edges[0].end_node in nodes

    def test_wall_chain_shares_intermediate_node(self, canvas, undo_stack):
        canvas.set_tool("wall")
        tool = canvas.tool_manager.wall_tool

        tool.on_mouse_press(make_context(1.0, 1.0))
        tool.on_mouse_press(make_context(3.0, 1.0))
        tool.on_mouse_press(make_context(5.0, 1.0))
        canvas.set_tool("select")

        nodes = items_of_type(canvas, NodeItem)
        edges = items_of_type(canvas, EdgeItem)
        assert len(nodes) == 3
        assert len(edges) == 2

    def test_wall_undo_removes_last_segment(self, canvas, undo_stack):
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)
        assert len(items_of_type(canvas, EdgeItem)) == 1

        undo_stack.undo()
        assert len(items_of_type(canvas, EdgeItem)) == 0
        # First node from first click remains
        assert len(items_of_type(canvas, NodeItem)) == 1

    def test_wall_undo_redo_roundtrip(self, canvas, undo_stack):
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)
        undo_stack.undo()
        assert len(items_of_type(canvas, EdgeItem)) == 0

        undo_stack.redo()
        assert len(items_of_type(canvas, EdgeItem)) == 1
        assert len(items_of_type(canvas, NodeItem)) == 2

    def test_right_click_finishes_chain(self, canvas, undo_stack):
        canvas.set_tool("wall")
        tool = canvas.tool_manager.wall_tool

        tool.on_mouse_press(make_context(1.0, 1.0))
        tool.on_mouse_press(make_context(3.0, 1.0))

        # Right-click release finishes chain
        ctx_right = make_context(3.0, 1.0, buttons=Qt.MouseButton.RightButton)
        tool.on_mouse_release(ctx_right)

        assert tool.current_start_node is None

    def test_click_outside_bounds_ignored(self, canvas, undo_stack):
        """Clicks outside background bounds (0-10m) are ignored."""
        canvas.set_tool("wall")
        tool = canvas.tool_manager.wall_tool

        tool.on_mouse_press(make_context(15.0, 15.0))
        assert tool.current_start_node is None
        assert len(items_of_type(canvas, NodeItem)) == 0
