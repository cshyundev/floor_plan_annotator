"""Tests for CoordinateSystem core module."""

import unittest
import numpy as np
from src.core.coordinate_system import CoordinateSystem


class TestPresets(unittest.TestCase):
    """Test preset coordinate systems."""

    def test_ros_preset(self):
        cs = CoordinateSystem.ros()
        self.assertEqual(cs.up_axis, 2)
        self.assertEqual(cs.up_direction, 1)
        self.assertEqual(cs.floor_axes, (0, 1))
        self.assertTrue(cs.flip_floor_v)

    def test_opencv_preset(self):
        cs = CoordinateSystem.opencv()
        self.assertEqual(cs.up_axis, 1)
        self.assertEqual(cs.up_direction, -1)
        self.assertEqual(cs.floor_axes, (0, 2))
        self.assertTrue(cs.flip_floor_v)

    def test_opengl_preset(self):
        cs = CoordinateSystem.opengl()
        self.assertEqual(cs.up_axis, 1)
        self.assertEqual(cs.up_direction, 1)
        self.assertEqual(cs.floor_axes, (0, 2))
        self.assertFalse(cs.flip_floor_v)

    def test_from_preset_valid(self):
        for name in ("ros", "opencv", "opengl"):
            cs = CoordinateSystem.from_preset(name)
            self.assertIsInstance(cs, CoordinateSystem)

    def test_from_preset_invalid(self):
        with self.assertRaises(ValueError):
            CoordinateSystem.from_preset("invalid")

    def test_default_is_ros(self):
        cs = CoordinateSystem()
        ros = CoordinateSystem.ros()
        self.assertEqual(cs.up_axis, ros.up_axis)
        self.assertEqual(cs.up_direction, ros.up_direction)
        self.assertEqual(cs.floor_axes, ros.floor_axes)
        self.assertEqual(cs.flip_floor_v, ros.flip_floor_v)


class TestSerialization(unittest.TestCase):
    """Test to_dict / from_dict round-trip."""

    def test_round_trip_ros(self):
        cs = CoordinateSystem.ros()
        d = cs.to_dict()
        cs2 = CoordinateSystem.from_dict(d)
        self.assertEqual(cs, cs2)

    def test_round_trip_opencv(self):
        cs = CoordinateSystem.opencv()
        d = cs.to_dict()
        cs2 = CoordinateSystem.from_dict(d)
        self.assertEqual(cs, cs2)

    def test_round_trip_opengl(self):
        cs = CoordinateSystem.opengl()
        d = cs.to_dict()
        cs2 = CoordinateSystem.from_dict(d)
        self.assertEqual(cs, cs2)

    def test_round_trip_custom(self):
        cs = CoordinateSystem(
            up_axis=0, up_direction=-1, floor_axes=(1, 2),
            floor_level=1.5, flip_floor_v=False,
        )
        d = cs.to_dict()
        cs2 = CoordinateSystem.from_dict(d)
        self.assertEqual(cs, cs2)

    def test_dict_keys(self):
        d = CoordinateSystem.ros().to_dict()
        expected_keys = {"up_axis", "up_direction", "floor_axes", "floor_level", "flip_floor_v"}
        self.assertEqual(set(d.keys()), expected_keys)

    def test_floor_axes_serialized_as_list(self):
        d = CoordinateSystem.ros().to_dict()
        self.assertIsInstance(d["floor_axes"], list)

    def test_from_dict_missing_floor_level_defaults(self):
        d = {"up_axis": 2, "up_direction": 1, "floor_axes": [0, 1]}
        cs = CoordinateSystem.from_dict(d)
        self.assertEqual(cs.floor_level, 0.0)
        self.assertTrue(cs.flip_floor_v)


