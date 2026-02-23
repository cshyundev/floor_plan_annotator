import numpy as np
import open3d as o3d
from scipy import ndimage

class SliceEngine:
    def __init__(self):
        self._geometry = None        # Store original (PointCloud or TriangleMesh)
        self._geometry_type = None   # "pointcloud" or "mesh"
        self._points = None
        self._colors = None
        self._bounds = None
        self._bounds_2d = None       # Fixed 2D footprint (min_x, min_y, max_x, max_y)

        # Mesh-specific
        self._mesh = None
        self._vertices = None

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
        self._bounds_2d = (
            float(self._points[:, 0].min()), float(self._points[:, 1].min()),
            float(self._points[:, 0].max()), float(self._points[:, 1].max()),
        )

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
        self._bounds_2d = (
            float(self._vertices[:, 0].min()), float(self._vertices[:, 1].min()),
            float(self._vertices[:, 0].max()), float(self._vertices[:, 1].max()),
        )

    def get_z_range(self):
        if self._bounds is None:
            return 0.0, 1.0
        return self._bounds[0][2], self._bounds[1][2]

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
        
        mask = (self._points[:, 2] >= z_min) & (self._points[:, 2] <= z_max)
        return self._points[mask], self._colors[mask]

    def project_to_image(self, points, pixel_size=0.01, padding=10, fixed_bounds=None):
        """
        Projects 3D points to a 2D density map / image.
        Args:
            points: Nx3 array
            pixel_size: Size of one pixel in meters (e.g., 0.01 = 1cm/pixel)
            padding: Padding in pixels around the image
            fixed_bounds: Optional (min_x, min_y, max_x, max_y) to use instead of
                          calculating from current points. Keeps image size constant.
        Returns:
            image: 2D numpy array (grayscale image)
            bounds: (min_x, min_y, max_x, max_y) in world coordinates
            scale: pixels per meter
        """
        if fixed_bounds is not None:
            min_x, min_y, max_x, max_y = fixed_bounds
        elif len(points) == 0:
            return None, (0, 0, 0, 0), 1.0 / pixel_size
        else:
            min_x, max_x = points[:, 0].min(), points[:, 0].max()
            min_y, max_y = points[:, 1].min(), points[:, 1].max()

        width_m = max_x - min_x
        height_m = max_y - min_y

        scale = 1.0 / pixel_size
        w = int(np.ceil(width_m * scale)) + 2 * padding
        h = int(np.ceil(height_m * scale)) + 2 * padding

        img = np.zeros((h, w), dtype=np.uint8)

        if len(points) > 0:
            x = points[:, 0]
            y = points[:, 1]

            ix = ((x - min_x) * scale + padding).astype(int)
            iy = (h - 1) - ((y - min_y) * scale + padding).astype(int)

            ix = np.clip(ix, 0, w - 1)
            iy = np.clip(iy, 0, h - 1)

            img[iy, ix] = 255
            img = ndimage.binary_dilation(img, iterations=1).astype(np.uint8) * 255

        return img, (min_x, min_y, max_x, max_y), scale
