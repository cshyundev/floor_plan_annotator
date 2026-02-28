"""
Performance benchmark tests for 2D canvas drag operations.

Run: QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_performance.py -v -s
"""
import os
import time
from unittest.mock import patch

import numpy as np
import pytest
from PyQt6.QtCore import QPointF, QPoint, Qt
from PyQt6.QtGui import QUndoStack

from src.gui.canvas_2d import Canvas2D
from src.core.input_context import InputContext
from src.gui.items.nodes import NodeItem, EdgeItem
from src.gui.items.room_item import RoomItem
from src.gui.items.object_item import ObjectItem
from src.gui.items.polygon_base import PolygonItem


pytestmark = pytest.mark.benchmark


@pytest.fixture(scope="session", autouse=True)
def ensure_offscreen():
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture
def canvas(qtbot):
    c = Canvas2D()
    c.set_undo_stack(QUndoStack())
    img = np.zeros((500, 500), dtype=np.uint8)
    c.update_background(img, (0.0, 0.0, 20.0, 20.0), 25.0)
    qtbot.addWidget(c)
    c.show()
    qtbot.waitExposed(c)
    return c


def make_context(x, y, buttons=Qt.MouseButton.LeftButton,
                 modifiers=Qt.KeyboardModifier.NoModifier):
    return InputContext(
        scene_pos=QPointF(x, y),
        screen_pos=QPoint(int(x * 25), int(y * 25)),
        buttons=buttons,
        modifiers=modifiers,
    )


def _draw_room(canvas, points, room_type="living_room"):
    canvas.set_tool("room")
    tool = canvas.tool_manager.room_tool
    for x, y in points:
        ctx = make_context(x, y)
        tool.on_mouse_press(ctx)
        tool.on_mouse_release(ctx)
    with patch.object(tool, "_select_room_type", return_value=room_type):
        tool.on_mouse_press(make_context(0, 0, buttons=Qt.MouseButton.RightButton))
    canvas.set_tool("select")


def _draw_wall(canvas, x1, y1, x2, y2):
    canvas.set_tool("wall")
    tool = canvas.tool_manager.wall_tool
    tool.on_mouse_press(make_context(x1, y1))
    tool.on_mouse_press(make_context(x2, y2))
    canvas.set_tool("select")


def _draw_object(canvas, x1, y1, x2, y2, object_type="furniture"):
    canvas.set_tool("object")
    tool = canvas.tool_manager.object_tool
    tool.on_mouse_press(make_context(x1, y1))
    tool.on_mouse_move(make_context(x2, y2))
    with patch.object(tool, "_select_object_type", return_value=object_type):
        tool.on_mouse_release(make_context(x2, y2))
    canvas.set_tool("select")


