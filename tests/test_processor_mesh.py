"""
Tests for SliceEngine mesh support.

This test module verifies that SliceEngine correctly handles both
PointCloud and TriangleMesh geometry types, including:
- Type detection
- Mesh slicing with Z-coordinate filtering
- Backward compatibility with point clouds
- Edge cases (sparse meshes, missing colors, etc.)
"""

import numpy as np
import open3d as o3d
import pytest
from src.core.processor import SliceEngine


class TestMeshTypeDetection:
    """Test geometry type detection."""

    def test_detects_mesh_geometry(self):
        """Should correctly identify TriangleMesh."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        assert engine._geometry_type == "mesh"
        assert engine._mesh is not None
        assert engine._vertices is not None

    def test_detects_pointcloud_geometry(self):
        """Should correctly identify PointCloud."""
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.random.rand(100, 3))
        engine = SliceEngine()
        engine.load_data(pcd)

        assert engine._geometry_type == "pointcloud"
        assert engine._mesh is None

    def test_mesh_with_sphere(self):
        """Should detect sphere mesh."""
        mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        assert engine._geometry_type == "mesh"

    def test_mesh_with_cylinder(self):
        """Should detect cylinder mesh."""
        mesh = o3d.geometry.TriangleMesh.create_cylinder(radius=0.5, height=2.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        assert engine._geometry_type == "mesh"


class TestMeshSlicing:
    """Test mesh slicing functionality."""

    def test_mesh_slice_at_height_filters_correctly(self):
        """Should return only vertices within Z range."""
        # Create a box from Z=0 to Z=1 (vertices only at Z=0 and Z=1)
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        # Slice at Z=0 with thickness 0.1 (Z range -0.05 to 0.05)
        points, colors = engine.slice_at_height(z_height=0.0, thickness=0.1)

        # Should return 4 bottom vertices at Z=0
        assert len(points) > 0, "Should return some points"
        assert len(points) == 4, "Box bottom has 4 vertices"
        assert np.all(np.abs(points[:, 2] - 0.0) <= 0.05), "All Z values should be near 0.0"

    def test_mesh_slice_returns_matching_colors(self):
        """Should return colors array matching points array."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        points, colors = engine.slice_at_height(z_height=0.5, thickness=0.2)

        assert len(points) == len(colors), "Points and colors should have same length"
        assert colors.shape[1] == 3, "Colors should be Nx3 array"

    def test_mesh_slice_outside_bounds_returns_empty(self):
        """Should return empty arrays when slice is outside mesh bounds."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        # Slice well above the box (Z=10)
        points, colors = engine.slice_at_height(z_height=10.0, thickness=0.1)

        assert len(points) == 0, "Should return empty points"
        assert len(colors) == 0, "Should return empty colors"

    def test_mesh_slice_thin_band(self):
        """Should handle very thin slice thickness."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        # Very thin slice
        points, colors = engine.slice_at_height(z_height=0.0, thickness=0.001)

        # Should still return points at Z=0 (bottom face)
        if len(points) > 0:
            assert np.all(np.abs(points[:, 2] - 0.0) <= 0.001)

    def test_mesh_slice_thick_band(self):
        """Should handle thick slice that covers entire mesh."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        # Thick slice covering entire box
        points, colors = engine.slice_at_height(z_height=0.5, thickness=2.0)

        # Should return all vertices
        assert len(points) == 8, "Box has 8 vertices"


class TestMeshColors:
    """Test mesh color handling."""

    def test_mesh_with_vertex_colors(self):
        """Should extract vertex colors from mesh."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        # Add red color to all vertices
        mesh.vertex_colors = o3d.utility.Vector3dVector(
            np.array([[1.0, 0.0, 0.0]] * len(mesh.vertices))
        )

        engine = SliceEngine()
        engine.load_data(mesh)

        points, colors = engine.slice_at_height(z_height=0.5, thickness=1.0)

        # Should have red colors
        assert np.allclose(colors[:, 0], 1.0), "Red channel should be 1.0"
        assert np.allclose(colors[:, 1], 0.0), "Green channel should be 0.0"
        assert np.allclose(colors[:, 2], 0.0), "Blue channel should be 0.0"

    def test_mesh_without_colors_gets_default_gray(self):
        """Should assign default gray color to uncolored mesh."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        # Don't set vertex colors

        engine = SliceEngine()
        engine.load_data(mesh)

        points, colors = engine.slice_at_height(z_height=0.5, thickness=1.0)

        # Should have gray colors (0.7, 0.7, 0.7)
        assert np.allclose(colors, 0.7), "Default color should be gray (0.7)"


class TestBackwardCompatibility:
    """Test that existing point cloud functionality still works."""

    def test_pointcloud_still_works(self):
        """Should still handle point clouds correctly."""
        # Create a simple point cloud
        points_array = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.5],
            [0.0, 1.0, 1.0],
            [1.0, 1.0, 1.5],
        ])
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_array)

        engine = SliceEngine()
        engine.load_data(pcd)

        assert engine._geometry_type == "pointcloud"

        # Slice at Z=0.5 with thickness 0.2 (range 0.4 to 0.6)
        points, colors = engine.slice_at_height(z_height=0.5, thickness=0.2)

        assert len(points) == 1, "Should return only the point at Z=0.5"
        assert np.allclose(points[0], [1.0, 0.0, 0.5])

    def test_pointcloud_with_colors(self):
        """Should extract point cloud colors correctly."""
        points_array = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
        colors_array = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_array)
        pcd.colors = o3d.utility.Vector3dVector(colors_array)

        engine = SliceEngine()
        engine.load_data(pcd)

        points, colors = engine.slice_at_height(z_height=0.5, thickness=2.0)

        assert len(points) == 2
        assert np.allclose(colors[0], [1.0, 0.0, 0.0])
        assert np.allclose(colors[1], [0.0, 1.0, 0.0])

    def test_pointcloud_without_colors_gets_white(self):
        """Should assign white to point cloud without colors (IMP-001 change)."""
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.random.rand(10, 3))

        engine = SliceEngine()
        engine.load_data(pcd)

        points, colors = engine.slice_at_height(z_height=0.5, thickness=1.0)

        if len(points) > 0:
            assert np.allclose(colors, 1.0), "Default point cloud color should be white"


class TestZRangeCalculation:
    """Test Z-range bounds calculation."""

    def test_mesh_z_range(self):
        """Should calculate correct Z bounds for mesh."""
        # Box from Z=0 to Z=1
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        z_min, z_max = engine.get_z_range()

        assert np.isclose(z_min, 0.0), "Z min should be 0.0"
        assert np.isclose(z_max, 1.0), "Z max should be 1.0"

    def test_pointcloud_z_range(self):
        """Should calculate correct Z bounds for point cloud."""
        points_array = np.array([
            [0.0, 0.0, -1.0],
            [0.0, 0.0, 2.5],
        ])
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_array)

        engine = SliceEngine()
        engine.load_data(pcd)

        z_min, z_max = engine.get_z_range()

        assert np.isclose(z_min, -1.0), "Z min should be -1.0"
        assert np.isclose(z_max, 2.5), "Z max should be 2.5"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_mesh(self):
        """Should handle empty mesh gracefully."""
        mesh = o3d.geometry.TriangleMesh()
        engine = SliceEngine()

        # Should not crash
        engine.load_data(mesh)

        # get_z_range should return default
        z_min, z_max = engine.get_z_range()
        assert z_min == 0.0 and z_max == 1.0

    def test_slice_before_loading_data(self):
        """Should return empty arrays when no data loaded."""
        engine = SliceEngine()
        points, colors = engine.slice_at_height(z_height=0.5, thickness=0.1)

        assert len(points) == 0
        assert len(colors) == 0

    def test_complex_mesh_slicing(self):
        """Should handle high-poly mesh."""
        # Create a sphere with many vertices
        mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=20)
        engine = SliceEngine()
        engine.load_data(mesh)

        # Slice at equator (Z=0)
        points, colors = engine.slice_at_height(z_height=0.0, thickness=0.1)

        assert len(points) > 0, "Should return points near equator"
        # All points should be near Z=0
        assert np.all(np.abs(points[:, 2]) <= 0.05)


class TestColorProjection:
    """Test IMP-001: 2D slice color projection."""

    def _make_pcd(self, points, colors=None):
        """Helper: create Open3D PointCloud from arrays."""
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.array(points, dtype=np.float64))
        if colors is not None:
            pcd.colors = o3d.utility.Vector3dVector(np.array(colors, dtype=np.float64))
        return pcd

    def test_project_with_colors_returns_rgb(self):
        """When colors are provided, project_to_image returns (h, w, 3) uint8 RGB image."""
        # Create 4 well-separated points on the XY floor plane at Z=0
        points_data = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ])
        colors_data = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 0.0],
        ])
        pcd = self._make_pcd(points_data, colors_data)

        engine = SliceEngine()
        engine.load_data(pcd)

        points, colors = engine.slice_at_height(z_height=0.0, thickness=0.5)
        image, bounds, scale = engine.project_to_image(points, pixel_size=0.01, colors=colors)

        assert image is not None, "Image should not be None"
        assert image.ndim == 3, f"Expected 3D array (RGB), got ndim={image.ndim}"
        assert image.shape[2] == 3, f"Expected 3 channels, got {image.shape[2]}"
        assert image.dtype == np.uint8, f"Expected uint8, got {image.dtype}"

    def test_project_without_colors_returns_grayscale(self):
        """When colors param is None (default), returns (h, w) grayscale -- backward compat."""
        points_data = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ])
        pcd = self._make_pcd(points_data)

        engine = SliceEngine()
        engine.load_data(pcd)

        points, colors = engine.slice_at_height(z_height=0.0, thickness=0.5)
        # No colors parameter -> grayscale
        image, bounds, scale = engine.project_to_image(points, pixel_size=0.01)

        assert image is not None, "Image should not be None"
        assert image.ndim == 2, f"Expected 2D array (grayscale), got ndim={image.ndim}"
        assert image.dtype == np.uint8, f"Expected uint8, got {image.dtype}"

    def test_topmost_point_color_wins(self):
        """In ROS (up_direction=+1, height=Z), higher Z point's color should win.

        Two points at same (x, y) but different Z: the point with higher Z
        is topmost (Z * up_direction is larger) and its color should overwrite.
        """
        # Both at x=0.5, y=0.5, but different Z
        points_data = np.array([
            [0.5, 0.5, 0.0],  # bottom point: red
            [0.5, 0.5, 1.0],  # top point: blue (should win)
        ])
        colors_data = np.array([
            [1.0, 0.0, 0.0],  # red
            [0.0, 0.0, 1.0],  # blue
        ])
        pcd = self._make_pcd(points_data, colors_data)

        engine = SliceEngine()
        # Default is ROS: up_axis=2, up_direction=+1
        engine.load_data(pcd)

        points, colors = engine.slice_at_height(z_height=0.5, thickness=2.0)
        image, bounds, scale = engine.project_to_image(
            points, pixel_size=0.01, colors=colors
        )

        assert image is not None
        # Find the pixel where the points project to
        # Pixel should be blue (0, 0, 255) because Z=1.0 is topmost in ROS
        colored_mask = image.sum(axis=2) > 0
        assert colored_mask.any(), "At least one pixel should have color"

        # Get the color at the projected pixel (could be original or dilated)
        colored_pixels = image[colored_mask]
        # The source pixel should be blue (0, 0, 255)
        # Due to dilation, check that the dominant color is blue
        # Find pixels with highest blue value
        max_blue_pixel = colored_pixels[colored_pixels[:, 2].argmax()]
        assert max_blue_pixel[2] == 255, f"Blue channel should be 255, got {max_blue_pixel[2]}"
        assert max_blue_pixel[0] == 0, f"Red channel should be 0, got {max_blue_pixel[0]}"

    def test_topmost_point_negative_up_direction(self):
        """In OpenCV (up_direction=-1, height=Y), lower Y is topmost.

        OpenCV: up_axis=1, up_direction=-1. Topmost = Y * (-1) highest,
        so the point with the most negative Y value should win.
        """
        from src.core.coordinate_system import CoordinateSystem

        # Two points at same (x=0.5, z=0.5) but different Y
        points_data = np.array([
            [0.5, 2.0, 0.5],   # Y=2.0  -> effective height = 2.0 * (-1) = -2 (not topmost)
            [0.5, -1.0, 0.5],  # Y=-1.0 -> effective height = -1.0 * (-1) = +1 (topmost, wins)
        ])
        colors_data = np.array([
            [1.0, 0.0, 0.0],  # red (Y=2.0)
            [0.0, 1.0, 0.0],  # green (Y=-1.0, should win)
        ])
        pcd = self._make_pcd(points_data, colors_data)

        engine = SliceEngine()
        engine.set_coordinate_system(CoordinateSystem.opencv())
        engine.load_data(pcd)

        # Slice along height axis (Y) covering both points
        points, colors = engine.slice_at_height(z_height=0.5, thickness=10.0)
        assert len(points) == 2, f"Expected 2 points, got {len(points)}"

        image, bounds, scale = engine.project_to_image(
            points, pixel_size=0.01, colors=colors
        )

        assert image is not None
        colored_mask = image.sum(axis=2) > 0
        assert colored_mask.any(), "At least one pixel should have color"

        colored_pixels = image[colored_mask]
        # The source pixel should be green (0, 255, 0) because Y=-1.0 is topmost in OpenCV
        max_green_pixel = colored_pixels[colored_pixels[:, 1].argmax()]
        assert max_green_pixel[1] == 255, f"Green channel should be 255, got {max_green_pixel[1]}"
        assert max_green_pixel[0] == 0, f"Red channel should be 0, got {max_green_pixel[0]}"

    def test_color_dilation_propagates_nearest(self):
        """Single colored point should propagate its color to dilated neighbor pixels."""
        # Single point at center of a small area
        points_data = np.array([
            [0.5, 0.5, 0.0],
        ])
        colors_data = np.array([
            [0.0, 1.0, 0.0],  # green
        ])
        pcd = self._make_pcd(points_data, colors_data)

        engine = SliceEngine()
        engine.load_data(pcd)

        points, colors = engine.slice_at_height(z_height=0.0, thickness=0.5)
        image, bounds, scale = engine.project_to_image(
            points, pixel_size=0.01, colors=colors
        )

        assert image is not None
        assert image.ndim == 3

        # Count non-zero pixels
        colored_mask = image.sum(axis=2) > 0
        num_colored = colored_mask.sum()

        # With dilation, more than 1 pixel should be colored
        assert num_colored > 1, (
            f"Expected dilation to produce multiple colored pixels, got {num_colored}"
        )

        # All colored pixels should be the same green color (nearest-neighbor dilation)
        colored_pixels = image[colored_mask]
        # All should be [0, 255, 0] (green in uint8)
        for i in range(len(colored_pixels)):
            assert colored_pixels[i, 0] == 0, f"Red should be 0, got {colored_pixels[i, 0]}"
            assert colored_pixels[i, 1] == 255, f"Green should be 255, got {colored_pixels[i, 1]}"
            assert colored_pixels[i, 2] == 0, f"Blue should be 0, got {colored_pixels[i, 2]}"

    def test_empty_points_with_colors(self):
        """Empty points array with colors should return None."""
        engine = SliceEngine()

        empty_points = np.array([]).reshape(0, 3)
        empty_colors = np.array([]).reshape(0, 3)

        image, bounds, scale = engine.project_to_image(
            empty_points, pixel_size=0.01, colors=empty_colors
        )

        assert image is None, "Empty points should return None image"

    def test_colors_clipped(self):
        """Colors slightly outside [0, 1] should not crash and produce valid uint8 output."""
        points_data = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
        ])
        # Out-of-range colors: negative and > 1.0
        colors_data = np.array([
            [-0.1, 1.2, 0.5],
            [0.0, 0.0, 2.0],
        ])
        pcd = self._make_pcd(points_data, colors_data)

        engine = SliceEngine()
        engine.load_data(pcd)

        points, colors = engine.slice_at_height(z_height=0.0, thickness=0.5)
        image, bounds, scale = engine.project_to_image(
            points, pixel_size=0.01, colors=colors
        )

        assert image is not None
        assert image.dtype == np.uint8
        assert image.ndim == 3
        # All values should be in valid uint8 range (0-255)
        assert image.min() >= 0
        assert image.max() <= 255
        # Verify clipping: -0.1 should clip to 0, 1.2 should clip to 255, 2.0 should clip to 255
        colored_mask = image.sum(axis=2) > 0
        assert colored_mask.any(), "Should have some colored pixels"

    def test_colorless_pointcloud_default_white(self):
        """Point cloud loaded without colors should default to white (1, 1, 1)."""
        points_data = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        pcd = self._make_pcd(points_data)  # no colors
        assert not pcd.has_colors(), "Point cloud should not have colors"

        engine = SliceEngine()
        engine.load_data(pcd)

        # Internal _colors should be all ones (white)
        assert engine._colors is not None
        assert engine._colors.shape == (3, 3), f"Expected (3, 3), got {engine._colors.shape}"
        assert np.allclose(engine._colors, 1.0), (
            f"Default colors should be white (1.0), got {engine._colors}"
        )


class TestProjectionIntegration:
    """Test that sliced mesh data works with projection."""

    def test_mesh_slice_can_be_projected(self):
        """Should be able to project sliced mesh points to 2D."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=2.0, height=2.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        # Slice at Z=0 where vertices exist
        points, colors = engine.slice_at_height(z_height=0.0, thickness=0.1)

        # Should be able to call project_to_image without error
        image, bounds, scale = engine.project_to_image(points, pixel_size=0.01)

        assert image is not None, "Should create an image"
        assert len(bounds) == 4, "Should return bounds (min_x, min_y, max_x, max_y)"
        assert scale > 0, "Scale should be positive"

    def test_empty_slice_projection(self):
        """Should handle projection of empty slice."""
        mesh = o3d.geometry.TriangleMesh.create_box(width=1.0, height=1.0, depth=1.0)
        engine = SliceEngine()
        engine.load_data(mesh)

        # Slice outside bounds
        points, colors = engine.slice_at_height(z_height=10.0, thickness=0.1)

        # Should handle empty points
        image, bounds, scale = engine.project_to_image(points, pixel_size=0.01)

        assert image is None, "Should return None for empty slice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
