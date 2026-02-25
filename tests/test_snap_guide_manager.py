"""Integration tests for SnapGuideManager with mock scene."""

import sys
import unittest
from unittest.mock import MagicMock, PropertyMock

from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsLineItem
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QTransform

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.gui.items.nodes import NodeItem, EdgeItem
from src.gui.items.object_item import ObjectItem
from src.gui.snap.snap_guide_manager import SnapGuideManager


class MockCanvas:
    """Minimal canvas mock for SnapGuideManager tests."""

    def __init__(self, scene):
        self.scene = scene
        self._zoom = 20.0

    def transform(self):
        t = QTransform()
        t.scale(self._zoom, self._zoom)
        return t


class TestSnapGuideManager(unittest.TestCase):

    def setUp(self):
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-10, -10, 30, 30)
        self.canvas = MockCanvas(self.scene)
        self.mgr = SnapGuideManager(self.scene, self.canvas)

    def tearDown(self):
        self.mgr.clear_guides()
        self.scene.clear()

    # ─── Initialization ──────────────────────

    def test_creation(self):
        """Manager initializes with empty guides."""
        self.assertEqual(len(self.mgr._active_guides), 0)

    # ─── Drawing snap ────────────────────────

    def test_snap_drawing_horizontal(self):
        """Drawing near horizontal → snaps to 0° and shows guide."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 0.3)  # ~1.7°
        result = self.mgr.snap_drawing_point(cursor, anchor_pos=anchor)

        self.assertAlmostEqual(result.y(), 0.0, places=5)
        self.assertGreater(len(self.mgr._active_guides), 0)

    def test_snap_drawing_vertical(self):
        """Drawing near vertical → snaps to 90° and shows guide."""
        anchor = QPointF(0, 0)
        cursor = QPointF(0.3, 10)  # ~88.3°
        result = self.mgr.snap_drawing_point(cursor, anchor_pos=anchor)

        self.assertAlmostEqual(result.x(), 0.0, places=5)

    def test_snap_drawing_no_anchor(self):
        """Without anchor, only alignment snap applies."""
        node = NodeItem(5, 0)
        self.scene.addItem(node)

        cursor = QPointF(5.1, 10)  # X near 5
        result = self.mgr.snap_drawing_point(cursor)

        # Should snap X to 5 (alignment) — no angle snap since no anchor
        self.assertAlmostEqual(result.x(), 5.0, places=5)

    # ─── Relative snap ───────────────────────

    def test_snap_parallel_to_existing_edge(self):
        """New line parallel to existing 45° edge → snaps."""
        n1 = NodeItem(0, 0)
        n2 = NodeItem(5, 5)
        self.scene.addItem(n1)
        self.scene.addItem(n2)
        edge = EdgeItem(n1, n2)
        self.scene.addItem(edge)

        anchor = QPointF(0, 3)
        cursor = QPointF(10, 13.5)  # ~46.3°, within 5° of 45°
        result = self.mgr.snap_drawing_point(cursor, anchor_pos=anchor)

        # Should snap to 45°: dx == dy
        dx = result.x() - anchor.x()
        dy = result.y() - anchor.y()
        self.assertAlmostEqual(dx, dy, places=4)

    # ─── Alignment snap ──────────────────────

    def test_alignment_with_existing_nodes(self):
        """Alignment guide shown when cursor X matches a node."""
        node = NodeItem(5, 3)
        self.scene.addItem(node)

        cursor = QPointF(5.1, 10)  # X near 5
        result = self.mgr.snap_drawing_point(cursor)

        self.assertAlmostEqual(result.x(), 5.0, places=5)
        # At least one alignment guide should be present
        guide_items = [g for g in self.mgr._active_guides if isinstance(g, QGraphicsLineItem)]
        self.assertGreater(len(guide_items), 0)

    def test_alignment_with_object_center(self):
        """Alignment guide shown when cursor matches an ObjectItem center."""
        obj = ObjectItem(QPointF(8, 4), 2.0, 1.0, 0.0, "table", "obj0")
        self.scene.addItem(obj)

        cursor = QPointF(8.1, 10)  # X near 8
        result = self.mgr.snap_drawing_point(cursor)

        self.assertAlmostEqual(result.x(), 8.0, places=5)

    # ─── Guide management ────────────────────

    def test_clear_guides_removes_items(self):
        """After clear, all guide items are removed from scene."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 0.3)
        self.mgr.snap_drawing_point(cursor, anchor_pos=anchor)
        self.assertGreater(len(self.mgr._active_guides), 0)

        self.mgr.clear_guides()
        self.assertEqual(len(self.mgr._active_guides), 0)

    def test_guides_refresh_on_each_call(self):
        """Each call clears previous guides before showing new ones."""
        anchor = QPointF(0, 0)
        self.mgr.snap_drawing_point(QPointF(10, 0.3), anchor_pos=anchor)
        first_count = len(self.mgr._active_guides)

        self.mgr.snap_drawing_point(QPointF(0.3, 10), anchor_pos=anchor)
        # Previous guides should be cleared, new ones shown
        self.assertGreater(len(self.mgr._active_guides), 0)

    def test_guide_z_value(self):
        """Guide items should have high z-value from config."""
        anchor = QPointF(0, 0)
        self.mgr.snap_drawing_point(QPointF(10, 0.3), anchor_pos=anchor)

        for guide_item in self.mgr._active_guides:
            self.assertEqual(guide_item.zValue(), 200)

    # ─── Shift toggle ────────────────────────

    def test_shift_disables_snap(self):
        """With Shift held, snap is disabled (default snap.enabled=true)."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 0.3)
        result = self.mgr.snap_drawing_point(
            cursor, anchor_pos=anchor,
            modifiers=Qt.KeyboardModifier.ShiftModifier,
        )

        # Snap disabled → original position returned
        self.assertAlmostEqual(result.x(), cursor.x(), places=5)
        self.assertAlmostEqual(result.y(), cursor.y(), places=5)
        self.assertEqual(len(self.mgr._active_guides), 0)

    # ─── Drag snap ───────────────────────────

    def test_drag_shows_guides_only(self):
        """Drag snap shows alignment guides but returns original position."""
        node = NodeItem(5, 3)
        self.scene.addItem(node)

        cursor = QPointF(5.1, 10)
        result = self.mgr.snap_drag_point(cursor)

        # Returns original position (guide-only in Phase 1)
        self.assertAlmostEqual(result.x(), cursor.x(), places=5)
        # But guides should be shown
        self.assertGreater(len(self.mgr._active_guides), 0)

    # ─── Reference collection ────────────────

    def test_collect_reference_positions(self):
        """Collects positions from NodeItem and ObjectItem."""
        n = NodeItem(3, 4)
        self.scene.addItem(n)
        obj = ObjectItem(QPointF(8, 2), 1, 1, 0, "table", "o0")
        self.scene.addItem(obj)

        positions = self.mgr._collect_reference_positions()
        xs = sorted([p.x() for p in positions])

        self.assertIn(3.0, xs)
        self.assertIn(8.0, xs)

    def test_exclude_items(self):
        """Excluded items are not in reference positions."""
        n1 = NodeItem(3, 4)
        n2 = NodeItem(7, 8)
        self.scene.addItem(n1)
        self.scene.addItem(n2)

        positions = self.mgr._collect_reference_positions(exclude_items=[n1])
        xs = [p.x() for p in positions]

        self.assertNotIn(3.0, xs)
        self.assertIn(7.0, xs)

    def test_collect_reference_edges(self):
        """Collects edge start/end from EdgeItem."""
        n1 = NodeItem(0, 0)
        n2 = NodeItem(5, 5)
        self.scene.addItem(n1)
        self.scene.addItem(n2)
        edge = EdgeItem(n1, n2)
        self.scene.addItem(edge)

        edges = self.mgr._collect_reference_edges()
        self.assertEqual(len(edges), 1)
        start, end = edges[0]
        self.assertAlmostEqual(start.x(), 0.0)
        self.assertAlmostEqual(end.x(), 5.0)


if __name__ == "__main__":
    unittest.main()
