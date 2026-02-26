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

from src.core.coordinate_system import CoordinateSystem


class RoomPlaneBuilder:
    """
    Creates horizontal polygon planes for room annotations.

    Generates colored floor planes at a specified z-level to represent
    room boundaries in 3D space.
    """

    def create_room_plane(self, polygon_2d: List[QPointF], z_level: float,
                         color: Tuple[float, float, float],
                         coord_sys: CoordinateSystem | None = None) -> o3d.geometry.TriangleMesh:
        """
        Create a horizontal polygon mesh at z_level.

        Args:
            polygon_2d: List of QPointF defining room boundary (floor_h, floor_v)
            z_level: Height coordinate for the plane (floor level)
            color: RGB tuple in [0-1] range
            coord_sys: Coordinate system for axis mapping (defaults to ROS)

        Returns:
            Open3D TriangleMesh of the room floor plane
        """
        if len(polygon_2d) < 3:
            return o3d.geometry.TriangleMesh()

        cs = coord_sys or CoordinateSystem.ros()
        vertices_3d = [cs.make_3d_point(p.x(), p.y(), z_level) for p in polygon_2d]

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
                        color: Tuple[float, float, float],
                        coord_sys: CoordinateSystem | None = None) -> o3d.geometry.TriangleMesh:
        """
        Create vertical wall plane mesh.

        Args:
            start_2d: Wall start point (floor_h, floor_v)
            end_2d: Wall end point (floor_h, floor_v)
            z_min: Bottom height coordinate
            z_max: Top height coordinate
            color: RGB tuple in [0-1] range
            coord_sys: Coordinate system for axis mapping (defaults to ROS)

        Returns:
            Open3D TriangleMesh representing the wall
        """
        cs = coord_sys or CoordinateSystem.ros()
        vertices = [
            cs.make_3d_point(start_2d.x(), start_2d.y(), z_min),
            cs.make_3d_point(start_2d.x(), start_2d.y(), z_max),
            cs.make_3d_point(end_2d.x(), end_2d.y(), z_max),
            cs.make_3d_point(end_2d.x(), end_2d.y(), z_min),
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


class ObjectGeometryBuilder:
    """
    Creates 3D OBB wireframe boxes for object annotations.
    """

    def create_object_box(self, center: Tuple[float, float], width: float, height: float,
                          angle: float, z_min: float, z_max: float,
                          color: Tuple[float, float, float],
                          coord_sys: CoordinateSystem | None = None) -> o3d.geometry.LineSet:
        """
        Create a 3D oriented bounding box wireframe.

        Args:
            center: (floor_h, floor_v) center position
            width: Box width in scene units
            height: Box height in scene units
            angle: Rotation angle in degrees
            z_min: Bottom height coordinate
            z_max: Top height coordinate
            color: RGB tuple in [0-1] range
            coord_sys: Coordinate system for axis mapping (defaults to ROS)

        Returns:
            Open3D LineSet of the oriented box wireframe
        """
        import math
        cs = coord_sys or CoordinateSystem.ros()
        cx, cy = center
        w, h = width / 2, height / 2
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        # 4 corner offsets in local frame
        local_corners = [(-w, -h), (w, -h), (w, h), (-w, h)]

        # Compute 8 3D vertices (4 bottom + 4 top)
        vertices = []
        for z in [z_min, z_max]:
            for dx, dy in local_corners:
                rx = dx * cos_a - dy * sin_a
                ry = dx * sin_a + dy * cos_a
                vertices.append(cs.make_3d_point(cx + rx, cy + ry, z))

        # 12 edges: 4 bottom + 4 top + 4 vertical
        lines = [
            # Bottom face edges (vertices 0-3)
            [0, 1], [1, 2], [2, 3], [3, 0],
            # Top face edges (vertices 4-7)
            [4, 5], [5, 6], [6, 7], [7, 4],
            # Vertical edges
            [0, 4], [1, 5], [2, 6], [3, 7],
        ]

        line_set = o3d.geometry.LineSet()
        line_set.points = o3d.utility.Vector3dVector(vertices)
        line_set.lines = o3d.utility.Vector2iVector(lines)
        line_set.colors = o3d.utility.Vector3dVector([color] * len(lines))
        return line_set


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
        self.object_builder = ObjectGeometryBuilder()

        # Coordinate system (default ROS, updated via set_coordinate_system)
        self._coord_sys: CoordinateSystem = CoordinateSystem.ros()

        # World bounds for coordinate conversion (scene → world floor_v)
        self._world_bounds = None  # (min_h, min_v, max_h, max_v)

        # Track created geometries
        self.room_geometries: Dict[str, o3d.geometry.TriangleMesh] = {}
        self.wall_geometries: Dict[str, o3d.geometry.TriangleMesh] = {}
        self.custom_polygon_geometries: Dict[str, o3d.geometry.TriangleMesh] = {}
        self.object_geometries: Dict[str, o3d.geometry.LineSet] = {}

        # Runtime visibility state (categories hidden by user via UI)
        self._hidden_categories: set = set()

        # Enabled flag (disabled in occupancy grid mode to skip 3D sync)
        self._enabled = True

    def set_enabled(self, enabled: bool):
        """Enable or disable 3D annotation sync.

        Disabled in occupancy grid mode to skip unnecessary 3D geometry creation.
        """
        self._enabled = enabled

    def set_coordinate_system(self, coord_sys: CoordinateSystem):
        """Update the coordinate system used for 3D geometry construction."""
        self._coord_sys = coord_sys

    def set_world_bounds(self, bounds):
        """Store world bounding box for scene→world floor-v axis conversion.

        Args:
            bounds: (min_h, min_v, max_h, max_v) from project_to_image
        """
        self._world_bounds = bounds

    def _to_world_floor_v(self, scene_v: float) -> float:
        """Convert Qt scene vertical coordinate to world floor-v coordinate.

        When flip_floor_v is True, the 2D projection flipped the second
        floor axis, so we invert it back here. When False, scene coordinate
        equals world coordinate directly.
        """
        if self._world_bounds is None:
            return scene_v
        if not self._coord_sys.flip_floor_v:
            return scene_v
        min_v, max_v = self._world_bounds[1], self._world_bounds[3]
        return (max_v + min_v) - scene_v

    def initialize_geometry(self, geometry):
        """
        Initialize after geometry load.

        Note: No longer needed for room synchronization since we're not
        coloring existing points. Kept for compatibility.

        Args:
            geometry: Open3D PointCloud or TriangleMesh (ignored)
        """
        pass  # No action needed with new approach

    def set_category_visibility(self, category: str, visible: bool):
        """Show/hide all annotations of a category in 3D viewer."""
        if visible:
            self._hidden_categories.discard(category)
        else:
            self._hidden_categories.add(category)
        self._apply_category_visibility(category, visible)

    def _apply_category_visibility(self, category: str, visible: bool):
        """Add/remove all geometries of a category from renderer."""
        geo_map = {
            "room": (self.room_geometries, self.viewer.add_room_geometry, self.viewer.remove_room_geometry),
            "wall": (self.wall_geometries, self.viewer.add_wall_geometry, self.viewer.remove_wall_geometry),
            "custom_polygon": (self.custom_polygon_geometries, self.viewer.add_custom_polygon_geometry, self.viewer.remove_custom_polygon_geometry),
            "object": (self.object_geometries, self.viewer.add_object_geometry, self.viewer.remove_object_geometry),
        }
        geometries, add_fn, remove_fn = geo_map[category]
        for geo_id, mesh in geometries.items():
            if visible:
                add_fn(geo_id, mesh)
            else:
                remove_fn(geo_id)

    def sync_room_annotation(self, room_item):
        """
        Create/update 3D plane for a room annotation.

        Creates a horizontal colored polygon plane at floor level to
        represent the room in 3D space.

        Args:
            room_item: RoomItem instance from canvas
        """
        if not self._enabled:
            return
        # Check if room planes are enabled
        if not self.config.get_ui_value("annotation_3d", "enable_room_planes"):
            return

        # Extract polygon from room nodes and convert to world coordinates
        polygon_2d = [
            QPointF(node.pos().x(), self._to_world_floor_v(node.pos().y()))
            for node in room_item.nodes
        ]

        # Get room color from config
        room_type_conf = self.config.get_room_type(room_item.room_type)
        if room_type_conf:
            color_rgba = room_type_conf.get("color", [200, 200, 200, 100])
            # Convert RGBA [0-255] to RGB [0-1]
            color = (color_rgba[0] / 255.0, color_rgba[1] / 255.0, color_rgba[2] / 255.0)
        else:
            color = (0.7, 0.7, 0.7)  # Default gray

        # Floor level from coordinate system
        z_level = self._coord_sys.floor_level

        # Create room plane mesh
        room_mesh = self.room_builder.create_room_plane(
            polygon_2d, z_level, color, self._coord_sys
        )

        # Get room ID
        room_id = room_item.room_id

        # Remove old room plane if exists
        if room_id in self.room_geometries:
            self.viewer.remove_room_geometry(room_id)

        # Store geometry; only add to renderer if category is visible
        self.room_geometries[room_id] = room_mesh
        if "room" not in self._hidden_categories:
            self.viewer.add_room_geometry(room_id, room_mesh)

    def sync_wall_annotation(self, edge_item):
        """
        Create/update 3D wall geometry for wall annotation.

        Args:
            edge_item: EdgeItem instance from canvas
        """
        if not self._enabled:
            return
        if not self.config.get_ui_value("annotation_3d", "enable_wall_geometry"):
            return

        # Get wall height from config
        wall_height = self.config.get_ui_value("annotation_3d", "wall_height")

        # Get start and end positions (converted to world coordinates)
        start_2d = QPointF(
            edge_item.start_node.pos().x(),
            self._to_world_floor_v(edge_item.start_node.pos().y())
        )
        end_2d = QPointF(
            edge_item.end_node.pos().x(),
            self._to_world_floor_v(edge_item.end_node.pos().y())
        )

        # Get wall color from config
        wall_color_rgb = self.config.get_color("wall", "default", "color")
        if wall_color_rgb:
            color = (wall_color_rgb.red() / 255.0,
                    wall_color_rgb.green() / 255.0,
                    wall_color_rgb.blue() / 255.0)
        else:
            color = (0.8, 0.8, 0.8)  # Default light gray

        # Create wall mesh using floor level from coordinate system
        floor_level = self._coord_sys.floor_level
        wall_mesh = self.wall_builder.create_wall_mesh(
            start_2d, end_2d,
            z_min=floor_level,
            z_max=floor_level + wall_height,
            color=color,
            coord_sys=self._coord_sys,
        )

        # Get edge ID
        edge_id = getattr(edge_item, 'edge_id', f"edge_{id(edge_item)}")

        # Remove old wall if exists
        if edge_id in self.wall_geometries:
            self.viewer.remove_wall_geometry(edge_id)

        # Store geometry; only add to renderer if category is visible
        self.wall_geometries[edge_id] = wall_mesh
        if "wall" not in self._hidden_categories:
            self.viewer.add_wall_geometry(edge_id, wall_mesh)

    def sync_custom_polygon_annotation(self, polygon_item):
        """Create/update 3D plane for a custom polygon annotation."""
        if not self._enabled:
            return
        if not self.config.get_ui_value("annotation_3d", "enable_custom_polygon_planes"):
            return

        polygon_2d = [
            QPointF(node.pos().x(), self._to_world_floor_v(node.pos().y()))
            for node in polygon_item.nodes
        ]

        poly_type_conf = self.config.get_custom_polygon_type(polygon_item.polygon_type)
        if poly_type_conf:
            color_rgba = poly_type_conf.get("color", [100, 220, 100, 100])
            color = (color_rgba[0] / 255.0, color_rgba[1] / 255.0, color_rgba[2] / 255.0)
        else:
            color = (0.4, 0.85, 0.4)

        z_level = self._coord_sys.floor_level

        mesh = self.room_builder.create_room_plane(
            polygon_2d, z_level, color, self._coord_sys
        )

        polygon_id = polygon_item.polygon_id
        if polygon_id in self.custom_polygon_geometries:
            self.viewer.remove_custom_polygon_geometry(polygon_id)

        # Store geometry; only add to renderer if category is visible
        self.custom_polygon_geometries[polygon_id] = mesh
        if "custom_polygon" not in self._hidden_categories:
            self.viewer.add_custom_polygon_geometry(polygon_id, mesh)

    def sync_object_annotation(self, object_item):
        """Create/update 3D OBB box for an object annotation."""
        if not self._enabled:
            return
        if not self.config.get_ui_value("annotation_3d", "enable_object_boxes"):
            return

        obj_type_conf = self.config.get_object_type(object_item.object_type)
        if obj_type_conf:
            color_rgba = obj_type_conf.get("color", [150, 200, 255, 150])
            color = (color_rgba[0] / 255.0, color_rgba[1] / 255.0, color_rgba[2] / 255.0)
        else:
            color = (0.6, 0.78, 1.0)

        floor_level = self._coord_sys.floor_level
        z_min = floor_level + object_item.elevation
        z_max = z_min + object_item.height_3d

        center = (object_item.center.x(), self._to_world_floor_v(object_item.center.y()))
        mesh = self.object_builder.create_object_box(
            center, object_item.width, object_item.height,
            object_item.angle, z_min, z_max, color,
            coord_sys=self._coord_sys,
        )

        object_id = object_item.object_id
        if object_id in self.object_geometries:
            self.viewer.remove_object_geometry(object_id)

        # Store geometry; only add to renderer if category is visible
        self.object_geometries[object_id] = mesh
        if "object" not in self._hidden_categories:
            self.viewer.add_object_geometry(object_id, mesh)

    def remove_custom_polygon_annotation(self, polygon_id: str):
        """Remove custom polygon plane geometry."""
        if polygon_id in self.custom_polygon_geometries:
            self.viewer.remove_custom_polygon_geometry(polygon_id)
            del self.custom_polygon_geometries[polygon_id]

    def remove_object_annotation(self, object_id: str):
        """Remove object box geometry."""
        if object_id in self.object_geometries:
            self.viewer.remove_object_geometry(object_id)
            del self.object_geometries[object_id]

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
        if not self._enabled:
            return

        # Clear all existing geometries
        for room_id in list(self.room_geometries.keys()):
            self.viewer.remove_room_geometry(room_id)
        self.room_geometries.clear()

        for edge_id in list(self.wall_geometries.keys()):
            self.viewer.remove_wall_geometry(edge_id)
        self.wall_geometries.clear()

        for polygon_id in list(self.custom_polygon_geometries.keys()):
            self.viewer.remove_custom_polygon_geometry(polygon_id)
        self.custom_polygon_geometries.clear()

        for object_id in list(self.object_geometries.keys()):
            self.viewer.remove_object_geometry(object_id)
        self.object_geometries.clear()

        # Import here to avoid circular dependency
        from src.gui.items import RoomItem, EdgeItem, CustomPolygonItem, ObjectItem

        # Rebuild all annotations from scene
        for item in scene.items():
            if isinstance(item, RoomItem):
                self.sync_room_annotation(item)
            elif isinstance(item, EdgeItem):
                self.sync_wall_annotation(item)
            elif isinstance(item, CustomPolygonItem):
                self.sync_custom_polygon_annotation(item)
            elif isinstance(item, ObjectItem):
                self.sync_object_annotation(item)
