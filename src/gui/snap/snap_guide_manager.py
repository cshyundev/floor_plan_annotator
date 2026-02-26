"""Scene-aware snap manager: creates/removes guide lines, delegates to SnapEngine."""

import math

from PyQt6.QtWidgets import QGraphicsLineItem
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtCore import Qt, QPointF, QLineF

from src.core.config import ConfigManager
from src.gui.snap.snap_engine import SnapEngine, SnapResult, GuideLine


class SnapGuideManager:
    """Manages snap computation and visual guide lines in the scene.

    Owned by Canvas2D. Used by tools and items to:
    1. Compute snapped positions.
    2. Display/remove visual guide lines.
    """

    def __init__(self, scene, canvas):
        self._scene = scene
        self._canvas = canvas
        self._engine = SnapEngine()
        self._config = ConfigManager.instance()
        self._active_guides: list[QGraphicsLineItem] = []

    def snap_drawing_point(
        self,
        cursor_pos: QPointF,
        anchor_pos: QPointF | None = None,
        modifiers=None,
    ) -> QPointF:
        """Compute snapped position for a drawing tool.

        Applies angle snap + relative snap (if anchor provided) + alignment snap.
        Shows guide lines. Returns the snapped position.
        """
        self.clear_guides()

        if not self._is_snap_active(modifiers):
            return QPointF(cursor_pos)

        scene_extent = self._get_scene_extent()
        threshold = self._config.get_ui_value("snap", "angle_threshold")
        angle_set = self._config.get_ui_value("snap", "angle_set")

        # Angle snap (global H/V)
        if anchor_pos is not None:
            angle_result = self._engine.compute_angle_snap(
                anchor_pos, cursor_pos, threshold, angle_set, scene_extent,
            )
        else:
            angle_result = SnapResult(QPointF(cursor_pos), False)

        # Relative snap (parallel/perpendicular to existing edges)
        if anchor_pos is not None and self._config.get_ui_value("snap", "relative_snap"):
            ref_edges = self._collect_reference_edges()
            offsets = self._config.get_ui_value("snap", "relative_offsets")
            relative_result = self._engine.compute_relative_snap(
                anchor_pos, cursor_pos, ref_edges, threshold, offsets, scene_extent,
            )
        else:
            relative_result = SnapResult(QPointF(cursor_pos), False)

        # Alignment snap (X/Y alignment with existing positions)
        ref_positions = self._collect_reference_positions()
        tolerance_scene = self._get_alignment_tolerance_scene()
        scene_min, scene_max = self._get_visible_scene_rect()
        alignment_result = self._engine.compute_alignment_snap(
            cursor_pos, ref_positions, tolerance_scene, scene_min, scene_max,
        )

        # Combine with priority
        combined = self._engine.combine_results(angle_result, relative_result, alignment_result)

        if combined.guides:
            self._show_guides(combined)

        return QPointF(combined.snapped_pos)

    def snap_drag_point(
        self,
        cursor_pos: QPointF,
        exclude_items: list | None = None,
        modifiers=None,
    ) -> QPointF:
        """Compute snapped position during item drag (guide-only for now).

        Only alignment snap (no angle snap during drag).
        Shows guide lines. Returns original cursor position (no auto-correction in Phase 1).
        """
        self.clear_guides()

        if not self._is_snap_active(modifiers):
            return QPointF(cursor_pos)

        ref_positions = self._collect_reference_positions(exclude_items)
        tolerance_scene = self._get_alignment_tolerance_scene()
        scene_min, scene_max = self._get_visible_scene_rect()

        result = self._engine.compute_alignment_snap(
            cursor_pos, ref_positions, tolerance_scene, scene_min, scene_max,
        )

        if result.guides:
            self._show_guides(result)

        # Phase 1: return original position (guide-only, no position forcing)
        return QPointF(cursor_pos)

    def snap_rotation_angle(
        self,
        center: QPointF,
        angle_deg: float,
        modifiers=None,
    ) -> float:
        """Snap a rotation angle to the nearest configured snap angle.

        Shows a guide line through *center* at the snapped direction.
        Returns the (possibly snapped) angle in degrees.
        """
        self.clear_guides()

        if not self._is_snap_active(modifiers):
            return angle_deg

        threshold = self._config.get_ui_value("snap", "angle_threshold")
        angle_set = self._config.get_ui_value("snap", "angle_set")

        normalized = angle_deg % 360
        if normalized < 0:
            normalized += 360

        best_snap = None
        best_diff = float("inf")

        for snap_angle in angle_set:
            diff = abs(normalized - snap_angle)
            diff = min(diff, 360.0 - diff)
            if diff < threshold and diff < best_diff:
                best_diff = diff
                best_snap = snap_angle

        if best_snap is None:
            return angle_deg

        extent = self._get_scene_extent()
        guide_rad = math.radians(best_snap)
        cos_a = math.cos(guide_rad)
        sin_a = math.sin(guide_rad)

        guide = GuideLine(
            QPointF(center.x() - extent * cos_a, center.y() - extent * sin_a),
            QPointF(center.x() + extent * cos_a, center.y() + extent * sin_a),
            "orthogonal",
        )
        result = SnapResult(
            snapped_pos=center,
            was_snapped=True,
            guides=[guide],
        )
        self._show_guides(result)

        return best_snap

    def clear_guides(self):
        """Remove all active guide lines from the scene."""
        for item in self._active_guides:
            if item.scene() is not None:
                self._scene.removeItem(item)
        self._active_guides.clear()

    # ─── Internal helpers ────────────────────────────────────────────

    def _is_snap_active(self, modifiers=None) -> bool:
        """Check if snapping is active (config + Shift toggle)."""
        enabled = self._config.get_ui_value("snap", "enabled")
        if modifiers is not None:
            shift_held = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
            return enabled ^ shift_held  # XOR: Shift toggles
        return enabled

    def _collect_reference_positions(self, exclude_items=None) -> list[QPointF]:
        """Collect positions of all NodeItem and ObjectItem centers in the scene."""
        from src.gui.items.nodes import NodeItem
        from src.gui.items.object_item import ObjectItem

        exclude = set(exclude_items) if exclude_items else set()
        positions: list[QPointF] = []

        for item in self._scene.items():
            if item in exclude:
                continue
            if isinstance(item, NodeItem):
                positions.append(QPointF(item.pos()))
            elif isinstance(item, ObjectItem):
                positions.append(QPointF(item.center))

        return positions

    def _collect_reference_edges(self, exclude_items=None) -> list[tuple[QPointF, QPointF]]:
        """Collect start/end positions of all EdgeItem in the scene."""
        from src.gui.items.nodes import EdgeItem

        exclude = set(exclude_items) if exclude_items else set()
        edges: list[tuple[QPointF, QPointF]] = []

        for item in self._scene.items():
            if item in exclude:
                continue
            if isinstance(item, EdgeItem):
                edges.append((
                    QPointF(item.start_node.pos()),
                    QPointF(item.end_node.pos()),
                ))

        return edges

    def _get_alignment_tolerance_scene(self) -> float:
        """Convert pixel tolerance to scene meters based on current zoom."""
        tolerance_px = self._config.get_ui_value("snap", "alignment_tolerance")
        zoom = self._canvas.transform().m11()
        return tolerance_px / zoom if zoom > 0 else tolerance_px

    def _get_scene_extent(self) -> float:
        """Get a reasonable extent for guide lines based on scene rect."""
        rect = self._scene.sceneRect()
        return max(rect.width(), rect.height(), 10.0)

    def _get_visible_scene_rect(self) -> tuple[QPointF, QPointF]:
        """Get visible scene rect as (min, max) QPointF pair."""
        rect = self._scene.sceneRect()
        return QPointF(rect.left(), rect.top()), QPointF(rect.right(), rect.bottom())

    def _show_guides(self, result: SnapResult):
        """Create QGraphicsLineItems for each guide and add to scene."""
        z_value = self._config.get_ui_value("snap", "guide_z_value")

        for guide in result.guides:
            color = self._get_guide_color(guide.guide_type)
            pen = QPen(color, 0)  # Cosmetic pen: always 1px regardless of zoom
            pen.setStyle(Qt.PenStyle.DashLine)

            line_item = QGraphicsLineItem(QLineF(guide.start, guide.end))
            line_item.setPen(pen)
            line_item.setZValue(z_value)
            self._scene.addItem(line_item)
            self._active_guides.append(line_item)

    def _get_guide_color(self, guide_type: str) -> QColor:
        """Get guide line color based on type."""
        color_key = {
            "orthogonal": ("snap", "orthogonal_color"),
            "relative": ("snap", "relative_color"),
            "alignment": ("snap", "alignment_color"),
        }
        keys = color_key.get(guide_type, ("snap", "alignment_color"))
        return self._config.get_color(*keys)