class TestAxisHelpers(unittest.TestCase):
    """Test axis helper methods."""

    def test_ros_columns(self):
        cs = CoordinateSystem.ros()
        self.assertEqual(cs.height_column(), 2)
        self.assertEqual(cs.floor_column_h(), 0)
        self.assertEqual(cs.floor_column_v(), 1)

    def test_opencv_columns(self):
        cs = CoordinateSystem.opencv()
        self.assertEqual(cs.height_column(), 1)
        self.assertEqual(cs.floor_column_h(), 0)
        self.assertEqual(cs.floor_column_v(), 2)

    def test_opengl_columns(self):
        cs = CoordinateSystem.opengl()
        self.assertEqual(cs.height_column(), 1)
        self.assertEqual(cs.floor_column_h(), 0)
        self.assertEqual(cs.floor_column_v(), 2)


class TestMake3DPoint(unittest.TestCase):
    """Test make_3d_point axis mapping."""

    def test_ros_point(self):
        cs = CoordinateSystem.ros()
        # ROS: floor_h=X, floor_v=Y, height=Z
        pt = cs.make_3d_point(1.0, 2.0, 3.0)
        self.assertEqual(pt, [1.0, 2.0, 3.0])

    def test_opencv_point(self):
        cs = CoordinateSystem.opencv()
        # OpenCV: floor_h=X, height=Y, floor_v=Z
        pt = cs.make_3d_point(1.0, 2.0, 3.0)
        self.assertEqual(pt, [1.0, 3.0, 2.0])

    def test_opengl_point(self):
        cs = CoordinateSystem.opengl()
        # OpenGL: floor_h=X, height=Y, floor_v=Z
        pt = cs.make_3d_point(1.0, 2.0, 3.0)
        self.assertEqual(pt, [1.0, 3.0, 2.0])

    def test_custom_axes(self):
        cs = CoordinateSystem(up_axis=0, floor_axes=(1, 2))
        # floor_h=Y, floor_v=Z, height=X
        pt = cs.make_3d_point(5.0, 6.0, 7.0)
        self.assertEqual(pt, [7.0, 5.0, 6.0])


class TestCameraUpVector(unittest.TestCase):
    """Test camera_up_vector returns floor_v axis direction."""

    def test_ros_camera_up(self):
        cs = CoordinateSystem.ros()
        # floor_axes=(0,1), floor_v=1 → [0, 1, 0]
        self.assertEqual(cs.camera_up_vector(), [0.0, 1.0, 0.0])

    def test_opencv_camera_up(self):
        cs = CoordinateSystem.opencv()
        # floor_axes=(0,2), floor_v=2 → [0, 0, 1]
        self.assertEqual(cs.camera_up_vector(), [0.0, 0.0, 1.0])

    def test_opengl_camera_up(self):
        cs = CoordinateSystem.opengl()
        # floor_axes=(0,2), floor_v=2 → [0, 0, 1]
        self.assertEqual(cs.camera_up_vector(), [0.0, 0.0, 1.0])

    def test_camera_up_perpendicular_to_view(self):
        """camera_up_vector must be perpendicular to the view direction (up_axis)."""
        import numpy as np
        for name in ("ros", "opencv", "opengl"):
            cs = CoordinateSystem.from_preset(name)
            view_dir = [0.0, 0.0, 0.0]
            view_dir[cs.up_axis] = 1.0
            cam_up = cs.camera_up_vector()
            dot = np.dot(view_dir, cam_up)
            self.assertAlmostEqual(dot, 0.0, msg=f"camera_up not perpendicular for {name}")


