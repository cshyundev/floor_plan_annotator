"""Tests for src.core.map_mesh_generator.MapMeshGenerator.

Covers:
- generate_mesh with real test data (test_map.png + test_map.yaml)
- generate_mesh with a fully white (all-free) image
- generate_mesh with a fully black (all-occupied) image
- Vertex bounds, triangle counts, vertex-color presence, floor quad
"""

import os
import unittest

import numpy as np

try:
    import open3d as o3d

    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

from PyQt6.QtWidgets import QApplication

from src.model.data import MapMetadata

# QImage requires a QApplication instance
_app = QApplication.instance() or QApplication([])

_DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data")
)
_TEST_YAML = os.path.join(_DATA_DIR, "occupancy_grid", "test_map.yaml")
_TEST_PNG = os.path.join(_DATA_DIR, "occupancy_grid", "test_map.png")


@unittest.skipUnless(HAS_OPEN3D, "open3d not installed")
class TestMapMeshGeneratorWithTestData(unittest.TestCase):
    """Integration tests using the bundled test_map data."""

    @classmethod
    def setUpClass(cls):
        from src.core.map_loader import MapLoader

        cls.metadata = MapLoader.parse_yaml(_TEST_YAML)
        cls.image_data = MapLoader.load_image(_TEST_PNG, cls.metadata)

    def setUp(self):
        from src.core.map_mesh_generator import MapMeshGenerator

        self.mesh = MapMeshGenerator.generate_mesh(
            self.image_data, self.metadata
        )

    def test_returns_triangle_mesh(self):
        self.assertIsInstance(self.mesh, o3d.geometry.TriangleMesh)

    def test_has_vertices(self):
        verts = np.asarray(self.mesh.vertices)
        self.assertGreater(len(verts), 0)

    def test_has_triangles(self):
        tris = np.asarray(self.mesh.triangles)
        self.assertGreater(len(tris), 0)

    def test_has_vertex_colors(self):
        colors = np.asarray(self.mesh.vertex_colors)
        self.assertEqual(len(colors), len(np.asarray(self.mesh.vertices)))

    def test_vertex_bounds_x(self):
        """X coordinates should lie within world bounds."""
        verts = np.asarray(self.mesh.vertices)
        self.assertGreaterEqual(verts[:, 0].min(), -5.0 - 1e-6)
        self.assertLessEqual(verts[:, 0].max(), 5.0 + 1e-6)

    def test_vertex_bounds_y(self):
        """Y coordinates should lie within world bounds."""
        verts = np.asarray(self.mesh.vertices)
        self.assertGreaterEqual(verts[:, 1].min(), -5.0 - 1e-6)
        self.assertLessEqual(verts[:, 1].max(), 5.0 + 1e-6)

    def test_vertex_bounds_z(self):
        """Z coordinates should be between 0 and block_height (default 0.3)."""
        verts = np.asarray(self.mesh.vertices)
        self.assertGreaterEqual(verts[:, 2].min(), 0.0 - 1e-6)
        self.assertLessEqual(verts[:, 2].max(), 0.3 + 1e-6)

    def test_floor_quad_exists(self):
        """The mesh should contain at least 4 vertices at z=0 (floor quad)."""
        verts = np.asarray(self.mesh.vertices)
        floor_verts = verts[np.abs(verts[:, 2]) < 1e-6]
        self.assertGreaterEqual(len(floor_verts), 4)

    def test_minimum_triangle_count(self):
        """Should have at least the 2 floor triangles."""
        tris = np.asarray(self.mesh.triangles)
        self.assertGreaterEqual(len(tris), 2)


@unittest.skipUnless(HAS_OPEN3D, "open3d not installed")
class TestMapMeshGeneratorAllFree(unittest.TestCase):
    """Generate mesh from a completely white (all-free) image.

    No occupied cells, so the mesh should contain only the floor quad.
    """

    def test_all_free_has_floor_only(self):
        from src.core.map_mesh_generator import MapMeshGenerator

        # All-white image => all pixels classified as free
        image = np.full((10, 10), 255, dtype=np.uint8)
        meta = MapMetadata(
            resolution=0.1,
            origin_x=0.0,
            origin_y=0.0,
            image_width=10,
            image_height=10,
            occupied_thresh=0.65,
            free_thresh=0.196,
        )

        mesh = MapMeshGenerator.generate_mesh(image, meta)
        verts = np.asarray(mesh.vertices)
        tris = np.asarray(mesh.triangles)

        # Floor quad: 4 vertices, 2 triangles
        self.assertEqual(len(verts), 4)
        self.assertEqual(len(tris), 2)

        # All vertices at z=0
        np.testing.assert_allclose(verts[:, 2], 0.0, atol=1e-9)

    def test_all_free_floor_covers_map_extent(self):
        from src.core.map_mesh_generator import MapMeshGenerator

        image = np.full((20, 30), 255, dtype=np.uint8)
        meta = MapMetadata(
            resolution=0.5,
            origin_x=-1.0,
            origin_y=-2.0,
            image_width=30,
            image_height=20,
            occupied_thresh=0.65,
            free_thresh=0.196,
        )

        mesh = MapMeshGenerator.generate_mesh(image, meta)
        verts = np.asarray(mesh.vertices)

        # Expected map extent: x in [-1, -1 + 30*0.5] = [-1, 14]
        #                      y in [-2, -2 + 20*0.5] = [-2, 8]
        self.assertAlmostEqual(verts[:, 0].min(), -1.0, places=5)
        self.assertAlmostEqual(verts[:, 0].max(), 14.0, places=5)
        self.assertAlmostEqual(verts[:, 1].min(), -2.0, places=5)
        self.assertAlmostEqual(verts[:, 1].max(), 8.0, places=5)


