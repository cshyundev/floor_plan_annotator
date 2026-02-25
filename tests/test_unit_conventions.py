"""Tests to prevent pixel/meter unit confusion and silent config fallbacks.

These tests verify:
1. QPen widths are in meter-scale scene coordinates (0.001 ~ 0.5), not pixels
2. No silent fallback patterns (get_ui_value(...) or default) exist in source
3. Config access uses correct methods (get_ui_value, not get_value("ui_config",...))
"""
import re
import unittest
import sys
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication, QGraphicsScene

if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.items import NodeItem, EdgeItem, RoomItem, CustomPolygonItem, ObjectItem
from src.core.config import ConfigManager


# Meter-scale scene coordinates: pen widths must fall in this range.
# Values >= 1.0 almost certainly indicate pixel units (the exact bug we guard against).
MIN_PEN_WIDTH_METERS = 0.001
MAX_PEN_WIDTH_METERS = 0.5

# Source files to check for forbidden patterns
# items.py and tools.py have been split into packages
_ITEMS_FILES = [
    "src/gui/items/nodes.py",
    "src/gui/items/polygon_base.py",
    "src/gui/items/room_item.py",
    "src/gui/items/custom_polygon_item.py",
    "src/gui/items/object_item.py",
]
_TOOLS_FILES = [
    "src/gui/tools/base.py",
    "src/gui/tools/select_tool.py",
    "src/gui/tools/draw_wall_tool.py",
    "src/gui/tools/draw_polygon_tool.py",
    "src/gui/tools/draw_object_tool.py",
]
SRC_GUI_FILES = _ITEMS_FILES + _TOOLS_FILES
SRC_ALL_FILES = SRC_GUI_FILES + [
    "src/gui/canvas_2d.py",
    "src/gui/clipboard_manager.py",
    "src/gui/data_serializer.py",
    "src/gui/event_coordinator.py",
    "src/gui/main_window.py",
    "src/gui/viewer_3d_stub.py",
    "src/gui/snap/snap_engine.py",
    "src/gui/snap/snap_guide_manager.py",
    "src/core/annotation_sync.py",
]


class TestAnnotationPenWidthUnits(unittest.TestCase):
    """Verify all annotation items use meter-scale pen widths, not pixels."""

    def setUp(self):
        self.scene = QGraphicsScene()

    def _assert_meter_scale(self, width: float, context: str):
        self.assertGreaterEqual(
            width, MIN_PEN_WIDTH_METERS,
            f"{context}: pen width {width} is below meter range "
            f"(min={MIN_PEN_WIDTH_METERS})"
        )
        self.assertLessEqual(
            width, MAX_PEN_WIDTH_METERS,
            f"{context}: pen width {width} exceeds meter range "
            f"(max={MAX_PEN_WIDTH_METERS}) — likely a pixel value"
        )

    def test_edge_item_pen_width_is_meters(self):
        """EdgeItem (wall) pen width should be in meter range."""
        n1 = NodeItem(0, 0)
        n2 = NodeItem(1, 0)
        self.scene.addItem(n1)
        self.scene.addItem(n2)
        edge = EdgeItem(n1, n2)
        self.scene.addItem(edge)

        width = edge.pen().widthF()
        self._assert_meter_scale(width, "EdgeItem default pen")

    def test_room_item_pen_width_is_meters(self):
        """RoomItem pen width should be in meter range."""
        nodes = [NodeItem(0, 0), NodeItem(1, 0), NodeItem(1, 1)]
        room = RoomItem(nodes, room_type="living_room", room_id="1")
        self.scene.addItem(room)

        width = room.pen().widthF()
        self._assert_meter_scale(width, "RoomItem pen")

    def test_custom_polygon_item_pen_width_is_meters(self):
        """CustomPolygonItem pen width should be in meter range."""
        nodes = [NodeItem(0, 0), NodeItem(1, 0), NodeItem(1, 1)]
        item = CustomPolygonItem(nodes, polygon_type="clean_zone", polygon_id="1")
        self.scene.addItem(item)

        width = item.pen().widthF()
        self._assert_meter_scale(width, "CustomPolygonItem pen")

    def test_object_item_pen_width_is_meters(self):
        """ObjectItem pen width should be in meter range."""
        from PyQt6.QtCore import QPointF
        item = ObjectItem(
            center=QPointF(0.0, 0.0),
            width=1.0, height=0.5, angle=0.0,
            object_type="chair", object_id="1"
        )
        self.scene.addItem(item)

        width = item.pen().widthF()
        self._assert_meter_scale(width, "ObjectItem pen")


