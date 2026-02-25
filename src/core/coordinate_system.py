"""Coordinate system abstraction for multi-convention 3D data support."""

from dataclasses import dataclass, field


@dataclass
class CoordinateSystem:
    """Describes how a 3D dataset's axes map to floor-plane and height.

    Attributes:
        up_axis: Which original axis is vertical (0=X, 1=Y, 2=Z).
        up_direction: +1 if positive values go up, -1 if negative.
        floor_axes: Tuple of two axis indices forming the floor plane
                    (first=horizontal/Point2D.x, second=vertical/Point2D.y).
        floor_level: Height value of the floor along the up axis.
        flip_floor_v: Whether to flip the second floor axis in 2D projection
                      (needed when positive direction is "down" on screen).
    """

    up_axis: int = 2
    up_direction: int = 1
    floor_axes: tuple[int, int] = (0, 1)
    floor_level: float = 0.0
    flip_floor_v: bool = True

    # ── Presets ───────────────────────────────────────────────────────────

    @classmethod
    def ros(cls) -> "CoordinateSystem":
        """ROS convention: Z-up, floor on XY plane."""
        return cls(
            up_axis=2,
            up_direction=1,
            floor_axes=(0, 1),
            floor_level=0.0,
            flip_floor_v=True,
        )

    @classmethod
    def opencv(cls) -> "CoordinateSystem":
        """OpenCV convention: Y-down, floor on XZ plane."""
        return cls(
            up_axis=1,
            up_direction=-1,
            floor_axes=(0, 2),
            floor_level=0.0,
            flip_floor_v=True,
        )

    @classmethod
    def opengl(cls) -> "CoordinateSystem":
        """OpenGL convention: Y-up, floor on XZ plane."""
        return cls(
            up_axis=1,
            up_direction=1,
            floor_axes=(0, 2),
            floor_level=0.0,
            flip_floor_v=False,
        )

    PRESET_NAMES = ("ros", "opencv", "opengl")

    @classmethod
    def from_preset(cls, name: str) -> "CoordinateSystem":
        if name not in cls.PRESET_NAMES:
            raise ValueError(
                f"Unknown coordinate system preset '{name}'. "
                f"Valid presets: {list(cls.PRESET_NAMES)}"
            )
        return getattr(cls, name)()

    # ── Serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "up_axis": self.up_axis,
            "up_direction": self.up_direction,
            "floor_axes": list(self.floor_axes),
            "floor_level": self.floor_level,
            "flip_floor_v": self.flip_floor_v,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CoordinateSystem":
        return cls(
            up_axis=d["up_axis"],
            up_direction=d["up_direction"],
            floor_axes=tuple(d["floor_axes"]),
            floor_level=d.get("floor_level", 0.0),
            flip_floor_v=d.get("flip_floor_v", True),
        )

    # ── Axis helpers ──────────────────────────────────────────────────────

    def height_column(self) -> int:
        """Numpy column index for the vertical (height) axis."""
        return self.up_axis

    def floor_column_h(self) -> int:
        """Numpy column index that maps to Point2D.x (horizontal on screen)."""
        return self.floor_axes[0]

    def floor_column_v(self) -> int:
        """Numpy column index that maps to Point2D.y (vertical on screen)."""
        return self.floor_axes[1]

    def make_3d_point(self, floor_h: float, floor_v: float, height: float) -> list:
        """Create a [x, y, z] list from floor-plane and height values.

        Places each value into the correct original-data axis position.
        For ROS (floor_axes=(0,1), up_axis=2): returns [floor_h, floor_v, height].
        For OpenCV (floor_axes=(0,2), up_axis=1): returns [floor_h, height, floor_v].
        """
        pt = [0.0, 0.0, 0.0]
        pt[self.floor_axes[0]] = floor_h
        pt[self.floor_axes[1]] = floor_v
        pt[self.up_axis] = height
        return pt

    def camera_up_vector(self) -> list[float]:
        """Return the screen-up direction for a top-down camera view.

        For a top-down view the camera looks along the up_axis.
        The screen-up direction must be perpendicular to the view direction,
        so we use the second floor axis (floor_v) as camera up.
        """
        v = [0.0, 0.0, 0.0]
        v[self.floor_axes[1]] = 1.0
        return v
