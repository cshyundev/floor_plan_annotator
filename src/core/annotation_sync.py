"""
2D Annotation to 3D Viewer Synchronization Module (Revised)

This module handles synchronization between 2D annotations (rooms and walls)
and the 3D viewer. It creates separate annotation geometries (polygon planes
for rooms, vertical planes for walls) that are rendered independently from
the original point cloud/mesh data.
"""

import numpy as np
import open3d as o3d
from typing import List, Tuple, Dict
from PyQt6.QtCore import QPointF


class RoomPlaneBuilder:
    """
    Creates horizontal polygon planes for room annotations.

    Generates colored floor planes at a specified z-level to represent
    room boundaries in 3D space.
    """

    def create_room_plane(self, polygon_2d: List[QPointF], z_level: float,
                         color: Tuple[float, float, float]) -> o3d.geometry.TriangleMesh:
        """
        Create a horizontal polygon mesh at z_level.

        Uses fan triangulation to convert the 2D polygon into a 3D mesh.
        Works well for convex polygons and most room shapes.

        Args:
            polygon_2d: List of QPointF defining room boundary
            z_level: Z coordinate for the plane (floor level)
            color: RGB tuple in [0-1] range

        Returns:
            Open3D TriangleMesh of the room floor plane
        """
        if len(polygon_2d) < 3:
            # Need at least 3 vertices for a valid polygon
            return o3d.geometry.TriangleMesh()

        # Convert to 3D vertices at z_level
        vertices_3d = [[p.x(), p.y(), z_level] for p in polygon_2d]

        # Fan triangulation from first vertex
        # Creates triangles: [0,1,2], [0,2,3], [0,3,4], ..., [0,n-2,n-1]
        n = len(vertices_3d)
        triangles = []
        for i in range(1, n - 1):
            triangles.append([0, i, i + 1])

        # Create mesh
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(vertices_3d)
        mesh.triangles = o3d.utility.Vector3iVector(triangles)

        # Apply color
        mesh.paint_uniform_color(color)

        # Compute normals for proper lighting
        mesh.compute_vertex_normals()

        return mesh


class WallGeometryBuilder:
    """
    Creates virtual 3D wall meshes from 2D wall edges.

    Builds vertical rectangular planes from z_min to z_max.
    """

    def create_wall_mesh(self, start_2d: QPointF, end_2d: QPointF,
                        z_min: float, z_max: float,
                        color: Tuple[float, float, float]) -> o3d.geometry.TriangleMesh:
        """
        Create vertical wall plane mesh.

        Creates a rectangular mesh representing a wall:
        - Bottom edge at z_min
        - Top edge at z_max
        - Endpoints from 2D coordinates

        Args:
            start_2d: Wall start point (x, y)
            end_2d: Wall end point (x, y)
            z_min: Bottom z coordinate (typically 0)
            z_max: Top z coordinate (wall height)
            color: RGB tuple in [0-1] range

        Returns:
            Open3D TriangleMesh representing the wall
        """
        # Define 4 vertices of the rectangular wall
        vertices = [
            [start_2d.x(), start_2d.y(), z_min],  # 0: bottom-left
            [start_2d.x(), start_2d.y(), z_max],  # 1: top-left
            [end_2d.x(), end_2d.y(), z_max],      # 2: top-right
            [end_2d.x(), end_2d.y(), z_min],      # 3: bottom-right
        ]

        # Define 2 triangles forming the rectangle
        triangles = [
            [0, 1, 2],  # First triangle
            [0, 2, 3],  # Second triangle
        ]

        # Create mesh
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        mesh.triangles = o3d.utility.Vector3iVector(triangles)

        # Paint uniform color
        mesh.paint_uniform_color(color)

        # Compute normals for proper lighting
        mesh.compute_vertex_normals()

        return mesh


