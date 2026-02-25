"""Pure computation for snapping logic. No scene/graphics dependencies."""

import math
from dataclasses import dataclass, field

from PyQt6.QtCore import QPointF


@dataclass
class GuideLine:
    """A guide line to display in the scene."""
    start: QPointF
    end: QPointF
    guide_type: str  # "orthogonal" | "alignment" | "relative"


@dataclass
class SnapResult:
    """Result of a snap computation."""
    snapped_pos: QPointF
    was_snapped: bool
    guides: list[GuideLine] = field(default_factory=list)


class SnapEngine:
    """Pure computation for snapping logic. No scene/graphics dependencies."""

    def compute_angle_snap(
        self,
        anchor: QPointF,
        cursor: QPointF,
        angle_threshold: float,
        angle_set: list[float],
        scene_extent: float,
    ) -> SnapResult:
        """Snap cursor to exact angle if within threshold of any angle in angle_set.

        Args:
            anchor: The fixed previous node position.
            cursor: Current cursor position.
            angle_threshold: Maximum angle difference in degrees to trigger snap.
            angle_set: List of snap angles in degrees (e.g. [0, 90, 180, 270]).
            scene_extent: Length for guide line extension.

        Returns:
            SnapResult with snapped position and guide lines.
        """
        dx = cursor.x() - anchor.x()
        dy = cursor.y() - anchor.y()
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 1e-9:
            return SnapResult(snapped_pos=QPointF(cursor), was_snapped=False)

        angle_deg = math.degrees(math.atan2(dy, dx))
        if angle_deg < 0:
            angle_deg += 360.0

        best_snap_angle = None
        best_diff = float("inf")

        for snap_angle in angle_set:
            diff = abs(angle_deg - snap_angle)
            diff = min(diff, 360.0 - diff)  # Handle wraparound
            if diff < angle_threshold and diff < best_diff:
                best_diff = diff
                best_snap_angle = snap_angle

        if best_snap_angle is None:
            return SnapResult(snapped_pos=QPointF(cursor), was_snapped=False)

        snap_rad = math.radians(best_snap_angle)
        cos_a = math.cos(snap_rad)
        sin_a = math.sin(snap_rad)

        snapped = QPointF(
            anchor.x() + distance * cos_a,
            anchor.y() + distance * sin_a,
        )

        guide_start = QPointF(
            anchor.x() - scene_extent * cos_a,
            anchor.y() - scene_extent * sin_a,
        )
        guide_end = QPointF(
            anchor.x() + scene_extent * cos_a,
            anchor.y() + scene_extent * sin_a,
        )

        return SnapResult(
            snapped_pos=snapped,
            was_snapped=True,
            guides=[GuideLine(guide_start, guide_end, "orthogonal")],
        )

    def compute_relative_snap(
        self,
        anchor: QPointF,
        cursor: QPointF,
        reference_edges: list[tuple[QPointF, QPointF]],
        angle_threshold: float,
        relative_offsets: list[float],
        scene_extent: float,
    ) -> SnapResult:
        """Snap cursor to be parallel/perpendicular to existing edges.

        For each existing edge, compute its angle and add each offset from
        relative_offsets. If the new line segment's angle is within threshold
        of any of these computed angles, snap to that angle.

        Args:
            anchor: The fixed previous node position.
            cursor: Current cursor position.
            reference_edges: List of (start, end) tuples for existing edges.
            angle_threshold: Maximum angle difference in degrees.
            relative_offsets: Angle offsets to check (e.g. [0, 90] for parallel/perpendicular).
            scene_extent: Length for guide line extension.

        Returns:
            SnapResult with snapped position and guide lines.
        """
        dx = cursor.x() - anchor.x()
        dy = cursor.y() - anchor.y()
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 1e-9:
            return SnapResult(snapped_pos=QPointF(cursor), was_snapped=False)

        cursor_angle = math.degrees(math.atan2(dy, dx))
        if cursor_angle < 0:
            cursor_angle += 360.0

        best_snap_angle = None
        best_diff = float("inf")

        for start, end in reference_edges:
            edge_dx = end.x() - start.x()
            edge_dy = end.y() - start.y()
            if edge_dx * edge_dx + edge_dy * edge_dy < 1e-9:
                continue

            edge_angle = math.degrees(math.atan2(edge_dy, edge_dx))
            if edge_angle < 0:
                edge_angle += 360.0

            for offset in relative_offsets:
                # Check both the angle and angle+180 (opposite direction)
                for candidate in [
                    (edge_angle + offset) % 360.0,
                    (edge_angle + offset + 180.0) % 360.0,
                ]:
                    diff = abs(cursor_angle - candidate)
                    diff = min(diff, 360.0 - diff)
                    if diff < angle_threshold and diff < best_diff:
                        best_diff = diff
                        best_snap_angle = candidate

        if best_snap_angle is None:
            return SnapResult(snapped_pos=QPointF(cursor), was_snapped=False)

        snap_rad = math.radians(best_snap_angle)
        cos_a = math.cos(snap_rad)
        sin_a = math.sin(snap_rad)

        snapped = QPointF(
            anchor.x() + distance * cos_a,
            anchor.y() + distance * sin_a,
        )

        guide_start = QPointF(
            anchor.x() - scene_extent * cos_a,
            anchor.y() - scene_extent * sin_a,
        )
        guide_end = QPointF(
            anchor.x() + scene_extent * cos_a,
            anchor.y() + scene_extent * sin_a,
        )

        return SnapResult(
            snapped_pos=snapped,
            was_snapped=True,
            guides=[GuideLine(guide_start, guide_end, "relative")],
        )

    def compute_alignment_snap(
        self,
        cursor: QPointF,
        reference_positions: list[QPointF],
        tolerance: float,
        scene_rect_min: QPointF,
        scene_rect_max: QPointF,
    ) -> SnapResult:
        """Check if cursor X or Y aligns with any reference position.

        X and Y are evaluated independently, so the cursor can snap to
        X-alignment with one reference and Y-alignment with another.

        Args:
            cursor: Current cursor position.
            reference_positions: Positions of existing nodes/objects.
            tolerance: Distance tolerance in scene units (meters).
            scene_rect_min: Top-left of visible scene (for guide extent).
            scene_rect_max: Bottom-right of visible scene (for guide extent).

        Returns:
            SnapResult with snapped position and guide lines.
        """
        snapped_x = cursor.x()
        snapped_y = cursor.y()
        guides: list[GuideLine] = []
        x_snapped = False
        y_snapped = False

        best_x_diff = tolerance
        best_y_diff = tolerance

        for ref in reference_positions:
            dx = abs(cursor.x() - ref.x())
            dy = abs(cursor.y() - ref.y())

            if dx < best_x_diff:
                best_x_diff = dx
                snapped_x = ref.x()
                x_snapped = True

            if dy < best_y_diff:
                best_y_diff = dy
                snapped_y = ref.y()
                y_snapped = True

        if x_snapped:
            guides.append(GuideLine(
                QPointF(snapped_x, scene_rect_min.y()),
                QPointF(snapped_x, scene_rect_max.y()),
                "alignment",
            ))

        if y_snapped:
            guides.append(GuideLine(
                QPointF(scene_rect_min.x(), snapped_y),
                QPointF(scene_rect_max.x(), snapped_y),
                "alignment",
            ))

        return SnapResult(
            snapped_pos=QPointF(snapped_x, snapped_y),
            was_snapped=(x_snapped or y_snapped),
            guides=guides,
        )

    def combine_results(
        self,
        angle_result: SnapResult,
        relative_result: SnapResult,
        alignment_result: SnapResult,
    ) -> SnapResult:
        """Combine results with priority: angle > relative > alignment.

        If angle snap fired, use its position. Else if relative snap fired,
        use its position. In both cases, alignment guides are shown but don't
        override the snapped position. If neither angle nor relative snapped,
        use alignment-snapped position.
        """
        guides: list[GuideLine] = []

        if angle_result.was_snapped:
            pos = QPointF(angle_result.snapped_pos)
            guides.extend(angle_result.guides)
            # Show alignment guides as info but don't adjust position
            guides.extend(alignment_result.guides)
        elif relative_result.was_snapped:
            pos = QPointF(relative_result.snapped_pos)
            guides.extend(relative_result.guides)
            guides.extend(alignment_result.guides)
        elif alignment_result.was_snapped:
            pos = QPointF(alignment_result.snapped_pos)
            guides.extend(alignment_result.guides)
        else:
            return SnapResult(
                snapped_pos=QPointF(angle_result.snapped_pos),
                was_snapped=False,
            )

        return SnapResult(snapped_pos=pos, was_snapped=True, guides=guides)
