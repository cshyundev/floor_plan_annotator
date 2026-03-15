"""Tests for registration algorithm abstraction."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.map_align.registration import (
    RegistrationAlgorithm,
    RegistrationResult,
    PointToPointICP,
)


class TestRegistrationResult:
    def test_fields(self):
        tf = np.eye(4)
        r = RegistrationResult(transform=tf, fitness=0.95, inlier_rmse=0.01)
        np.testing.assert_array_equal(r.transform, tf)
        assert r.fitness == 0.95
        assert r.inlier_rmse == 0.01

    def test_named_access(self):
        r = RegistrationResult(np.eye(4), 0.5, 0.1)
        assert r[1] == 0.5
        assert r[2] == 0.1


class TestRegistrationAlgorithm:
    def test_base_raises_not_implemented(self):
        algo = RegistrationAlgorithm()
        with pytest.raises(NotImplementedError):
            algo.run(None, None, np.eye(4))


class TestPointToPointICP:
    @patch("src.map_align.registration.o3d")
    def test_run_calls_open3d(self, mock_o3d):
        # Set up mock return value
        mock_result = MagicMock()
        mock_result.transformation = np.eye(4)
        mock_result.fitness = 0.92
        mock_result.inlier_rmse = 0.03
        mock_o3d.pipelines.registration.registration_icp.return_value = mock_result

        source = MagicMock()
        target = MagicMock()
        init_tf = np.eye(4)

        algo = PointToPointICP(max_correspondence_distance=0.5, max_iteration=100)
        result = algo.run(source, target, init_tf)

        # Verify Open3D was called
        mock_o3d.pipelines.registration.registration_icp.assert_called_once()
        call_args = mock_o3d.pipelines.registration.registration_icp.call_args
        assert call_args[0][0] is source
        assert call_args[0][1] is target
        assert call_args[0][2] == 0.5
        np.testing.assert_array_equal(call_args[0][3], init_tf)

        # Verify convergence criteria
        mock_o3d.pipelines.registration.ICPConvergenceCriteria.assert_called_once_with(
            max_iteration=100,
        )

        # Verify result
        assert isinstance(result, RegistrationResult)
        np.testing.assert_array_equal(result.transform, np.eye(4))
        assert result.fitness == 0.92
        assert result.inlier_rmse == 0.03

    @patch("src.map_align.registration.o3d")
    def test_default_parameters(self, mock_o3d):
        mock_result = MagicMock()
        mock_result.transformation = np.eye(4)
        mock_result.fitness = 0.0
        mock_result.inlier_rmse = 0.0
        mock_o3d.pipelines.registration.registration_icp.return_value = mock_result

        algo = PointToPointICP()
        algo.run(MagicMock(), MagicMock(), np.eye(4))

        call_args = mock_o3d.pipelines.registration.registration_icp.call_args
        assert call_args[0][2] == 0.5  # default max_correspondence_distance
        mock_o3d.pipelines.registration.ICPConvergenceCriteria.assert_called_once_with(
            max_iteration=200,  # default max_iteration
        )
