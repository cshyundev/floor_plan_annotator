"""
Performance benchmark tests for 2D canvas drag and selection operations.

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


class TestSelectionPerformance:
    """Benchmark tests to measure selection, click, and hover performance."""

    def test_scene_items_query(self, canvas):
        """Measure raw scene.items(pos) BSP tree query time."""
        _populate_scene(canvas)

        total_items = len(canvas.scene.items())

        # Position overlapping items (room area)
        test_pos = QPointF(1.0, 1.0)
        canvas.scene.items(test_pos)  # warm up

        N = 1000
        start = time.perf_counter()
        for _ in range(N):
            canvas.scene.items(test_pos)
        elapsed = time.perf_counter() - start

        per_call_us = (elapsed / N) * 1_000_000

        # Empty position (no items)
        empty_pos = QPointF(18.0, 18.0)
        start = time.perf_counter()
        for _ in range(N):
            canvas.scene.items(empty_pos)
        elapsed_empty = time.perf_counter() - start

        per_empty_us = (elapsed_empty / N) * 1_000_000

        print(f"\nscene.items(pos) — {total_items} total scene items:")
        print(f"  With items:  {per_call_us:.1f}us/call")
        print(f"  Empty area:  {per_empty_us:.1f}us/call")
        assert per_call_us < 100, f"scene.items(pos) too slow: {per_call_us:.1f}us"

    def test_select_tool_click(self, canvas):
        """Measure full SelectTool.on_mouse_press path."""
        _populate_scene(canvas)
        canvas.set_tool("select")
        tool = canvas.tool_manager.select_tool

        # Click on room polygon area
        ctx = make_context(1.0, 1.0)

        N = 500
        start = time.perf_counter()
        for _ in range(N):
            tool.on_mouse_press(ctx)
        elapsed = time.perf_counter() - start

        per_call_us = (elapsed / N) * 1_000_000

        # Click on empty area (clearSelection path)
        ctx_empty = make_context(18.0, 18.0)
        start = time.perf_counter()
        for _ in range(N):
            tool.on_mouse_press(ctx_empty)
        elapsed_empty = time.perf_counter() - start

        per_empty_us = (elapsed_empty / N) * 1_000_000

        print(f"\nSelectTool.on_mouse_press:")
        print(f"  On item:    {per_call_us:.1f}us/call")
        print(f"  Empty area: {per_empty_us:.1f}us/call")
        assert per_call_us < 500, f"Selection click too slow: {per_call_us:.1f}us"

    def test_guide_pool_bsp_impact(self, canvas):
        """Measure scene.items(pos) overhead from snap guide pool items in BSP tree."""
        _populate_scene(canvas)

        test_pos = QPointF(1.0, 1.0)
        N = 1000

        # Baseline: no guide pool items
        pool_before = len(canvas.snap_manager._guide_pool)
        canvas.scene.items(test_pos)  # warm up

        start = time.perf_counter()
        for _ in range(N):
            canvas.scene.items(test_pos)
        elapsed_without = time.perf_counter() - start

        # Create guide pool items by triggering snap_drag_point
        for i in range(10):
            canvas.snap_manager.snap_drag_point(QPointF(i * 0.5, i * 0.5))
        canvas.snap_manager.clear_guides()  # hide but keep in scene

        pool_after = len(canvas.snap_manager._guide_pool)
        total_items = len(canvas.scene.items())

        start = time.perf_counter()
        for _ in range(N):
            canvas.scene.items(test_pos)
        elapsed_with = time.perf_counter() - start

        overhead_pct = ((elapsed_with - elapsed_without) / elapsed_without) * 100 if elapsed_without > 0 else 0

        print(f"\nGuide pool BSP impact:")
        print(f"  Pool items: {pool_before} -> {pool_after}")
        print(f"  Without pool: {elapsed_without*1000:.2f}ms ({N} queries)")
        print(f"  With pool:    {elapsed_with*1000:.2f}ms ({N} queries)")
        print(f"  Overhead:     {overhead_pct:+.1f}%")
        print(f"  Total scene items: {total_items}")
        assert overhead_pct < 20, f"Guide pool BSP overhead too high: {overhead_pct:.1f}%"

    def test_hover_find_nearest_edge(self, canvas):
        """Measure _find_nearest_edge cost during polygon hover."""
        _populate_scene(canvas)

        rooms = [i for i in canvas.scene.items() if isinstance(i, RoomItem)]
        assert rooms, "No rooms found"
        room = rooms[0]

        hover_pos = QPointF(room._centroid.x() + 0.1, room._centroid.y())

        N = 5000
        start = time.perf_counter()
        for _ in range(N):
            room._find_nearest_edge(hover_pos)
        elapsed = time.perf_counter() - start

        per_call_us = (elapsed / N) * 1_000_000
        print(f"\n_find_nearest_edge ({len(room.nodes)} nodes): {per_call_us:.2f}us/call")
        assert per_call_us < 50, f"_find_nearest_edge too slow: {per_call_us:.2f}us"

    def test_is_drawing_tool_active(self, canvas):
        """Measure _is_drawing_tool_active per-item guard overhead."""
        _populate_scene(canvas)
        canvas.set_tool("select")

        rooms = [i for i in canvas.scene.items() if isinstance(i, RoomItem)]
        objects = [i for i in canvas.scene.items() if isinstance(i, ObjectItem)]
        room = rooms[0]
        obj = objects[0]

        N = 5000
        start = time.perf_counter()
        for _ in range(N):
            room._is_drawing_tool_active()
        elapsed_poly = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(N):
            obj._is_drawing_tool_active()
        elapsed_obj = time.perf_counter() - start

        poly_us = (elapsed_poly / N) * 1_000_000
        obj_us = (elapsed_obj / N) * 1_000_000

        print(f"\n_is_drawing_tool_active:")
        print(f"  PolygonItem: {poly_us:.2f}us/call")
        print(f"  ObjectItem:  {obj_us:.2f}us/call")
        assert poly_us < 20, f"_is_drawing_tool_active (polygon) too slow: {poly_us:.2f}us"
        assert obj_us < 20, f"_is_drawing_tool_active (object) too slow: {obj_us:.2f}us"

    def test_hit_testing_shape(self, canvas):
        """Measure shape()/boundingRect() cost for hit testing."""
        _populate_scene(canvas)

        objects = [i for i in canvas.scene.items() if isinstance(i, ObjectItem)]
        rooms = [i for i in canvas.scene.items() if isinstance(i, RoomItem)]
        obj = objects[0]
        room = rooms[0]

        N = 5000

        start = time.perf_counter()
        for _ in range(N):
            obj.shape()
        elapsed_obj_shape = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(N):
            obj.boundingRect()
        elapsed_obj_br = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(N):
            room.shape()
        elapsed_room_shape = time.perf_counter() - start

        obj_shape_us = (elapsed_obj_shape / N) * 1_000_000
        obj_br_us = (elapsed_obj_br / N) * 1_000_000
        room_shape_us = (elapsed_room_shape / N) * 1_000_000

        print(f"\nHit testing:")
        print(f"  ObjectItem.shape():        {obj_shape_us:.2f}us/call")
        print(f"  ObjectItem.boundingRect():  {obj_br_us:.2f}us/call")
        print(f"  RoomItem.shape():          {room_shape_us:.2f}us/call")
        assert obj_shape_us < 50, f"ObjectItem.shape() too slow: {obj_shape_us:.2f}us"

    def test_cycle_detection_overlapping(self, canvas):
        """Measure click performance with multiple overlapping items."""
        # Create overlapping items at the same position
        for _ in range(5):
            _draw_room(canvas, [
                (1.0, 1.0), (3.0, 1.0), (3.0, 3.0), (1.0, 3.0)
            ])
        for _ in range(3):
            _draw_object(canvas, 1.5, 1.5, 2.5, 2.5)

        canvas.set_tool("select")
        tool = canvas.tool_manager.select_tool

        ctx = make_context(2.0, 2.0)
        items_at_pos = len(canvas.scene.items(QPointF(2.0, 2.0)))

        N = 500
        start = time.perf_counter()
        for _ in range(N):
            tool.on_mouse_press(ctx)
        elapsed = time.perf_counter() - start

        per_call_us = (elapsed / N) * 1_000_000

        print(f"\nCycle detection ({items_at_pos} items at pos):")
        print(f"  Per click: {per_call_us:.1f}us/call")
        assert per_call_us < 1000, f"Cycle click too slow: {per_call_us:.1f}us"

    def test_filter_rubberband_selection(self, canvas):
        """Measure _filter_rubberband_selection cost (called on every mouseRelease)."""
        _populate_scene(canvas)

        # Select a few items
        rooms = [i for i in canvas.scene.items() if isinstance(i, RoomItem)]
        for r in rooms[:3]:
            r.setSelected(True)

        N = 2000
        start = time.perf_counter()
        for _ in range(N):
            canvas._filter_rubberband_selection()
        elapsed = time.perf_counter() - start

        per_call_us = (elapsed / N) * 1_000_000
        print(f"\n_filter_rubberband_selection: {per_call_us:.2f}us/call")
        assert per_call_us < 50, f"Rubberband filter too slow: {per_call_us:.2f}us"

    def test_edge_paint_set_pen(self, canvas):
        """Measure EdgeItem.paint per-frame state check and setPen overhead."""
        _populate_scene(canvas)

        edges = [i for i in canvas.scene.items() if isinstance(i, EdgeItem)]
        assert edges, "No edges found"
        edge = edges[0]

        N = 5000

        # State check cost
        start = time.perf_counter()
        for _ in range(N):
            edge.isSelected()
            edge.isUnderMouse()
        elapsed_check = time.perf_counter() - start

        # setPen cost
        pen = edge.pen_default
        start = time.perf_counter()
        for _ in range(N):
            edge.setPen(pen)
        elapsed_pen = time.perf_counter() - start

        check_us = (elapsed_check / N) * 1_000_000
        pen_us = (elapsed_pen / N) * 1_000_000

        print(f"\nEdgeItem paint overhead:")
        print(f"  State checks (isSelected+isUnderMouse): {check_us:.2f}us/frame")
        print(f"  setPen():                                {pen_us:.2f}us/frame")
        assert check_us < 40, f"State check too slow: {check_us:.2f}us"