class TestSliceEngineCoordinateSystem(unittest.TestCase):
    """Test SliceEngine with different coordinate systems."""

    def _make_point_cloud(self, points):
        import open3d as o3d
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.array(points, dtype=np.float64))
        pcd.colors = o3d.utility.Vector3dVector(np.ones((len(points), 3)) * 0.5)
        return pcd

    def setUp(self):
        from src.core.processor import SliceEngine
        self.engine = SliceEngine()
        # Points: 4 points at different positions
        # [x, y, z]
        self.points = [
            [1.0, 2.0, 0.5],
            [3.0, 4.0, 1.0],
            [5.0, 6.0, 1.5],
            [7.0, 8.0, 2.0],
        ]
        self.pcd = self._make_point_cloud(self.points)

    def test_ros_z_range(self):
        self.engine.load_data(self.pcd)  # default ROS
        z_min, z_max = self.engine.get_z_range()
        self.assertAlmostEqual(z_min, 0.5)
        self.assertAlmostEqual(z_max, 2.0)

    def test_opencv_z_range_uses_y_axis(self):
        self.engine.set_coordinate_system(CoordinateSystem.opencv())
        self.engine.load_data(self.pcd)
        z_min, z_max = self.engine.get_z_range()
        # OpenCV up_axis=1 (Y), so height range is Y: 2.0 to 8.0
        self.assertAlmostEqual(z_min, 2.0)
        self.assertAlmostEqual(z_max, 8.0)

    def test_ros_slice_at_height(self):
        self.engine.load_data(self.pcd)
        pts, _ = self.engine.slice_at_height(1.0, thickness=0.2)
        # Should get point at z=1.0 (within 0.9-1.1)
        self.assertEqual(len(pts), 1)
        np.testing.assert_array_almost_equal(pts[0], [3.0, 4.0, 1.0])

    def test_opencv_slice_at_height(self):
        self.engine.set_coordinate_system(CoordinateSystem.opencv())
        self.engine.load_data(self.pcd)
        # OpenCV slices on Y axis. Point [1,2,0.5] has Y=2.0
        pts, _ = self.engine.slice_at_height(2.0, thickness=0.2)
        self.assertEqual(len(pts), 1)
        np.testing.assert_array_almost_equal(pts[0], [1.0, 2.0, 0.5])

    def test_bounds_2d_ros(self):
        self.engine.load_data(self.pcd)
        bounds = self.engine.get_bounds_2d()
        # ROS floor_axes=(0,1) → X and Y
        self.assertAlmostEqual(bounds[0], 1.0)  # min_h (X)
        self.assertAlmostEqual(bounds[1], 2.0)  # min_v (Y)
        self.assertAlmostEqual(bounds[2], 7.0)  # max_h (X)
        self.assertAlmostEqual(bounds[3], 8.0)  # max_v (Y)

    def test_bounds_2d_opencv(self):
        self.engine.set_coordinate_system(CoordinateSystem.opencv())
        self.engine.load_data(self.pcd)
        bounds = self.engine.get_bounds_2d()
        # OpenCV floor_axes=(0,2) → X and Z
        self.assertAlmostEqual(bounds[0], 1.0)  # min_h (X)
        self.assertAlmostEqual(bounds[1], 0.5)  # min_v (Z)
        self.assertAlmostEqual(bounds[2], 7.0)  # max_h (X)
        self.assertAlmostEqual(bounds[3], 2.0)  # max_v (Z)

    def test_set_coordinate_system_recomputes_bounds(self):
        self.engine.load_data(self.pcd)
        bounds_ros = self.engine.get_bounds_2d()
        self.engine.set_coordinate_system(CoordinateSystem.opencv())
        bounds_opencv = self.engine.get_bounds_2d()
        # Bounds should differ because floor axes changed
        self.assertNotEqual(bounds_ros, bounds_opencv)

    def test_detect_floor_level_ros(self):
        self.engine.load_data(self.pcd)
        floor = self.engine.detect_floor_level(percentile=5.0)
        # Lowest Z is 0.5, percentile should be near it
        self.assertLessEqual(floor, 0.6)

    def test_detect_floor_level_opencv(self):
        self.engine.set_coordinate_system(CoordinateSystem.opencv())
        self.engine.load_data(self.pcd)
        floor = self.engine.detect_floor_level(percentile=5.0)
        # OpenCV: up_direction=-1, uses 100-percentile → near max Y=8.0
        self.assertGreaterEqual(floor, 7.5)

    def test_project_to_image_returns_bounds(self):
        self.engine.load_data(self.pcd)
        pts, _ = self.engine.slice_at_height(1.0, thickness=2.0)
        _, bounds, _ = self.engine.project_to_image(pts, pixel_size=0.1)
        # Bounds should be (min_h, min_v, max_h, max_v) on floor axes
        self.assertEqual(len(bounds), 4)


if __name__ == "__main__":
    unittest.main()