def _populate_scene(canvas):
    """Create a realistic scene: 10 rooms, 5 objects, 20 walls."""
    for i in range(10):
        ox, oy = (i % 5) * 3.0, (i // 5) * 3.0
        _draw_room(canvas, [
            (ox, oy), (ox + 2, oy), (ox + 2, oy + 2), (ox, oy + 2)
        ])

    for i in range(5):
        ox = i * 3.0 + 0.5
        _draw_object(canvas, ox, 7.0, ox + 1.0, 8.0)

    for i in range(20):
        x = i * 0.8
        _draw_wall(canvas, x, 10.0, x, 12.0)


def _count_items(canvas, item_type):
    return sum(1 for i in canvas.scene.items() if isinstance(i, item_type))


class TestPerformanceBaseline:
    """Benchmark tests to measure drag performance."""

    def test_scene_setup(self, canvas):
        """Verify the test scene is populated correctly."""
        _populate_scene(canvas)
        rooms = _count_items(canvas, RoomItem)
        objects = _count_items(canvas, ObjectItem)
        nodes = _count_items(canvas, NodeItem)
        edges = _count_items(canvas, EdgeItem)
        print(f"\nScene: {rooms} rooms, {objects} objects, {nodes} nodes, {edges} edges")
        assert rooms == 10
        assert objects == 5

    def test_polygon_drag_performance(self, canvas):
        """Measure time for 100 polygon drag events."""
        _populate_scene(canvas)

        # Find the first room
        rooms = [i for i in canvas.scene.items() if isinstance(i, RoomItem)]
        assert rooms, "No rooms found"
        room = rooms[0]

        # Count update_shape calls
        shape_count = 0
        original_update_shape = PolygonItem.update_shape

        def counting_update_shape(self_):
            nonlocal shape_count
            shape_count += 1
            original_update_shape(self_)

        # Simulate polygon drag using batch update path (as in mouseMoveEvent)
        centroid = room._centroid
        drag_start = QPointF(centroid)
        initial_positions = [QPointF(n.pos()) for n in room.nodes]

        with patch.object(PolygonItem, 'update_shape', counting_update_shape):
            start = time.perf_counter()
            for step in range(100):
                delta = QPointF(step * 0.01, step * 0.01)
                room._batch_updating = True
                for i, node in enumerate(room.nodes):
                    node.setPos(initial_positions[i] + delta)
                room._batch_updating = False
                room.update_shape()
            elapsed = time.perf_counter() - start

        print(f"\nPolygon drag: {elapsed*1000:.1f}ms for 100 frames")
        print(f"  update_shape() calls: {shape_count}")
        print(f"  Per frame: {elapsed*10:.2f}ms")
        # Store for comparison
        assert elapsed < 10.0, f"Polygon drag too slow: {elapsed:.2f}s"

    def test_node_drag_performance(self, canvas):
        """Measure time for 100 node drag events."""
        _populate_scene(canvas)

        nodes = [i for i in canvas.scene.items() if isinstance(i, NodeItem)]
        assert nodes, "No nodes found"
        node = nodes[0]

        shape_count = 0
        original_update_shape = PolygonItem.update_shape

        def counting_update_shape(self_):
            nonlocal shape_count
            shape_count += 1
            original_update_shape(self_)

        node._drag_start_pos = node.pos()

        with patch.object(PolygonItem, 'update_shape', counting_update_shape):
            start = time.perf_counter()
            for step in range(100):
                node.setPos(node._drag_start_pos + QPointF(step * 0.01, step * 0.01))
            elapsed = time.perf_counter() - start

        node._drag_start_pos = None

        print(f"\nNode drag: {elapsed*1000:.1f}ms for 100 frames")
        print(f"  update_shape() calls: {shape_count}")
        print(f"  Per frame: {elapsed*10:.2f}ms")
        assert elapsed < 10.0, f"Node drag too slow: {elapsed:.2f}s"

    def test_object_drag_performance(self, canvas):
        """Measure time for 100 object drag events."""
        _populate_scene(canvas)

        objects = [i for i in canvas.scene.items() if isinstance(i, ObjectItem)]
        assert objects, "No objects found"
        obj = objects[0]

        start_center = QPointF(obj.center)

        start = time.perf_counter()
        for step in range(100):
            obj.center = start_center + QPointF(step * 0.01, step * 0.01)
            obj.update_shape()
        elapsed = time.perf_counter() - start

        print(f"\nObject drag: {elapsed*1000:.1f}ms for 100 frames")
        print(f"  Per frame: {elapsed*10:.2f}ms")
        assert elapsed < 10.0, f"Object drag too slow: {elapsed:.2f}s"

    def test_snap_collection_performance(self, canvas):
        """Measure snap reference position collection time."""
        _populate_scene(canvas)

        start = time.perf_counter()
        for _ in range(100):
            canvas.snap_manager._collect_reference_positions()
        elapsed = time.perf_counter() - start

        total_items = len(canvas.scene.items())
        print(f"\nSnap collection: {elapsed*1000:.1f}ms for 100 calls ({total_items} scene items)")
        print(f"  Per call: {elapsed*10:.2f}ms")
        assert elapsed < 5.0, f"Snap collection too slow: {elapsed:.2f}s"
