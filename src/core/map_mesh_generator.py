"""Occupancy grid to 3D mesh generator.

Converts a 2D occupancy grid into an Open3D TriangleMesh with:
- A floor plane covering the map extent
- Block meshes for each occupied cell raised to a configurable height
"""

import numpy as np
import open3d as o3d

from src.model.data import MapMetadata
from src.core.map_loader import MapLoader


class MapMeshGenerator:
    """Generates 3D block mesh from occupancy grid data."""

    # Colors (RGB, 0-1 range)
    FLOOR_COLOR = [0.85, 0.85, 0.85]
    BLOCK_COLOR = [0.35, 0.35, 0.40]

    @staticmethod
    def generate_mesh(
        image_data: np.ndarray,
        metadata: MapMetadata,
        block_height: float = 0.3,
    ) -> o3d.geometry.TriangleMesh:
        """Generate a combined floor + occupied-block mesh.

        Args:
            image_data: Grayscale occupancy grid image (H, W), uint8.
            metadata: MapMetadata with resolution, origin, thresholds.
            block_height: Height of occupied cell blocks in meters.

        Returns:
            Open3D TriangleMesh with vertex colors and normals.
        """
        classified = MapLoader.classify_pixels(image_data, metadata)
        H, W = classified.shape
        res = metadata.resolution
        ox, oy = metadata.origin_x, metadata.origin_y

        vertices = []
        triangles = []
        colors = []

        # --- Floor mesh (single quad at z=0) ---
        map_w = W * res
        map_h = H * res
        floor_z = 0.0
        # 4 vertices for floor quad
        vertices.extend([
            [ox, oy, floor_z],
            [ox + map_w, oy, floor_z],
            [ox + map_w, oy + map_h, floor_z],
            [ox, oy + map_h, floor_z],
        ])
        triangles.extend([[0, 2, 1], [0, 3, 2]])
        colors.extend([MapMeshGenerator.FLOOR_COLOR] * 4)

        # --- Block meshes for occupied cells ---
        occupied_mask = (classified == 1)
        occ_rows, occ_cols = np.where(occupied_mask)

        for row, col in zip(occ_rows, occ_cols):
            # Image pixel (row, col) → world coordinates
            # row 0 = top of image = world max_y
            x0 = ox + col * res
            y0 = oy + (H - 1 - row) * res
            x1 = x0 + res
            y1 = y0 + res
            z0 = floor_z
            z1 = block_height

            base = len(vertices)

            # 8 vertices per box
            vertices.extend([
                [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],  # bottom
                [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1],  # top
            ])

            # 12 triangles (6 faces × 2 triangles each)
            triangles.extend([
                # Top face
                [base + 4, base + 6, base + 5], [base + 4, base + 7, base + 6],
                # Bottom face
                [base + 0, base + 1, base + 2], [base + 0, base + 2, base + 3],
                # Front face (y = y0)
                [base + 0, base + 5, base + 1], [base + 0, base + 4, base + 5],
                # Back face (y = y1)
                [base + 2, base + 7, base + 3], [base + 2, base + 6, base + 7],
                # Left face (x = x0)
                [base + 3, base + 4, base + 0], [base + 3, base + 7, base + 4],
                # Right face (x = x1)
                [base + 1, base + 6, base + 2], [base + 1, base + 5, base + 6],
            ])

            colors.extend([MapMeshGenerator.BLOCK_COLOR] * 8)

        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        mesh.triangles = o3d.utility.Vector3iVector(triangles)
        mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
        mesh.compute_vertex_normals()

        return mesh
