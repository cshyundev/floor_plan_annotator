"""Alignment state: tracks the current transform between source and reference."""

import copy
from dataclasses import dataclass, field

import numpy as np
import open3d as o3d


@dataclass
class AlignmentState:
    """Manages the current alignment transform (6DOF: tx, ty, tz, roll, pitch, yaw).

    The reference is fixed; the source is transformed.
    Display geometry can be TriangleMesh or PointCloud.
    """

    reference_cloud: o3d.geometry.PointCloud | None = None
    source_cloud: o3d.geometry.PointCloud | None = None

    # Display geometry — mesh or point cloud, rendered as-is
    reference_geom: o3d.geometry.TriangleMesh | o3d.geometry.PointCloud | None = None
    source_geom: o3d.geometry.TriangleMesh | o3d.geometry.PointCloud | None = None

    # Current 6DOF transform: translation (meters) + rotation (degrees)
    tx: float = 0.0
    ty: float = 0.0
    tz: float = 0.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0

    # ICP result metadata
    icp_fitness: float = 0.0
    icp_rmse: float = 0.0

    # File paths for output metadata
    reference_path: str = ""
    source_path: str = ""

    def reset_transform(self) -> None:
        """Reset transform to identity."""
        self.tx = 0.0
        self.ty = 0.0
        self.tz = 0.0
        self.roll_deg = 0.0
        self.pitch_deg = 0.0
        self.yaw_deg = 0.0
        self.icp_fitness = 0.0
        self.icp_rmse = 0.0

    def get_transform_4x4(self) -> np.ndarray:
        """Return the current transform as a 4x4 homogeneous matrix.

        Rotation order: R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
        """
        roll = np.radians(self.roll_deg)
        pitch = np.radians(self.pitch_deg)
        yaw = np.radians(self.yaw_deg)

        cr, sr = np.cos(roll), np.sin(roll)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)

        # Rz(yaw) @ Ry(pitch) @ Rx(roll)
        R = np.array([
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp,     cp * sr,                cp * cr],
        ])

        T = np.eye(4)
        T[:3, :3] = R
        T[0, 3] = self.tx
        T[1, 3] = self.ty
        T[2, 3] = self.tz
        return T

    def set_from_4x4(self, matrix: np.ndarray) -> None:
        """Extract 6DOF transform from a 4x4 matrix.

        Assumes rotation order: Rz(yaw) @ Ry(pitch) @ Rx(roll)
        """
        self.tx = float(matrix[0, 3])
        self.ty = float(matrix[1, 3])
        self.tz = float(matrix[2, 3])

        R = matrix[:3, :3]
        # pitch from -sp = R[2,0]
        sp = -R[2, 0]
        sp = np.clip(sp, -1.0, 1.0)
        pitch = np.arcsin(sp)

        cp = np.cos(pitch)
        if abs(cp) > 1e-6:
            self.roll_deg = float(np.degrees(np.arctan2(R[2, 1] / cp, R[2, 2] / cp)))
            self.yaw_deg = float(np.degrees(np.arctan2(R[1, 0] / cp, R[0, 0] / cp)))
        else:
            # Gimbal lock
            self.roll_deg = float(np.degrees(np.arctan2(-R[1, 2], R[1, 1])))
            self.yaw_deg = 0.0
        self.pitch_deg = float(np.degrees(pitch))

    def get_transformed_source_points(self) -> np.ndarray:
        """Return source points with the current transform applied.

        Returns:
            Nx3 numpy array of transformed points.
        """
        if self.source_cloud is None:
            return np.empty((0, 3))

        points = np.asarray(self.source_cloud.points)
        if len(points) == 0:
            return points

        T = self.get_transform_4x4()
        # Apply as homogeneous transform
        ones = np.ones((len(points), 1))
        pts_h = np.hstack([points, ones])  # Nx4
        transformed = (T @ pts_h.T).T[:, :3]  # Nx3
        return transformed

    def get_transformed_source_geom(self) -> o3d.geometry.TriangleMesh | o3d.geometry.PointCloud | None:
        """Return a copy of source display geometry with current transform applied."""
        if self.source_geom is None:
            return None
        geom = copy.deepcopy(self.source_geom)
        geom.transform(self.get_transform_4x4())
        return geom

    def get_source_centroid(self) -> tuple[float, float]:
        """Get centroid of original source cloud (for rotation center)."""
        if self.source_cloud is None:
            return (0.0, 0.0)
        points = np.asarray(self.source_cloud.points)
        if len(points) == 0:
            return (0.0, 0.0)
        return (float(points[:, 0].mean()), float(points[:, 1].mean()))
