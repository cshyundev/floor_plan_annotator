"""Pure geometric utilities for annotation edge computations."""

import math

from PyQt6.QtCore import QPointF


def compute_hv_status(
    a: QPointF, b: QPointF, threshold: float,
) -> tuple[bool, float, str | None]:
    """Check whether a line segment is horizontal or vertical.

    Args:
        a: Start point of the segment.
        b: End point of the segment.
        threshold: Maximum angle in degrees to consider H/V.

    Returns:
        (is_hv, deviation_deg, label) where label is
        "Horizontal", "Vertical", or None.
    """
    dx = b.x() - a.x()
    dy = b.y() - a.y()
    angle = math.degrees(math.atan2(abs(dy), abs(dx)))
    if angle <= threshold:
        return True, angle, "Horizontal"
    elif angle >= 90 - threshold:
        return True, 90 - angle, "Vertical"
    else:
        return False, min(angle, 90 - angle), None


def compute_aligned_positions(
    a: QPointF, b: QPointF, direction: str,
) -> tuple[QPointF, QPointF]:
    """Compute positions that align a line segment to horizontal or vertical.

    Args:
        a: Start point of the segment.
        b: End point of the segment.
        direction: "horizontal" or "vertical".

    Returns:
        (new_a, new_b) as QPointF pair.
    """
    if direction == "horizontal":
        avg_y = (a.y() + b.y()) / 2
        return QPointF(a.x(), avg_y), QPointF(b.x(), avg_y)
    else:
        avg_x = (a.x() + b.x()) / 2
        return QPointF(avg_x, a.y()), QPointF(avg_x, b.y())
