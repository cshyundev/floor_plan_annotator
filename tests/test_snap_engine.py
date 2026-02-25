"""Unit tests for SnapEngine — pure computation, no Qt scene dependencies."""

import math
import pytest
from PyQt6.QtCore import QPointF

from src.gui.snap.snap_engine import SnapEngine, SnapResult, GuideLine


@pytest.fixture
def engine():
    return SnapEngine()


# ────────────────────────────────────────
# compute_angle_snap
# ────────────────────────────────────────

class TestAngleSnap:
    """Tests for global angle snapping (H/V and configurable angle sets)."""

    ANGLE_SET_HV = [0, 90, 180, 270]
    THRESHOLD = 5.0
    EXTENT = 100.0

    def test_snap_horizontal_right(self, engine):
        """Cursor at ~3° from horizontal → snaps to exactly 0°."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 0.5)  # ~2.86°
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert result.was_snapped
        assert abs(result.snapped_pos.y() - 0) < 1e-6  # Y should be exactly 0
        assert result.snapped_pos.x() > 0  # Should be to the right
        assert len(result.guides) == 1
        assert result.guides[0].guide_type == "orthogonal"

    def test_snap_horizontal_left(self, engine):
        """Cursor going left at ~178° → snaps to 180°."""
        anchor = QPointF(0, 0)
        cursor = QPointF(-10, 0.3)
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert result.was_snapped
        assert abs(result.snapped_pos.y() - 0) < 1e-6

    def test_snap_vertical_down(self, engine):
        """Cursor at ~88° → snaps to 90° (downward in scene coords)."""
        anchor = QPointF(0, 0)
        cursor = QPointF(0.3, 10)
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 0) < 1e-6

    def test_snap_vertical_up(self, engine):
        """Cursor at ~272° → snaps to 270° (upward)."""
        anchor = QPointF(0, 0)
        cursor = QPointF(0.3, -10)
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 0) < 1e-6

    def test_no_snap_diagonal(self, engine):
        """Cursor at 45° — outside threshold for H/V → no snap."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 10)  # Exactly 45°
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert not result.was_snapped
        assert len(result.guides) == 0

    def test_preserves_distance(self, engine):
        """Snapped point should be same distance from anchor as original cursor."""
        anchor = QPointF(5, 3)
        cursor = QPointF(15, 3.4)  # ~2.3° from horizontal
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert result.was_snapped
        original_dist = math.sqrt((cursor.x() - anchor.x())**2 + (cursor.y() - anchor.y())**2)
        snapped_dist = math.sqrt(
            (result.snapped_pos.x() - anchor.x())**2 +
            (result.snapped_pos.y() - anchor.y())**2
        )
        assert abs(original_dist - snapped_dist) < 1e-6

    def test_zero_distance_no_snap(self, engine):
        """Cursor at same position as anchor → no snap."""
        anchor = QPointF(5, 5)
        cursor = QPointF(5, 5)
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert not result.was_snapped

    def test_snap_with_45_angle_set(self, engine):
        """With extended angle set including 45°, diagonal should snap."""
        angle_set = [0, 45, 90, 135, 180, 225, 270, 315]
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 10.5)  # ~46.3°, within 5° of 45
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, angle_set, self.EXTENT)

        assert result.was_snapped
        # At 45°, x and y should be equal
        dx = result.snapped_pos.x() - anchor.x()
        dy = result.snapped_pos.y() - anchor.y()
        assert abs(dx - dy) < 1e-6

    def test_wraparound_near_360(self, engine):
        """Cursor at ~358° (near 0°) should snap to 0°."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, -0.3)  # Just below horizontal, ~358°
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert result.was_snapped
        assert abs(result.snapped_pos.y() - 0) < 1e-6

    def test_threshold_boundary_inside(self, engine):
        """Cursor at exactly threshold-1° should snap."""
        anchor = QPointF(0, 0)
        angle_rad = math.radians(4.0)  # 4° < 5° threshold
        cursor = QPointF(10 * math.cos(angle_rad), 10 * math.sin(angle_rad))
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert result.was_snapped

    def test_threshold_boundary_outside(self, engine):
        """Cursor at exactly threshold+1° should not snap."""
        anchor = QPointF(0, 0)
        angle_rad = math.radians(6.0)  # 6° > 5° threshold
        cursor = QPointF(10 * math.cos(angle_rad), 10 * math.sin(angle_rad))
        result = engine.compute_angle_snap(anchor, cursor, self.THRESHOLD, self.ANGLE_SET_HV, self.EXTENT)

        assert not result.was_snapped


# ────────────────────────────────────────
# compute_relative_snap
# ────────────────────────────────────────

class TestRelativeSnap:
    """Tests for relative snapping (parallel/perpendicular to existing edges)."""

    THRESHOLD = 5.0
    OFFSETS = [0, 90]  # parallel + perpendicular
    EXTENT = 100.0

    def test_parallel_to_horizontal_edge(self, engine):
        """New line parallel to an existing horizontal edge → snaps."""
        anchor = QPointF(0, 5)
        cursor = QPointF(10, 5.3)  # ~1.7° from horizontal
        ref_edges = [(QPointF(0, 0), QPointF(10, 0))]  # Horizontal edge

        result = engine.compute_relative_snap(
            anchor, cursor, ref_edges, self.THRESHOLD, self.OFFSETS, self.EXTENT
        )

        assert result.was_snapped
        assert abs(result.snapped_pos.y() - 5) < 1e-6
        assert result.guides[0].guide_type == "relative"

    def test_perpendicular_to_horizontal_edge(self, engine):
        """New line perpendicular to horizontal edge (vertical) → snaps."""
        anchor = QPointF(5, 0)
        cursor = QPointF(5.3, 10)  # ~88.3°, within 5° of 90
        ref_edges = [(QPointF(0, 0), QPointF(10, 0))]  # Horizontal edge

        result = engine.compute_relative_snap(
            anchor, cursor, ref_edges, self.THRESHOLD, self.OFFSETS, self.EXTENT
        )

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 5) < 1e-6

    def test_parallel_to_diagonal_edge(self, engine):
        """New line parallel to a 45° edge → snaps to 45°."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 10.5)  # ~46.3°, within 5° of 45°
        ref_edges = [(QPointF(0, 0), QPointF(5, 5))]  # 45° edge

        result = engine.compute_relative_snap(
            anchor, cursor, ref_edges, self.THRESHOLD, self.OFFSETS, self.EXTENT
        )

        assert result.was_snapped
        dx = result.snapped_pos.x() - anchor.x()
        dy = result.snapped_pos.y() - anchor.y()
        assert abs(dx - dy) < 1e-6

    def test_perpendicular_to_diagonal_edge(self, engine):
        """New line perpendicular to 45° edge → snaps to 135°."""
        anchor = QPointF(0, 0)
        # 135° = going up-left, so cursor at ~133°
        angle_rad = math.radians(133.0)
        cursor = QPointF(10 * math.cos(angle_rad), 10 * math.sin(angle_rad))
        ref_edges = [(QPointF(0, 0), QPointF(5, 5))]  # 45° edge

        result = engine.compute_relative_snap(
            anchor, cursor, ref_edges, self.THRESHOLD, self.OFFSETS, self.EXTENT
        )

        assert result.was_snapped

    def test_no_snap_unrelated_angle(self, engine):
        """New line at 30° with a horizontal edge → no snap (not parallel/perpendicular)."""
        anchor = QPointF(0, 0)
        angle_rad = math.radians(30.0)
        cursor = QPointF(10 * math.cos(angle_rad), 10 * math.sin(angle_rad))
        ref_edges = [(QPointF(0, 0), QPointF(10, 0))]  # Horizontal

        result = engine.compute_relative_snap(
            anchor, cursor, ref_edges, self.THRESHOLD, self.OFFSETS, self.EXTENT
        )

        assert not result.was_snapped

    def test_opposite_direction_parallel(self, engine):
        """Line going in opposite direction of reference edge should still snap as parallel."""
        anchor = QPointF(10, 0)
        cursor = QPointF(0, 0.3)  # Going left, ~178.3°, parallel to rightward edge
        ref_edges = [(QPointF(0, 5), QPointF(10, 5))]  # Horizontal, going right

        result = engine.compute_relative_snap(
            anchor, cursor, ref_edges, self.THRESHOLD, self.OFFSETS, self.EXTENT
        )

        assert result.was_snapped

    def test_no_reference_edges(self, engine):
        """No reference edges → no snap."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 0)
        result = engine.compute_relative_snap(
            anchor, cursor, [], self.THRESHOLD, self.OFFSETS, self.EXTENT
        )

        assert not result.was_snapped

    def test_zero_length_edge_ignored(self, engine):
        """Zero-length reference edges are ignored."""
        anchor = QPointF(0, 0)
        cursor = QPointF(10, 0.3)
        ref_edges = [(QPointF(5, 5), QPointF(5, 5))]  # Zero-length

        result = engine.compute_relative_snap(
            anchor, cursor, ref_edges, self.THRESHOLD, self.OFFSETS, self.EXTENT
        )

        assert not result.was_snapped


# ────────────────────────────────────────
# compute_alignment_snap
# ────────────────────────────────────────

class TestAlignmentSnap:
    """Tests for alignment snapping (X/Y match with existing positions)."""

    TOLERANCE = 0.5  # scene units (meters)

    def test_snap_x_only(self, engine):
        """Cursor X near reference X → snap X, keep Y."""
        cursor = QPointF(5.3, 10)
        refs = [QPointF(5, 3)]
        scene_min = QPointF(0, 0)
        scene_max = QPointF(20, 20)

        result = engine.compute_alignment_snap(cursor, refs, self.TOLERANCE, scene_min, scene_max)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 5) < 1e-6
        assert abs(result.snapped_pos.y() - 10) < 1e-6  # Y unchanged
        assert len(result.guides) == 1
        assert result.guides[0].guide_type == "alignment"
        # Vertical guide (for X alignment)
        assert abs(result.guides[0].start.x() - 5) < 1e-6

    def test_snap_y_only(self, engine):
        """Cursor Y near reference Y → snap Y, keep X."""
        cursor = QPointF(10, 3.2)
        refs = [QPointF(5, 3)]
        scene_min = QPointF(0, 0)
        scene_max = QPointF(20, 20)

        result = engine.compute_alignment_snap(cursor, refs, self.TOLERANCE, scene_min, scene_max)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 10) < 1e-6  # X unchanged
        assert abs(result.snapped_pos.y() - 3) < 1e-6

    def test_snap_both_axes(self, engine):
        """Cursor near reference on both X and Y → snap both."""
        cursor = QPointF(5.2, 3.1)
        refs = [QPointF(5, 3)]
        scene_min = QPointF(0, 0)
        scene_max = QPointF(20, 20)

        result = engine.compute_alignment_snap(cursor, refs, self.TOLERANCE, scene_min, scene_max)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 5) < 1e-6
        assert abs(result.snapped_pos.y() - 3) < 1e-6
        assert len(result.guides) == 2

    def test_snap_different_references(self, engine):
        """X snaps to one reference, Y to another."""
        cursor = QPointF(5.2, 8.3)
        refs = [QPointF(5, 3), QPointF(10, 8)]
        scene_min = QPointF(0, 0)
        scene_max = QPointF(20, 20)

        result = engine.compute_alignment_snap(cursor, refs, self.TOLERANCE, scene_min, scene_max)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 5) < 1e-6   # From first ref
        assert abs(result.snapped_pos.y() - 8) < 1e-6   # From second ref

    def test_no_snap_outside_tolerance(self, engine):
        """No reference within tolerance → no snap."""
        cursor = QPointF(10, 10)
        refs = [QPointF(5, 5)]  # Distance > tolerance on both axes
        scene_min = QPointF(0, 0)
        scene_max = QPointF(20, 20)

        result = engine.compute_alignment_snap(cursor, refs, self.TOLERANCE, scene_min, scene_max)

        assert not result.was_snapped
        assert abs(result.snapped_pos.x() - 10) < 1e-6
        assert abs(result.snapped_pos.y() - 10) < 1e-6

    def test_closest_reference_wins(self, engine):
        """Multiple references in tolerance → closest one wins."""
        cursor = QPointF(5.1, 10)
        refs = [QPointF(5, 3), QPointF(5.3, 7)]  # Both X within tolerance, 5.0 is closer
        scene_min = QPointF(0, 0)
        scene_max = QPointF(20, 20)

        result = engine.compute_alignment_snap(cursor, refs, self.TOLERANCE, scene_min, scene_max)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 5) < 1e-6

    def test_no_references(self, engine):
        """Empty reference list → no snap."""
        cursor = QPointF(10, 10)
        scene_min = QPointF(0, 0)
        scene_max = QPointF(20, 20)

        result = engine.compute_alignment_snap(cursor, [], self.TOLERANCE, scene_min, scene_max)

        assert not result.was_snapped


# ────────────────────────────────────────
# combine_results
# ────────────────────────────────────────

class TestCombineResults:
    """Tests for combining snap results with priority rules."""

    def test_angle_takes_priority(self, engine):
        """Angle snap overrides relative and alignment."""
        angle = SnapResult(QPointF(10, 0), True, [GuideLine(QPointF(0, 0), QPointF(20, 0), "orthogonal")])
        relative = SnapResult(QPointF(10, 1), True, [GuideLine(QPointF(0, 0), QPointF(20, 2), "relative")])
        alignment = SnapResult(QPointF(9, 0), True, [GuideLine(QPointF(9, -10), QPointF(9, 10), "alignment")])

        result = engine.combine_results(angle, relative, alignment)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 10) < 1e-6
        assert abs(result.snapped_pos.y() - 0) < 1e-6
        # Should have angle guide + alignment guide (as info)
        types = [g.guide_type for g in result.guides]
        assert "orthogonal" in types
        assert "alignment" in types

    def test_relative_when_no_angle(self, engine):
        """Relative snap used when angle didn't fire."""
        angle = SnapResult(QPointF(10, 1), False)
        relative = SnapResult(QPointF(10, 0.5), True, [GuideLine(QPointF(0, 0), QPointF(20, 1), "relative")])
        alignment = SnapResult(QPointF(9, 1), True, [GuideLine(QPointF(9, -10), QPointF(9, 10), "alignment")])

        result = engine.combine_results(angle, relative, alignment)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 10) < 1e-6
        assert abs(result.snapped_pos.y() - 0.5) < 1e-6

    def test_alignment_when_no_angle_or_relative(self, engine):
        """Alignment used when neither angle nor relative fired."""
        angle = SnapResult(QPointF(10, 5), False)
        relative = SnapResult(QPointF(10, 5), False)
        alignment = SnapResult(QPointF(9, 5), True, [GuideLine(QPointF(9, -10), QPointF(9, 10), "alignment")])

        result = engine.combine_results(angle, relative, alignment)

        assert result.was_snapped
        assert abs(result.snapped_pos.x() - 9) < 1e-6

    def test_no_snap_at_all(self, engine):
        """Nothing snapped → result is not snapped."""
        angle = SnapResult(QPointF(10, 5), False)
        relative = SnapResult(QPointF(10, 5), False)
        alignment = SnapResult(QPointF(10, 5), False)

        result = engine.combine_results(angle, relative, alignment)

        assert not result.was_snapped
        assert len(result.guides) == 0
