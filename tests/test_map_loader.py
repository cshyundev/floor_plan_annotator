"""Tests for src.core.map_loader.MapLoader.

Covers:
- parse_yaml: happy path + error cases (missing file, empty YAML,
  missing image field, invalid resolution)
- load_image: normal load, shape/dtype checks, negate flag
- compute_bounds: world-coordinate bounds from metadata
- compute_scale: pixels-per-meter calculation
- classify_pixels: occupied / free / unknown trinary classification
- find_yaml_for_image: YAML discovery heuristics
- make_relative_path: relative-path computation
"""

import os
import tempfile
import unittest

import numpy as np
import yaml
from PyQt6.QtWidgets import QApplication

from src.core.map_loader import MapLoader
from src.model.data import MapMetadata

# QImage requires a QApplication instance
_app = QApplication.instance() or QApplication([])

# Absolute paths to the test data shipped with the repo
_DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data")
)
_TEST_YAML = os.path.join(_DATA_DIR, "occupancy_grid", "test_map.yaml")
_TEST_PNG = os.path.join(_DATA_DIR, "occupancy_grid", "test_map.png")


class TestParseYaml(unittest.TestCase):
    """Tests for MapLoader.parse_yaml()."""

    def test_parse_test_map_yaml(self):
        """Happy-path: parse the bundled test_map.yaml and verify every field."""
        meta = MapLoader.parse_yaml(_TEST_YAML)

        self.assertAlmostEqual(meta.resolution, 0.05)
        self.assertAlmostEqual(meta.origin_x, -5.0)
        self.assertAlmostEqual(meta.origin_y, -5.0)
        self.assertAlmostEqual(meta.origin_yaw, 0.0)
        self.assertAlmostEqual(meta.occupied_thresh, 0.65)
        self.assertAlmostEqual(meta.free_thresh, 0.196)
        self.assertEqual(meta.negate, 0)
        self.assertEqual(meta.image_path, "test_map.png")
        # image_path_absolute should point to data/test_map.png
        self.assertTrue(
            meta.image_path_absolute.endswith("test_map.png"),
            f"Expected absolute path to end with test_map.png, got: {meta.image_path_absolute}",
        )
        self.assertTrue(os.path.isabs(meta.image_path_absolute))

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            MapLoader.parse_yaml("/nonexistent/path/map.yaml")

    def test_empty_yaml_raises_value_error(self):
        """An empty YAML file should raise ValueError."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", delete=False
        ) as f:
            f.write("")  # empty content
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                MapLoader.parse_yaml(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_missing_image_field_raises_value_error(self):
        """YAML without the 'image' key should raise ValueError."""
        data = {"resolution": 0.05, "origin": [0, 0, 0]}
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                MapLoader.parse_yaml(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_invalid_resolution_raises_value_error(self):
        """Zero or negative resolution should raise ValueError."""
        for bad_res in [0, -0.05]:
            data = {"image": "map.png", "resolution": bad_res, "origin": [0, 0, 0]}
            with tempfile.NamedTemporaryFile(
                suffix=".yaml", mode="w", delete=False
            ) as f:
                yaml.dump(data, f)
                tmp_path = f.name
            try:
                with self.assertRaises(ValueError):
                    MapLoader.parse_yaml(tmp_path)
            finally:
                os.unlink(tmp_path)

    def test_invalid_origin_raises_value_error(self):
        """An origin with fewer than 2 elements should raise ValueError."""
        data = {"image": "map.png", "resolution": 0.05, "origin": [1.0]}
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                MapLoader.parse_yaml(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_origin_without_yaw_defaults_to_zero(self):
        """An origin with only [x, y] should give origin_yaw=0.0."""
        data = {"image": "map.png", "resolution": 0.05, "origin": [1.0, 2.0]}
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name
        try:
            meta = MapLoader.parse_yaml(tmp_path)
            self.assertAlmostEqual(meta.origin_yaw, 0.0)
            self.assertAlmostEqual(meta.origin_x, 1.0)
            self.assertAlmostEqual(meta.origin_y, 2.0)
        finally:
            os.unlink(tmp_path)


class TestLoadImage(unittest.TestCase):
    """Tests for MapLoader.load_image()."""

    def setUp(self):
        self.metadata = MapLoader.parse_yaml(_TEST_YAML)

    def test_load_test_map_shape_and_dtype(self):
        """Loading test_map.png should produce a 200x200 uint8 array."""
        arr = MapLoader.load_image(_TEST_PNG, self.metadata)

        self.assertEqual(arr.shape, (200, 200))
        self.assertEqual(arr.dtype, np.uint8)
        self.assertEqual(self.metadata.image_width, 200)
        self.assertEqual(self.metadata.image_height, 200)

    def test_load_image_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            MapLoader.load_image("/nonexistent/image.png", self.metadata)

    def test_negate_flag_inverts_values(self):
        """With negate=1, pixel values should be inverted (255 - original)."""
        meta_normal = MapLoader.parse_yaml(_TEST_YAML)
        meta_normal.negate = 0
        arr_normal = MapLoader.load_image(_TEST_PNG, meta_normal)

        meta_negate = MapLoader.parse_yaml(_TEST_YAML)
        meta_negate.negate = 1
        arr_negate = MapLoader.load_image(_TEST_PNG, meta_negate)

        # Every pixel should satisfy: negate + normal == 255
        np.testing.assert_array_equal(arr_normal + arr_negate, 255)


class TestComputeBounds(unittest.TestCase):
    """Tests for MapLoader.compute_bounds()."""

    def test_bounds_from_test_map(self):
        """With resolution=0.05, origin=(-5,-5), 200x200 image => (-5,-5,5,5)."""
        meta = MapMetadata(
            resolution=0.05,
            origin_x=-5.0,
            origin_y=-5.0,
            image_width=200,
            image_height=200,
        )
        bounds = MapLoader.compute_bounds(meta)
        self.assertAlmostEqual(bounds[0], -5.0)
        self.assertAlmostEqual(bounds[1], -5.0)
        self.assertAlmostEqual(bounds[2], 5.0)
        self.assertAlmostEqual(bounds[3], 5.0)

    def test_bounds_with_different_origin(self):
        """Verify bounds shift correctly with a different origin."""
        meta = MapMetadata(
            resolution=0.1,
            origin_x=0.0,
            origin_y=0.0,
            image_width=100,
            image_height=50,
        )
        min_x, min_y, max_x, max_y = MapLoader.compute_bounds(meta)
        self.assertAlmostEqual(min_x, 0.0)
        self.assertAlmostEqual(min_y, 0.0)
        self.assertAlmostEqual(max_x, 10.0)   # 100 * 0.1
        self.assertAlmostEqual(max_y, 5.0)    # 50 * 0.1


class TestComputeScale(unittest.TestCase):
    """Tests for MapLoader.compute_scale()."""

    def test_scale_from_resolution(self):
        meta = MapMetadata(resolution=0.05)
        self.assertAlmostEqual(MapLoader.compute_scale(meta), 20.0)

    def test_scale_resolution_one(self):
        meta = MapMetadata(resolution=1.0)
        self.assertAlmostEqual(MapLoader.compute_scale(meta), 1.0)

    def test_scale_resolution_ten(self):
        meta = MapMetadata(resolution=10.0)
        self.assertAlmostEqual(MapLoader.compute_scale(meta), 0.1)


class TestClassifyPixels(unittest.TestCase):
    """Tests for MapLoader.classify_pixels().

    ROS trinary classification:
        occ_prob = (255 - pixel) / 255
        occupied: occ_prob > occupied_thresh  => pixel < (1 - occ_thresh) * 255
        free:     occ_prob < free_thresh      => pixel > (1 - free_thresh) * 255
        unknown:  everything else
    """

    def setUp(self):
        self.meta = MapMetadata(occupied_thresh=0.65, free_thresh=0.196)
        # pixel thresholds for default settings:
        # occ_pixel_max = (1 - 0.65) * 255 = 89.25  => pixel <= 89 is occupied
        # free_pixel_min = (1 - 0.196) * 255 = 205.02 => pixel >= 205 is free

    def test_occupied_pixel(self):
        """Very dark pixel (e.g. 0 = black) should be classified as occupied (1)."""
        arr = np.array([[0]], dtype=np.uint8)
        result = MapLoader.classify_pixels(arr, self.meta)
        self.assertEqual(result[0, 0], 1)

    def test_free_pixel(self):
        """Very bright pixel (e.g. 254 = near-white) should be classified as free (0)."""
        arr = np.array([[254]], dtype=np.uint8)
        result = MapLoader.classify_pixels(arr, self.meta)
        self.assertEqual(result[0, 0], 0)

    def test_unknown_pixel(self):
        """Middle-range pixel (e.g. 128) should be classified as unknown (2)."""
        arr = np.array([[128]], dtype=np.uint8)
        result = MapLoader.classify_pixels(arr, self.meta)
        self.assertEqual(result[0, 0], 2)

    def test_boundary_occupied(self):
        """Pixel exactly at occ_pixel_max boundary should be occupied."""
        occ_pixel_max = int((1.0 - self.meta.occupied_thresh) * 255.0)
        arr = np.array([[occ_pixel_max]], dtype=np.uint8)
        result = MapLoader.classify_pixels(arr, self.meta)
        # pixel <= occ_pixel_max => occupied
        self.assertEqual(result[0, 0], 1)

    def test_boundary_free(self):
        """Pixel at ceil(free_pixel_min) should be free."""
        import math
        free_pixel_min = (1.0 - self.meta.free_thresh) * 255.0
        pixel_val = int(math.ceil(free_pixel_min))
        arr = np.array([[pixel_val]], dtype=np.uint8)
        result = MapLoader.classify_pixels(arr, self.meta)
        self.assertEqual(result[0, 0], 0)

    def test_mixed_image(self):
        """A 1x3 image with one occupied, one unknown, one free pixel."""
        arr = np.array([[0, 128, 254]], dtype=np.uint8)
        result = MapLoader.classify_pixels(arr, self.meta)
        np.testing.assert_array_equal(result, [[1, 2, 0]])

    def test_output_shape_matches_input(self):
        arr = np.zeros((10, 15), dtype=np.uint8)
        result = MapLoader.classify_pixels(arr, self.meta)
        self.assertEqual(result.shape, (10, 15))


class TestFindYamlForImage(unittest.TestCase):
    """Tests for MapLoader.find_yaml_for_image()."""

    def test_find_yaml_for_test_map(self):
        """Should find test_map.yaml in the same directory as test_map.png."""
        result = MapLoader.find_yaml_for_image(_TEST_PNG)
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith("test_map.yaml"))

    def test_find_yaml_returns_none_for_nonexistent_dir(self):
        """If the image is in a nonexistent directory, should return None."""
        result = MapLoader.find_yaml_for_image("/nonexistent/dir/image.png")
        self.assertIsNone(result)

    def test_find_yaml_prefers_same_basename(self):
        """When multiple candidate YAML files exist, the same-basename one wins."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create two YAML files
            same_name_yaml = os.path.join(tmp_dir, "my_map.yaml")
            generic_yaml = os.path.join(tmp_dir, "map.yaml")
            with open(same_name_yaml, "w") as f:
                f.write("image: my_map.png\n")
            with open(generic_yaml, "w") as f:
                f.write("image: my_map.png\n")

            image_path = os.path.join(tmp_dir, "my_map.png")
            result = MapLoader.find_yaml_for_image(image_path)
            self.assertEqual(result, same_name_yaml)

    def test_find_yaml_falls_back_to_map_yaml(self):
        """If no same-basename YAML exists, should fall back to map.yaml."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            generic_yaml = os.path.join(tmp_dir, "map.yaml")
            with open(generic_yaml, "w") as f:
                f.write("image: some.png\n")

            image_path = os.path.join(tmp_dir, "some_other_name.png")
            result = MapLoader.find_yaml_for_image(image_path)
            self.assertEqual(result, generic_yaml)

    def test_find_yaml_returns_none_when_no_match(self):
        """If no candidate YAML exists at all, should return None."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = os.path.join(tmp_dir, "image.png")
            result = MapLoader.find_yaml_for_image(image_path)
            self.assertIsNone(result)


class TestMakeRelativePath(unittest.TestCase):
    """Tests for MapLoader.make_relative_path()."""

    def test_sibling_file(self):
        """Image and project in the same directory."""
        result = MapLoader.make_relative_path(
            "/home/user/project/map.png",
            "/home/user/project/project.json",
        )
        self.assertEqual(result, "map.png")

    def test_subdirectory(self):
        """Image in a subdirectory relative to the project."""
        result = MapLoader.make_relative_path(
            "/home/user/project/data/map.png",
            "/home/user/project/project.json",
        )
        expected = os.path.join("data", "map.png")
        self.assertEqual(result, expected)

    def test_parent_directory(self):
        """Image in a parent directory relative to the project."""
        result = MapLoader.make_relative_path(
            "/home/user/map.png",
            "/home/user/project/project.json",
        )
        expected = os.path.join("..", "map.png")
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