@unittest.skipUnless(HAS_OPEN3D, "open3d not installed")
class TestMapMeshGeneratorAllOccupied(unittest.TestCase):
    """Generate mesh from a completely black (all-occupied) image."""

    def test_all_occupied_block_count(self):
        from src.core.map_mesh_generator import MapMeshGenerator

        size = 4  # 4x4 image = 16 occupied cells
        image = np.zeros((size, size), dtype=np.uint8)
        meta = MapMetadata(
            resolution=1.0,
            origin_x=0.0,
            origin_y=0.0,
            image_width=size,
            image_height=size,
            occupied_thresh=0.65,
            free_thresh=0.196,
        )

        mesh = MapMeshGenerator.generate_mesh(image, meta)
        verts = np.asarray(mesh.vertices)
        tris = np.asarray(mesh.triangles)

        # 4 floor verts + 16 blocks * 8 verts = 132
        expected_verts = 4 + size * size * 8
        self.assertEqual(len(verts), expected_verts)

        # 2 floor tris + 16 blocks * 12 tris = 194
        expected_tris = 2 + size * size * 12
        self.assertEqual(len(tris), expected_tris)

    def test_all_occupied_has_blocks_at_height(self):
        from src.core.map_mesh_generator import MapMeshGenerator

        block_height = 0.5
        image = np.zeros((2, 2), dtype=np.uint8)
        meta = MapMetadata(
            resolution=1.0,
            origin_x=0.0,
            origin_y=0.0,
            image_width=2,
            image_height=2,
            occupied_thresh=0.65,
            free_thresh=0.196,
        )

        mesh = MapMeshGenerator.generate_mesh(
            image, meta, block_height=block_height
        )
        verts = np.asarray(mesh.vertices)

        # Some vertices should be at z = block_height
        top_verts = verts[np.abs(verts[:, 2] - block_height) < 1e-6]
        self.assertGreater(len(top_verts), 0)


@unittest.skipUnless(HAS_OPEN3D, "open3d not installed")
class TestMapMeshGeneratorCustomBlockHeight(unittest.TestCase):
    """Verify that block_height parameter is respected."""

    def test_custom_block_height(self):
        from src.core.map_mesh_generator import MapMeshGenerator

        # Single occupied pixel
        image = np.zeros((1, 1), dtype=np.uint8)
        meta = MapMetadata(
            resolution=1.0,
            origin_x=0.0,
            origin_y=0.0,
            image_width=1,
            image_height=1,
            occupied_thresh=0.65,
            free_thresh=0.196,
        )

        for height in [0.1, 0.5, 1.0, 2.5]:
            mesh = MapMeshGenerator.generate_mesh(
                image, meta, block_height=height
            )
            verts = np.asarray(mesh.vertices)
            z_max = verts[:, 2].max()
            self.assertAlmostEqual(z_max, height, places=5)


@unittest.skipUnless(HAS_OPEN3D, "open3d not installed")
class TestMapMeshGeneratorVertexColors(unittest.TestCase):
    """Verify vertex colors follow the expected scheme."""

    def test_floor_vertices_have_floor_color(self):
        from src.core.map_mesh_generator import MapMeshGenerator

        # All-white => only floor
        image = np.full((2, 2), 255, dtype=np.uint8)
        meta = MapMetadata(
            resolution=1.0,
            origin_x=0.0,
            origin_y=0.0,
            image_width=2,
            image_height=2,
            occupied_thresh=0.65,
            free_thresh=0.196,
        )
        mesh = MapMeshGenerator.generate_mesh(image, meta)
        colors = np.asarray(mesh.vertex_colors)

        expected_floor = MapMeshGenerator.FLOOR_COLOR
        for c in colors:
            np.testing.assert_allclose(c, expected_floor, atol=1e-6)

    def test_block_vertices_have_block_color(self):
        from src.core.map_mesh_generator import MapMeshGenerator

        # All-black => floor + blocks
        image = np.zeros((1, 1), dtype=np.uint8)
        meta = MapMetadata(
            resolution=1.0,
            origin_x=0.0,
            origin_y=0.0,
            image_width=1,
            image_height=1,
            occupied_thresh=0.65,
            free_thresh=0.196,
        )
        mesh = MapMeshGenerator.generate_mesh(image, meta)
        colors = np.asarray(mesh.vertex_colors)

        # First 4 vertices = floor, remaining 8 = block
        block_colors = colors[4:]
        expected_block = MapMeshGenerator.BLOCK_COLOR
        for c in block_colors:
            np.testing.assert_allclose(c, expected_block, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
