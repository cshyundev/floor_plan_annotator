import open3d as o3d
import open3d.visualization.rendering as rendering
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QImage, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QTimer, QPoint

class Viewer3D(QWidget):
    def __init__(self):
        super().__init__()
        self.renderer = None
        self.image = None
        self._image_data = None  # Store numpy array to prevent garbage collection
        self._renderer_failed = False  # Track if renderer initialization failed
        self._shown_once = False  # Track if widget has been shown at least once

        # Scene Data
        self.geometry = None
        self.plane_geometry = None
        self.material = None
        self.geometry_visible = True  # Track original geometry visibility

        # Camera State
        self.camera_eye = np.array([0.0, 0.0, 10.0])
        self.camera_center = np.array([0.0, 0.0, 0.0])
        self.camera_up = np.array([0.0, 1.0, 0.0])
        self.fov = 60.0

        # Interaction State
        self.last_mouse_pos = QPoint()
        self.is_rotating = False
        self.is_panning = False

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Initial Material
        try:
            self.material = rendering.MaterialRecord()
            self.material.shader = "defaultLit"
        except Exception as e:
            print(f"Warning: Failed to create material: {e}")
            self.material = None
            self._renderer_failed = True

    def _create_renderer(self, w, h):
        """Create or recreate the OffscreenRenderer with given dimensions.

        Args:
            w: Width in pixels
            h: Height in pixels
        """
        try:
            # Clean up old renderer if it exists
            if self.renderer is not None:
                try:
                    # Clear scene before destroying renderer
                    self.renderer.scene.clear_geometry()
                except:
                    pass
                # Delete old renderer
                del self.renderer
                self.renderer = None

            # Create new renderer
            self.renderer = rendering.OffscreenRenderer(w, h)
            self.renderer.scene.set_background([0.9, 0.9, 0.9, 1.0])
            self.renderer.scene.scene.set_sun_light([0.707, 0.0, -0.707], [1.0, 1.0, 1.0], 75000)
            self.renderer.scene.scene.enable_sun_light(True)

            # Re-add geometries if they exist
            if self.geometry and self.material:
                self.renderer.scene.add_geometry("geometry", self.geometry, self.material)
            if self.plane_geometry:
                mat = rendering.MaterialRecord()
                mat.shader = "unlitLine"
                mat.line_width = 2.0
                self.renderer.scene.add_geometry("plane", self.plane_geometry, mat)

            self.render_scene()
        except Exception as e:
            # Prevent crashes from renderer creation failures
            print(f"Warning: Viewer3D renderer creation failed: {e}")
            print("Viewer3D disabled due to Open3D OffscreenRenderer failure.")
            print("This is likely due to missing OpenGL support in the environment.")
            self._renderer_failed = True
            self.renderer = None
            self.update()

    def showEvent(self, event):
        """Mark that widget has been shown - schedule renderer creation."""
        super().showEvent(event)
        self._shown_once = True

        # Schedule renderer creation after event processing is complete
        from PyQt6.QtCore import QTimer
        def create_renderer_delayed():
            if not self.renderer and not self._renderer_failed:
                w, h = self.width(), self.height()
                if w > 0 and h > 0:
                    self._create_renderer(w, h)

        QTimer.singleShot(200, create_renderer_delayed)

    def resizeEvent(self, event):
        """Handle resize event safely to prevent crashes.

        Note: OffscreenRenderer recreation is expensive, so we add safety checks.
        Defers renderer creation until widget is shown at least once to avoid OpenGL context issues.
        If renderer fails to initialize, widget gracefully degrades to showing error message.
        """
        super().resizeEvent(event)

        w = event.size().width()
        h = event.size().height()

        # Skip if renderer previously failed
        if self._renderer_failed:
            return

        # Skip until widget has been shown at least once
        if not self._shown_once:
            return

        # Validate dimensions
        if w <= 0 or h <= 0:
            return

        # Create or recreate renderer
        self._create_renderer(w, h)

    def load_geometry(self, file_path):
        """Load 3D geometry from file.

        Note: Gracefully handles renderer failure by loading geometry but not displaying.
        """
        if self._renderer_failed:
            print("Warning: Viewer3D renderer failed, cannot load geometry")
            return

        try:
            # Load Mesh or Point Cloud
            geom = o3d.io.read_point_cloud(file_path)
            if geom.is_empty():
                geom = o3d.io.read_triangle_mesh(file_path)
                geom.compute_vertex_normals()
                if not geom.has_vertex_colors():
                    geom.paint_uniform_color([0.7, 0.7, 0.7])

            self.original_geometry = geom

            # Keep a copy for slicing (initially full)
            import copy
            self.geometry = copy.deepcopy(self.original_geometry)

            # Center camera (only on new load)
            bbox = self.geometry.get_axis_aligned_bounding_box()
            self.camera_center = bbox.get_center()
            extent = bbox.get_max_bound() - bbox.get_min_bound()
            max_extent = max(extent)
            self.camera_eye = self.camera_center + np.array([0, 0, max_extent * 2.0])
            self.camera_up = np.array([0, 1, 0])

            # Setup Plane placeholder
            self.plane_geometry = o3d.geometry.LineSet()

            # Update Renderer
            if self.renderer and self.material:
                self.renderer.scene.clear_geometry()
                self.renderer.scene.add_geometry("geometry", self.geometry, self.material)

                mat_plane = rendering.MaterialRecord()
                mat_plane.shader = "unlitLine"
                mat_plane.line_width = 2.0
                self.renderer.scene.add_geometry("plane", self.plane_geometry, mat_plane)

            self.render_scene()
        except Exception as e:
            print(f"Warning: load_geometry failed: {e}")

    def update_slice_plane(self, z_height):
        """Update the slice plane visualization.

        Note: Gracefully handles renderer failure.
        """
        # Skip if renderer failed
        if self._renderer_failed:
            return

        # 1. Update Slice Plane Visualization
        if not hasattr(self, 'original_geometry') or not self.original_geometry:
            return
            
        # 2. Update Plane Geometry (Visual Indicator)
        bbox = self.original_geometry.get_axis_aligned_bounding_box()
        min_b = bbox.get_min_bound()
        max_b = bbox.get_max_bound()
        
        points = [
            [min_b[0], min_b[1], z_height],
            [max_b[0], min_b[1], z_height],
            [max_b[0], max_b[1], z_height],
            [min_b[0], max_b[1], z_height],
        ]
        lines = [[0, 1], [1, 2], [2, 3], [3, 0]]
        colors = [[1, 0, 0] for _ in range(len(lines))]
        
        self.plane_geometry.points = o3d.utility.Vector3dVector(points)
        self.plane_geometry.lines = o3d.utility.Vector2iVector(lines)
        self.plane_geometry.colors = o3d.utility.Vector3dVector(colors)
        
        # 3. Crop Geometry
        # Crop from bottom up to z_height
        # Note: crop is non-destructive usually returns new geometry
        crop_box = o3d.geometry.AxisAlignedBoundingBox(
            min_bound=[min_b[0], min_b[1], min_b[2] - 100.0], # Allow some margin below
            max_bound=[max_b[0], max_b[1], z_height]
        )
        
        new_geometry = self.original_geometry.crop(crop_box)
        
        # 4. Update Renderer
        if self.renderer:
            # Update Plane
            self.renderer.scene.remove_geometry("plane")
            mat_plane = rendering.MaterialRecord()
            mat_plane.shader = "unlitLine"
            mat_plane.line_width = 2.0
            self.renderer.scene.add_geometry("plane", self.plane_geometry, mat_plane)
            
            # Update Geometry
            self.renderer.scene.remove_geometry("geometry")
            
            if not new_geometry.is_empty():
                self.geometry = new_geometry
                self.renderer.scene.add_geometry("geometry", self.geometry, self.material)
            else:
                # Handle empty geometry case
                # Open3D might not like remove_geometry if it wasn't there, but we just removed it.
                # If we don't add anything back, the scene effectively has no "geometry" object.
                # Next update will try to remove "geometry". Does remove_geometry throw if not found?
                # It usually logs a warning but doesn't crash.
                # To be safe, we can track if geometry is in scene.
                pass
            
            self.render_scene()

    def render_scene(self):
        """Render the 3D scene to an image.

        CRITICAL: Store numpy array as instance variable to prevent garbage collection!
        QImage references the numpy array's memory, so we must keep it alive.
        """
        if not self.renderer:
            return

        try:
            self.renderer.setup_camera(self.fov, self.camera_center, self.camera_eye, self.camera_up)
            img_np = np.asarray(self.renderer.render_to_image())

            # CRITICAL: Store copy as instance variable to keep it alive
            self._image_data = np.copy(img_np)

            # Convert to QImage
            h, w, c = self._image_data.shape
            bytes_per_line = 3 * w

            # Create QImage from the stored data
            q_image = QImage(
                self._image_data.data,
                w, h,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )

            # Make another copy to ensure QImage owns its data
            self.image = q_image.copy()

            self.update()  # Schedule repaint
        except Exception as e:
            # Prevent crashes from render failures
            print(f"Warning: render_scene failed: {e}")

    def paintEvent(self, event):
        """Paint the 3D view.

        Note: Wrapped in try-except to prevent crashes from paint failures.
        Shows error message if renderer initialization failed.
        """
        try:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(240, 240, 240))

            if self._renderer_failed:
                # Show error message
                painter.setPen(QColor(200, 0, 0))
                font = QFont()
                font.setPointSize(12)
                painter.setFont(font)
                painter.drawText(
                    self.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    "Viewer3D Disabled\n\nOpen3D OffscreenRenderer failed to initialize.\n"
                    "This is likely due to missing OpenGL support.\n\n"
                    "The 2D canvas still works normally."
                )
            elif self.image:
                painter.drawImage(0, 0, self.image)
            else:
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Data / Loading...")
        except Exception as e:
            print(f"Warning: paintEvent failed: {e}")

    # --- Interaction ---
    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_rotating = True
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = True
    
    def mouseReleaseEvent(self, event):
        self.is_rotating = False
        self.is_panning = False

    def mouseMoveEvent(self, event):
        dx = event.pos().x() - self.last_mouse_pos.x()
        dy = event.pos().y() - self.last_mouse_pos.y()
        self.last_mouse_pos = event.pos()
        
        if self.is_rotating:
            self.orbit_camera(dx, dy)
        elif self.is_panning:
            self.pan_camera(dx, dy)
            
    def wheelEvent(self, event):
        # Zoom
        delta = event.angleDelta().y()
        self.zoom_camera(delta)
        
    def orbit_camera(self, dx, dy):
        # Simple Orbit around camera_center
        # Azimuth (dx) and Elevation (dy)
        
        # Convert to spherical? Or just rotate vector
        # Vector from center to eye
        v = self.camera_eye - self.camera_center
        
        # Rotate around Up axis (Azimuth)
        # We need to construct interaction properly, but for now simple approximation:
        # X movement rotates around World UP (0,1,0)
        # Y movement rotates around Right vector
        
        # ... Implementation of rotation matrix ...
        # Using Open3D geometry functions or numpy
        
        sensitivity = 0.01
        alpha = -dx * sensitivity
        beta = -dy * sensitivity
        
        # Rotate around Y (Global Up)
        import math
        # Axis Angle rotation?
        
        # Right vector
        forward = (self.camera_center - self.camera_eye)
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, self.camera_up)
        right = right / np.linalg.norm(right)
        
        # Rotate v around Y
        R_y = self.rotation_matrix(np.array([0, 1, 0]), alpha)
        v = R_y @ v
        
        # Rotate v around Right
        R_x = self.rotation_matrix(right, beta)
        v = R_x @ v
        
        # Update Eye
        self.camera_eye = self.camera_center + v
        # Re-orthogonalize Up? 
        # For simple orbit, keeping Up as (0,1,0) usually works unless we pitch too far.
        # Let's keep it simple.
        
        self.render_scene()
        
    def pan_camera(self, dx, dy):
        sensitivity = 0.01
        
        forward = (self.camera_center - self.camera_eye)
        dist = np.linalg.norm(forward)
        forward = forward / dist
        
        right = np.cross(forward, self.camera_up)
        right = right / np.linalg.norm(right)
        
        up = np.cross(right, forward)
        
        # Scale movement by distance
        move = -right * dx * sensitivity * (dist/10.0) + up * dy * sensitivity * (dist/10.0)
        
        self.camera_eye += move
        self.camera_center += move
        
        self.render_scene()

    def zoom_camera(self, delta):
        # Move eye towards center
        v = self.camera_center - self.camera_eye
        dist = np.linalg.norm(v)
        
        zoom_speed = 0.1 * (dist if dist > 0.1 else 0.1)
        
        if delta > 0:
            step = 1.0 * zoom_speed
        else:
            step = -1.0 * zoom_speed
            
        move = (v / dist) * step
        
        # Don't pass center
        if np.linalg.norm(move) < dist:
            self.camera_eye += move
        
        self.render_scene()

    def rotation_matrix(self, axis, theta):
        """
        Return the rotation matrix associated with counterclockwise rotation about
        the given axis by theta radians.
        """
        axis = np.asarray(axis)
        axis = axis / math.sqrt(np.dot(axis, axis))
        a = math.cos(theta / 2.0)
        b, c, d = -axis * math.sin(theta / 2.0)
        aa, bb, cc, dd = a * a, b * b, c * c, d * d
        bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
        return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                         [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                         [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])

    # --- Annotation Sync Methods ---
    def add_room_geometry(self, room_id: str, room_mesh):
        """
        Add room floor plane to scene.

        Args:
            room_id: Unique room identifier
            room_mesh: TriangleMesh of the room floor plane
        """
        if not self.renderer or self._renderer_failed:
            return

        # Always remove first to prevent duplicate-name silent failure in Open3D
        self.renderer.scene.remove_geometry(f"room_{room_id}")
        mat = rendering.MaterialRecord()
        mat.shader = "defaultLit"
        self.renderer.scene.add_geometry(f"room_{room_id}", room_mesh, mat)
        self.render_scene()

    def remove_room_geometry(self, room_id: str):
        """Remove room floor plane from scene."""
        if not self.renderer or self._renderer_failed:
            return

        self.renderer.scene.remove_geometry(f"room_{room_id}")
        self.render_scene()

    def add_wall_geometry(self, wall_id: str, wall_mesh):
        """
        Add virtual wall geometry to scene.

        Creates a 3D wall plane from 2D wall annotation.

        Args:
            wall_id: Unique identifier for the wall (e.g., "edge_12345")
            wall_mesh: Open3D TriangleMesh representing the wall
        """
        if not self.renderer or self._renderer_failed:
            return

        # Always remove first to prevent duplicate-name silent failure in Open3D
        self.renderer.scene.remove_geometry(f"wall_{wall_id}")
        mat = rendering.MaterialRecord()
        mat.shader = "defaultLit"
        self.renderer.scene.add_geometry(f"wall_{wall_id}", wall_mesh, mat)
        self.render_scene()

    def remove_wall_geometry(self, wall_id: str):
        """
        Remove virtual wall geometry from scene.

        Args:
            wall_id: Unique identifier for the wall to remove
        """
        if not self.renderer or self._renderer_failed:
            return

        # Remove from scene
        self.renderer.scene.remove_geometry(f"wall_{wall_id}")

        # Re-render
        self.render_scene()

    def clear_all_walls(self):
        """Remove all virtual wall geometries from scene."""
        # Note: This requires tracking wall IDs externally
        # Current implementation relies on annotation_sync to track and remove individually
        pass

    def set_geometry_visibility(self, visible: bool):
        """
        Toggle visibility of original geometry (point cloud/mesh).

        Args:
            visible: True to show, False to hide
        """
        if not self.renderer or self._renderer_failed:
            return

        self.geometry_visible = visible

        if visible:
            # Add geometry back to scene
            if self.geometry and self.material:
                self.renderer.scene.add_geometry("geometry", self.geometry, self.material)
        else:
            # Remove geometry from scene
            self.renderer.scene.remove_geometry("geometry")

        self.render_scene()

import math

