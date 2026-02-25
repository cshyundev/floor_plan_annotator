"""Tests for CoordinateSystem core module."""

import unittest
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


if __name__ == "__main__":
    unittest.main()
