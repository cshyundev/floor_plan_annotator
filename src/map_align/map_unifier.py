"""Load any supported map format as an Open3D PointCloud.

Supported inputs:
- Point clouds: .ply, .pcd
- Meshes: .obj, .stl, .glb, .gltf (vertices extracted as points)
- Occupancy grids: .yaml/.yml (ROS2 map_server format, extruded to 3D via wall_height)
"""

import os
from pathlib import Path

import numpy as np
import open3d as o3d
import trimesh


# 3D file extensions (point cloud + mesh)
_3D_EXTENSIONS = frozenset({'.ply', '.pcd', '.obj', '.stl', '.glb', '.gltf'})
_OCCUPANCY_EXTENSIONS = frozenset({'.yaml', '.yml'})


def load_as_geometry(
    file_path: str,
    voxel_size: float = 0.0,
    wall_height: float = 2.0,
) -> o3d.geometry.TriangleMesh | o3d.geometry.PointCloud:
    """Load a file preserving its native format (mesh stays mesh).

    Meshes are returned as TriangleMesh with vertex normals.
    Point clouds and occupancy grids are returned as PointCloud.
    """
    ext = Path(file_path).suffix.lower()

    if ext in _OCCUPANCY_EXTENSIONS:
        return _load_occupancy_grid(file_path, wall_height)

    if ext in _3D_EXTENSIONS:
        # Try mesh first
        if ext in ('.obj', '.stl', '.ply'):
            mesh = o3d.io.read_triangle_mesh(file_path)
            if len(mesh.triangles) > 0:
                mesh.compute_vertex_normals()
                return mesh
        elif ext in ('.glb', '.gltf'):
            # glTF → trimesh → Open3D mesh
            loaded = trimesh.load(file_path)
            if isinstance(loaded, trimesh.Scene):
                meshes = [m for m in loaded.dump() if isinstance(m, trimesh.Trimesh)]
                if meshes:
                    loaded = trimesh.util.concatenate(meshes)
            if isinstance(loaded, trimesh.Trimesh) and len(loaded.faces) > 0:
                mesh = o3d.geometry.TriangleMesh()
                mesh.vertices = o3d.utility.Vector3dVector(np.asarray(loaded.vertices, dtype=np.float64))
                mesh.triangles = o3d.utility.Vector3iVector(np.asarray(loaded.faces))
                mesh.compute_vertex_normals()
                if loaded.visual and hasattr(loaded.visual, 'vertex_colors'):
                    colors = np.asarray(loaded.visual.vertex_colors)[:, :3] / 255.0
                    mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
                return mesh

        # Fallback to point cloud
        pcd = o3d.io.read_point_cloud(file_path)
        if len(pcd.points) > 0:
            if voxel_size > 0:
                pcd = pcd.voxel_down_sample(voxel_size)
            return pcd

    raise ValueError(f"Failed to load geometry from {file_path}")


def load_as_pointcloud(
    file_path: str,
    voxel_size: float = 0.0,
    wall_height: float = 2.0,
) -> o3d.geometry.PointCloud:
    """Load any supported map file and return an Open3D PointCloud.

    3D data is loaded with original coordinates preserved.
    Occupancy grids are extruded to 3D using wall_height.

    Args:
        file_path: Path to map file (3D data or YAML occupancy grid).
        voxel_size: If > 0, voxel-downsample the result for display performance.
        wall_height: Height (meters) for occupancy grid wall extrusion.

    Returns:
        Open3D PointCloud with 3D coordinates.
    """
    ext = Path(file_path).suffix.lower()

    if ext in _OCCUPANCY_EXTENSIONS:
        pcd = _load_occupancy_grid(file_path, wall_height)
    elif ext in _3D_EXTENSIONS:
        pcd = _load_3d_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    points = np.asarray(pcd.points)
    if len(points) == 0:
        raise ValueError(f"No points loaded from {file_path}")

    if voxel_size > 0:
        pcd = pcd.voxel_down_sample(voxel_size)

    return pcd