class AnnotationSync3D:
    """
    Central coordinator for 2D-3D annotation synchronization.

    Creates and manages separate annotation geometries (room planes and wall planes)
    that are rendered independently from the original point cloud/mesh data.
    """

    def __init__(self, viewer_3d, processor, config):
        """
        Initialize synchronization coordinator.

        Args:
            viewer_3d: Viewer3D instance
            processor: SliceEngine instance
            config: ConfigManager instance
        """
        self.viewer = viewer_3d
        self.processor = processor
        self.config = config

        # Builders for creating annotation geometries
        self.room_builder = RoomPlaneBuilder()
        self.wall_builder = WallGeometryBuilder()

        # Track created geometries
        self.room_geometries: Dict[str, o3d.geometry.TriangleMesh] = {}
        self.wall_geometries: Dict[str, o3d.geometry.TriangleMesh] = {}

    def initialize_geometry(self, geometry):
        """
        Initialize after geometry load.

        Note: No longer needed for room synchronization since we're not
        coloring existing points. Kept for compatibility.

        Args:
            geometry: Open3D PointCloud or TriangleMesh (ignored)
        """
        pass  # No action needed with new approach

    def sync_room_annotation(self, room_item):
        """
        Create/update 3D plane for a room annotation.

        Creates a horizontal colored polygon plane at floor level to
        represent the room in 3D space.

        Args:
            room_item: RoomItem instance from canvas
        """
        # Check if room planes are enabled
        if not self.config.get_value("ui_config", "annotation_3d", "enable_room_planes"):
            return

        # Extract polygon from room nodes
        polygon_2d = [node.pos() for node in room_item.nodes]

        # Get room color from config
        room_type_conf = self.config.get_room_type(room_item.room_type)
        if room_type_conf:
            color_rgba = room_type_conf.get("color", [200, 200, 200, 100])
            # Convert RGBA [0-255] to RGB [0-1]
            color = (color_rgba[0] / 255.0, color_rgba[1] / 255.0, color_rgba[2] / 255.0)
        else:
            color = (0.7, 0.7, 0.7)  # Default gray

        # Get floor z level from config
        z_level = self.config.get_value("ui_config", "annotation_3d", "floor_z_level")
        if z_level is None:
            z_level = 0.0

        # Create room plane mesh
        room_mesh = self.room_builder.create_room_plane(polygon_2d, z_level, color)

        # Get room ID
        room_id = room_item.room_id

        # Remove old room plane if exists
        if room_id in self.room_geometries:
            self.viewer.remove_room_geometry(room_id)

        # Add new room plane
        self.room_geometries[room_id] = room_mesh
        self.viewer.add_room_geometry(room_id, room_mesh)

    def sync_wall_annotation(self, edge_item):
        """
        Create/update 3D wall geometry for wall annotation.

        Args:
            edge_item: EdgeItem instance from canvas
        """
        if not self.config.get_value("ui_config", "annotation_3d", "enable_wall_geometry"):
            return

        # Get wall height from config
        wall_height = self.config.get_value("ui_config", "annotation_3d", "wall_height")
        if wall_height is None:
            wall_height = 1.5

        # Get start and end positions
        start_2d = edge_item.start_node.pos()
        end_2d = edge_item.end_node.pos()

        # Get wall color from config
        wall_color_rgb = self.config.get_color("wall", "default", "color")
        if wall_color_rgb:
            color = (wall_color_rgb.red() / 255.0,
                    wall_color_rgb.green() / 255.0,
                    wall_color_rgb.blue() / 255.0)
        else:
            color = (0.8, 0.8, 0.8)  # Default light gray

        # Create wall mesh
        wall_mesh = self.wall_builder.create_wall_mesh(
            start_2d, end_2d,
            z_min=0.0,
            z_max=wall_height,
            color=color
        )

        # Get edge ID
        edge_id = getattr(edge_item, 'edge_id', f"edge_{id(edge_item)}")

        # Remove old wall if exists
        if edge_id in self.wall_geometries:
            self.viewer.remove_wall_geometry(edge_id)

        # Add new wall
        self.wall_geometries[edge_id] = wall_mesh
        self.viewer.add_wall_geometry(edge_id, wall_mesh)

    def remove_room_annotation(self, room_id: str):
        """
        Remove room plane geometry.

        Args:
            room_id: Room identifier
        """
        if room_id in self.room_geometries:
            self.viewer.remove_room_geometry(room_id)
            del self.room_geometries[room_id]

    def remove_wall_annotation(self, edge_id: str):
        """
        Remove virtual wall geometry.

        Args:
            edge_id: Edge identifier
        """
        if edge_id in self.wall_geometries:
            self.viewer.remove_wall_geometry(edge_id)
            del self.wall_geometries[edge_id]

    def update_all_annotations(self, scene):
        """
        Full rebuild of all annotation geometries from current scene state.

        Called on undo/redo or other major state changes.

        Args:
            scene: QGraphicsScene containing all annotation items
        """
        # Clear all room geometries
        for room_id in list(self.room_geometries.keys()):
            self.viewer.remove_room_geometry(room_id)
        self.room_geometries.clear()

        # Clear all wall geometries
        for edge_id in list(self.wall_geometries.keys()):
            self.viewer.remove_wall_geometry(edge_id)
        self.wall_geometries.clear()

        # Import here to avoid circular dependency
        from src.gui.items import RoomItem, EdgeItem

        # Rebuild all annotations from scene
        for item in scene.items():
            if isinstance(item, RoomItem):
                self.sync_room_annotation(item)
            elif isinstance(item, EdgeItem):
                self.sync_wall_annotation(item)