class TestTempEdgePenWidthUnits(unittest.TestCase):
    """Verify DrawPolygonTool creates temp edges with meter-scale pen width."""

    def setUp(self):
        self.scene = QGraphicsScene()

    def test_create_temp_edge_pen_width_is_meters(self):
        """_create_temp_edge() should produce an edge with meter-scale pen."""
        from src.gui.tools import DrawRoomTool

        canvas = MagicMock()
        canvas.scene.return_value = self.scene

        tool = DrawRoomTool(canvas)
        tool.scene = self.scene

        n1 = NodeItem(0, 0)
        n2 = NodeItem(1, 0)
        self.scene.addItem(n1)
        self.scene.addItem(n2)

        edge = tool._create_temp_edge(n1, n2)

        width = edge.pen().widthF()
        self.assertGreaterEqual(width, MIN_PEN_WIDTH_METERS)
        self.assertLessEqual(
            width, MAX_PEN_WIDTH_METERS,
            f"Temp edge pen width {width} exceeds meter range — likely pixel value"
        )


class TestStaticForbiddenPatterns(unittest.TestCase):
    """Static analysis: detect forbidden patterns in source files."""

    def _read_source(self, path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    def test_no_qpen_with_integer_width(self):
        """No QPen(color, integer) in GUI files."""
        for path in SRC_GUI_FILES:
            source = self._read_source(path)
            matches = re.findall(r'QPen\([^)]*,\s*[1-9]\d*\s*\)', source)
            self.assertEqual(
                matches, [],
                f"{path}: QPen with integer width (likely pixels): {matches}"
            )

    def test_no_width_from_colors_config(self):
        """No get_value("colors", ..., "width") — colors.yaml has no width values."""
        for path in SRC_GUI_FILES:
            source = self._read_source(path)
            matches = re.findall(r'get_value\("colors".*width', source)
            self.assertEqual(
                matches, [],
                f"{path}: fetching width from colors config: {matches}"
            )

    def test_no_silent_fallbacks_on_get_ui_value(self):
        """No get_ui_value(...) or fallback — get_ui_value raises KeyError."""
        for path in SRC_ALL_FILES:
            source = self._read_source(path)
            matches = re.findall(r'get_ui_value\(.*?\)\s+or\s+', source)
            self.assertEqual(
                matches, [],
                f"{path}: silent fallback on get_ui_value (forbidden): {matches}"
            )

    def test_no_silent_fallbacks_on_get_value(self):
        """No get_value(...) or fallback — config must be authoritative."""
        for path in SRC_ALL_FILES:
            source = self._read_source(path)
            matches = re.findall(r'get_value\(.*?\)\s+or\s+', source)
            self.assertEqual(
                matches, [],
                f"{path}: silent fallback on get_value (forbidden): {matches}"
            )

    def test_no_get_value_ui_config(self):
        """No get_value("ui_config", ...) — use get_ui_value() instead."""
        for path in SRC_ALL_FILES:
            source = self._read_source(path)
            matches = re.findall(r'get_value\("ui_config"', source)
            self.assertEqual(
                matches, [],
                f"{path}: use get_ui_value() instead of get_value('ui_config',...): {matches}"
            )


if __name__ == "__main__":
    unittest.main()