def _mesh_to_pointcloud(mesh: o3d.geometry.TriangleMesh) -> o3d.geometry.PointCloud:
    """Extract vertices from a TriangleMesh as a PointCloud, preserving colors and normals."""
    pcd = o3d.geometry.PointCloud()
    pcd.points = mesh.vertices
    if mesh.has_vertex_colors():
        pcd.colors = mesh.vertex_colors
    if mesh.has_vertex_normals():
        pcd.normals = mesh.vertex_normals
    return pcd


def _load_3d_file(file_path: str) -> o3d.geometry.PointCloud:
    """Load a 3D file and convert to point cloud, preserving colors."""
    ext = Path(file_path).suffix.lower()

    if ext in ('.glb', '.gltf'):
        return _load_gltf_as_pointcloud(file_path)

    # For mesh-native formats, extract vertices directly
    if ext in ('.obj', '.stl'):
        mesh = o3d.io.read_triangle_mesh(file_path)
        if len(mesh.triangles) > 0:
            return _mesh_to_pointcloud(mesh)

    # PLY/PCD: read as point cloud directly (avoids TriangleMesh warning)
    pcd = o3d.io.read_point_cloud(file_path)
    if len(pcd.points) > 0:
        return pcd

    # Last resort: try mesh for PLY that has triangles but no point cloud data
    if ext == '.ply':
        mesh = o3d.io.read_triangle_mesh(file_path)
        if len(mesh.triangles) > 0:
            return _mesh_to_pointcloud(mesh)

    raise ValueError(f"Failed to load any geometry from {file_path}")


def _load_gltf_as_pointcloud(file_path: str) -> o3d.geometry.PointCloud:
    """Load GLB/GLTF via trimesh, return as Open3D PointCloud."""
    loaded = trimesh.load(file_path)
    if isinstance(loaded, trimesh.Scene):
        meshes = [m for m in loaded.dump() if isinstance(m, trimesh.Trimesh)]
        if not meshes:
            raise ValueError(f"No meshes found in {file_path}")
        loaded = trimesh.util.concatenate(meshes)

    vertices = np.asarray(loaded.vertices, dtype=np.float64)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(vertices)
    if loaded.visual and hasattr(loaded.visual, 'vertex_colors'):
        colors = np.asarray(loaded.visual.vertex_colors)[:, :3] / 255.0
        pcd.colors = o3d.utility.Vector3dVector(colors.astype(np.float64))
    return pcd


def _load_occupancy_grid(yaml_path: str, wall_height: float) -> o3d.geometry.PointCloud:
    """Load ROS2 occupancy grid and convert to 3D point cloud.

    Each occupied pixel generates two points: one at z=0 (floor)
    and one at z=wall_height (ceiling), creating a 3D representation.
    """
    from src.core.map_loader import MapLoader

    metadata = MapLoader.parse_yaml(yaml_path)
    image_data = MapLoader.load_image(metadata.image_path_absolute, metadata)
    classified = MapLoader.classify_pixels(image_data, metadata)

    # Extract occupied pixel coordinates
    occupied_rows, occupied_cols = np.where(classified == 1)
    if len(occupied_rows) == 0:
        raise ValueError(f"No occupied pixels found in {yaml_path}")

    # Convert pixel coords to world coords
    # ROS convention: origin is lower-left pixel
    # Image row 0 = top = max_y
    height = metadata.image_height
    resolution = metadata.resolution

    x = metadata.origin_x + occupied_cols * resolution + resolution * 0.5
    y = metadata.origin_y + (height - 1 - occupied_rows) * resolution + resolution * 0.5

    # Create 3D points: floor (z=0) + ceiling (z=wall_height)
    z_bottom = np.zeros_like(x)
    z_top = np.full_like(x, wall_height)

    points_bottom = np.column_stack([x, y, z_bottom])
    points_top = np.column_stack([x, y, z_top])
    points = np.vstack([points_bottom, points_top])

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    return pcd


def get_bounds_2d(pcd: o3d.geometry.PointCloud) -> tuple[float, float, float, float]:
    """Get 2D bounding box (min_x, min_y, max_x, max_y) from a point cloud."""
    points = np.asarray(pcd.points)
    return (
        float(points[:, 0].min()),
        float(points[:, 1].min()),
        float(points[:, 0].max()),
        float(points[:, 1].max()),
    )
