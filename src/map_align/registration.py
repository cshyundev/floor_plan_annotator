"""Registration algorithm abstraction for point cloud alignment."""

from typing import NamedTuple

import numpy as np
import open3d as o3d


class RegistrationResult(NamedTuple):
    """Result of a registration algorithm."""
    transform: np.ndarray    # 4x4 homogeneous matrix
    fitness: float           # Overlap ratio [0, 1]
    inlier_rmse: float       # RMSE of inlier correspondences (meters)


class RegistrationAlgorithm:
    """Base class for registration algorithms."""

    def run(
        self,
        source: o3d.geometry.PointCloud,
        target: o3d.geometry.PointCloud,
        initial_transform: np.ndarray,
    ) -> RegistrationResult:
        """Run the registration algorithm.

        Args:
            source: Source point cloud to align.
            target: Target (reference) point cloud.
            initial_transform: 4x4 initial alignment guess.

        Returns:
            RegistrationResult with refined transform, fitness, and RMSE.
        """
        raise NotImplementedError


class PointToPointICP(RegistrationAlgorithm):
    """Open3D Point-to-Point ICP registration."""

    def __init__(
        self,
        max_correspondence_distance: float = 0.5,
        max_iteration: int = 200,
    ):
        self._max_correspondence_distance = max_correspondence_distance
        self._max_iteration = max_iteration

    def run(
        self,
        source: o3d.geometry.PointCloud,
        target: o3d.geometry.PointCloud,
        initial_transform: np.ndarray,
    ) -> RegistrationResult:
        """Run Point-to-Point ICP alignment.

        Args:
            source: Source point cloud to align.
            target: Target (reference) point cloud.
            initial_transform: 4x4 initial alignment guess.

        Returns:
            RegistrationResult with refined transform, fitness, and RMSE.
        """
        result = o3d.pipelines.registration.registration_icp(
            source,
            target,
            self._max_correspondence_distance,
            initial_transform,
            o3d.pipelines.registration.TransformationEstimationPointToPoint(),
            o3d.pipelines.registration.ICPConvergenceCriteria(
                max_iteration=self._max_iteration,
            ),
        )
        return RegistrationResult(
            transform=np.array(result.transformation),
            fitness=result.fitness,
            inlier_rmse=result.inlier_rmse,
        )
