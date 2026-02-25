import numpy as np
import open3d as o3d
from scipy import ndimage

from src.core.coordinate_system import CoordinateSystem


class SliceEngine:
    def __init__(self):
        self._geometry = None        # Store original (PointCloud or TriangleMesh)
        self._geometry_type = None   # "pointcloud" or "mesh"
        self._points = None
        self._colors = None
        self._bounds = None
        self._bounds_2d = None       # Fixed 2D footprint (min_h, min_v, max_h, max_v)
        self._coord_sys: CoordinateSystem = CoordinateSystem.ros()

        # Mesh-specific
        self._mesh = None
        self._vertices = None

    def set_coordinate_system(self, cs: CoordinateSystem):
        """Update coordinate system. Recomputes 2D bounds if data is loaded."""
        self._coord_sys = cs
        if self._points is not None:
            self._recompute_bounds_2d()

    def get_coordinate_system(self) -> CoordinateSystem:
        return self._coord_sys

    def _recompute_bounds_2d(self):
        """Recompute the fixed 2D footprint from current points and coordinate system."""
        if self._points is None or len(self._points) == 0:
            self._bounds_2d = None
            return
        fh = self._coord_sys.floor_column_h()
        fv = self._coord_sys.floor_column_v()
        self._bounds_2d = (
            float(self._points[:, fh].min()), float(self._points[:, fv].min()),
            float(self._points[:, fh].max()), float(self._points[:, fv].max()),
        )

    def load_data(self, geometry):
        """Loads Open3D PointCloud or TriangleMesh data.

        Args:
            geometry: Open3D PointCloud or TriangleMesh object
        """
        self._geometry = geometry

        # Type detection using duck typing
        if hasattr(geometry, 'triangles') and hasattr(geometry, 'vertices'):
            self._geometry_type = "mesh"
            self._load_mesh(geometry)
        else:
            self._geometry_type = "pointcloud"
            self._load_pointcloud(geometry)

    def _load_pointcloud(self, pcd):
        """Load point cloud data (existing logic)."""
        self._points = np.asarray(pcd.points)

        # Handle empty point cloud
        if len(self._points) == 0:
            self._colors = np.array([])
            self._bounds = None
            return

        if pcd.has_colors():
            self._colors = np.asarray(pcd.colors)
        else:
            self._colors = np.zeros_like(self._points)
        self._bounds = (self._points.min(axis=0), self._points.max(axis=0))
        self._recompute_bounds_2d()

    def _load_mesh(self, mesh):
        """Load triangle mesh data.

        Uses mesh vertices as points for slicing. This provides
        a simple, fast approach that works with the existing slicing
        algorithm (Z-coordinate filtering).
        """
        self._mesh = mesh
        self._vertices = np.asarray(mesh.vertices)

        # Use vertices as points for slicing
        self._points = self._vertices

        # Handle empty mesh
        if len(self._vertices) == 0:
            self._colors = np.array([])
            self._bounds = None
            return

        # Extract colors
        if mesh.has_vertex_colors():
            self._colors = np.asarray(mesh.vertex_colors)
        else:
            # Default to gray for uncolored meshes
            self._colors = np.ones_like(self._vertices) * 0.7

        self._bounds = (self._vertices.min(axis=0), self._vertices.max(axis=0))
        self._recompute_bounds_2d()

    def get_z_range(self):
        if self._bounds is None:
            return 0.0, 1.0
        ua = self._coord_sys.height_column()
        return self._bounds[0][ua], self._bounds[1][ua]

    def get_bounds_2d(self):
        """Return fixed 2D footprint bounds (min_x, min_y, max_x, max_y) from full geometry."""
        return self._bounds_2d

    def slice_at_height(self, z_height, thickness=0.1):
        """Slices geometry at z_height with thickness band.

        Works with both PointCloud and TriangleMesh. For meshes, uses
        vertices for filtering. For point clouds, uses points directly.

        Args:
            z_height: Height in meters to slice at
            thickness: Thickness of the slice band (default 0.1m)

        Returns:
            points: Nx3 numpy array of points within the slice
            colors: Nx3 numpy array of colors
        """
        if self._points is None:
            return np.array([]), np.array([])
            
        z_min = z_height - (thickness / 2.0)
        z_max = z_height + (thickness / 2.0)

        ua = self._coord_sys.height_column()
        mask = (self._points[:, ua] >= z_min) & (self._points[:, ua] <= z_max)
        return self._points[mask], self._colors[mask]

    def project_to_image(self, points, pixel_size=0.01, padding=10, fixed_bounds=None):
        """
        Projects 3D points to a 2D density map / image.
        Args:
            points: Nx3 array
            pixel_size: Size of one pixel in meters (e.g., 0.01 = 1cm/pixel)
            padding: Padding in pixels around the image
            fixed_bounds: Optional (min_h, min_v, max_h, max_v) to use instead of
                          calculating from current points. Keeps image size constant.
        Returns:
            image: 2D numpy array (grayscale image)
            bounds: (min_h, min_v, max_h, max_v) in world coordinates
            scale: pixels per meter
        """
        fh = self._coord_sys.floor_column_h()
        fv = self._coord_sys.floor_column_v()

        if fixed_bounds is not None:
            min_h, min_v, max_h, max_v = fixed_bounds
        elif len(points) == 0:
            return None, (0, 0, 0, 0), 1.0 / pixel_size
        else:
            min_h, max_h = points[:, fh].min(), points[:, fh].max()
            min_v, max_v = points[:, fv].min(), points[:, fv].max()

        width_m = max_h - min_h
        height_m = max_v - min_v

        scale = 1.0 / pixel_size
        w = int(np.ceil(width_m * scale)) + 2 * padding
        h = int(np.ceil(height_m * scale)) + 2 * padding

        img = np.zeros((h, w), dtype=np.uint8)

        if len(points) > 0:
            x = points[:, fh]
            y = points[:, fv]

            ix = ((x - min_h) * scale + padding).astype(int)
            if self._coord_sys.flip_floor_v:
                iy = (h - 1) - ((y - min_v) * scale + padding).astype(int)
            else:
                iy = ((y - min_v) * scale + padding).astype(int)

            ix = np.clip(ix, 0, w - 1)
            iy = np.clip(iy, 0, h - 1)

            img[iy, ix] = 255
            img = ndimage.binary_dilation(img, iterations=1).astype(np.uint8) * 255

        return img, (min_h, min_v, max_h, max_v), scale
