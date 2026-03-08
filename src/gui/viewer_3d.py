import open3d as o3d
import open3d.visualization.rendering as rendering
import numpy as np
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QImage, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QTimer, QPoint

from src.gui.viewer_3d_camera_mixin import CameraMixin
from src.gui.viewer_3d_annotation_mixin import AnnotationMixin
from src.core.coordinate_system import CoordinateSystem


class Viewer3D(CameraMixin, AnnotationMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.renderer = None
        self.image = None
        self._image_data = None  # Store numpy array to prevent garbage collection
        self._renderer_failed = False  # Track if renderer initialization failed
        self._shown_once = False  # Track if widget has been shown at least once
        self.on_renderer_ready = None  # Optional callback: called once after renderer is created

        # Coordinate system (default ROS, updated via set_coordinate_system)
        self._coord_sys: CoordinateSystem = CoordinateSystem.ros()

        # Scene Data
        self._axes_size = 1.0
        self.geometry = None
        self.plane_geometry = None
        self.material = None
        self.geometry_visible = True  # Track original geometry visibility
        self.downsampled_geometry = None  # Downsampled copy for fast preview during drag

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

    def set_coordinate_system(self, coord_sys: CoordinateSystem):
        """Update coordinate system. Resets camera and grid if geometry is loaded."""
        self._coord_sys = coord_sys
        if hasattr(self, 'original_geometry') and self.original_geometry:
            self._reset_camera_for_coord_sys()
            self._add_grid_to_scene()
            self.render_scene()

    def _reset_camera_for_coord_sys(self):
        """Reset camera to a top-down position based on the current coordinate system."""
        bbox = self.original_geometry.get_axis_aligned_bounding_box()
        cs = self._coord_sys
        self.camera_center = bbox.get_center()
        extent = bbox.get_max_bound() - bbox.get_min_bound()
        max_extent = max(extent)
        # Position eye along the up axis, looking down
        eye_offset = np.zeros(3)
        eye_offset[cs.up_axis] = max_extent * 2.0 * cs.up_direction
        self.camera_eye = self.camera_center + eye_offset
        # Camera up = floor_v axis (perpendicular to view direction)
        self.camera_up = np.array(cs.camera_up_vector())
        self._axes_size = float(max_extent) * 0.2

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
            bg_img = self._create_gradient_bg(w, h)
            self.renderer.scene.set_background([0.11, 0.137, 0.212, 1.0], bg_img)
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

            self._add_axes_to_scene()
            self._add_grid_to_scene()
            self.render_scene()
            # Notify listeners that renderer is ready (e.g. to re-sync annotations).
            if self.on_renderer_ready:
                self.on_renderer_ready()
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

        Creates both full-resolution and downsampled copies. The downsampled
        version is used for fast preview during slider drag (IMP-002).

        Supported formats:
        - Point clouds: .ply, .pcd
        - Meshes (vertex colors): .ply, .obj, .stl
        - Meshes (UV textures baked to vertex colors): .glb, .gltf  (REQ-031)

        Note: Geometry loading proceeds even when the 3D renderer has failed, so
        that the 2D canvas projection remains functional. _setup_geometry() guards
        renderer access internally.
        """
        try:
            from pathlib import Path
            ext = Path(file_path).suffix.lower()

            if ext in ('.glb', '.gltf'):
                # GLB/GLTF: load via trimesh, bake UV texture → vertex colors (REQ-031)
                geom = self._load_gltf(file_path)
            else:
                # Try mesh first — read_point_cloud() succeeds on mesh PLY
                # files (reads vertices as points, discards faces), so we must
                # try read_triangle_mesh() first to preserve face connectivity.
                geom = o3d.io.read_triangle_mesh(file_path)
                if len(geom.triangles) > 0:
                    geom.compute_vertex_normals()
                    if not geom.has_vertex_colors():
                        geom.paint_uniform_color([0.7, 0.7, 0.7])
                else:
                    geom = o3d.io.read_point_cloud(file_path)

            self.original_geometry = geom

            # Create downsampled copy for fast 3D preview during drag
            from src.core.config import ConfigManager
            config = ConfigManager.instance()
            voxel_size = config.get_ui_value("viewer_3d", "voxel_size")
            if voxel_size > 0:
                if hasattr(geom, 'triangles') and len(geom.triangles) > 0:
                    self.downsampled_geometry = geom.simplify_vertex_clustering(
                        voxel_size=voxel_size,
                    )
                else:
                    self.downsampled_geometry = geom.voxel_down_sample(
                        voxel_size=voxel_size,
                    )
            else:
                self.downsampled_geometry = None

            self._setup_geometry()
        except Exception as e:
            import traceback
            print(f"Warning: load_geometry failed: {e}")
            traceback.print_exc()

    def _load_gltf(self, file_path: str) -> 'o3d.geometry.TriangleMesh':
        """Load a GLB or GLTF file, baking UV textures into vertex colors.

        Uses trimesh for loading and texture baking, then converts to an
        Open3D TriangleMesh so the rest of the pipeline is unchanged.
        """
        import trimesh

        loaded = trimesh.load(file_path)
        if isinstance(loaded, trimesh.Scene):
            # dump() applies each node's global transform before concatenation,
            # unlike geometry.values() which returns local-coordinate geometry.
            meshes = [m for m in loaded.dump() if isinstance(m, trimesh.Trimesh)]
            if not meshes:
                raise ValueError(f"No triangle meshes found in {file_path}")
            loaded = trimesh.util.concatenate(meshes)
        elif not isinstance(loaded, trimesh.Trimesh):
            raise ValueError(f"Unexpected trimesh object type: {type(loaded)}")

        # Bake UV-mapped texture → per-vertex RGBA colors
        if hasattr(loaded.visual, 'to_color'):
            loaded.visual = loaded.visual.to_color()

        vertices = np.asarray(loaded.vertices, dtype=np.float64)
        faces = np.asarray(loaded.faces, dtype=np.int32)

        vc = loaded.visual.vertex_colors
        if vc is not None and len(vc) == len(vertices):
            colors = np.asarray(vc, dtype=np.uint8)[:, :3] / 255.0
        else:
            colors = np.full((len(vertices), 3), 0.7)

        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        mesh.triangles = o3d.utility.Vector3iVector(faces)
        mesh.vertex_colors = o3d.utility.Vector3dVector(np.clip(colors, 0.0, 1.0))
        mesh.compute_vertex_normals()
        return mesh

    def set_geometry(self, geometry):
        """Set pre-created geometry directly (no file loading).

        Used for generated meshes like occupancy grid 3D visualization.
        No downsampling is performed.

        Args:
            geometry: Open3D PointCloud or TriangleMesh object.
        """
        if self._renderer_failed:
            print("Warning: Viewer3D renderer failed, cannot set geometry")
            return

        try:
            self.original_geometry = geometry
            self.downsampled_geometry = None
            self._setup_geometry()
        except Exception as e:
            print(f"Warning: set_geometry failed: {e}")

    def _setup_geometry(self):
        """Common setup after geometry is assigned to original_geometry.

        Copies geometry, resets camera, sets up plane, and updates renderer.
        """
        import copy
        self.geometry = copy.deepcopy(self.original_geometry)

        # Center camera based on coordinate system
        self._reset_camera_for_coord_sys()

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

        self._add_axes_to_scene()
        self._add_grid_to_scene()
        self.render_scene()

    def _update_plane_indicator(self, z_height):
        """Update the red slice plane indicator line at z_height.

        Shared by both dragging and final update paths.
        """
        if not self.renderer:
            return

        bbox = self.original_geometry.get_axis_aligned_bounding_box()
        min_b = bbox.get_min_bound()
        max_b = bbox.get_max_bound()

        cs = self._coord_sys
        fh, fv = cs.floor_column_h(), cs.floor_column_v()
        points = [
            cs.make_3d_point(min_b[fh], min_b[fv], z_height),
            cs.make_3d_point(max_b[fh], min_b[fv], z_height),
            cs.make_3d_point(max_b[fh], max_b[fv], z_height),
            cs.make_3d_point(min_b[fh], max_b[fv], z_height),
        ]
        lines = [[0, 1], [1, 2], [2, 3], [3, 0]]
        colors = [[1, 0, 0] for _ in range(len(lines))]

        self.plane_geometry.points = o3d.utility.Vector3dVector(points)
        self.plane_geometry.lines = o3d.utility.Vector2iVector(lines)
        self.plane_geometry.colors = o3d.utility.Vector3dVector(colors)

        self.renderer.scene.remove_geometry("plane")
        mat_plane = rendering.MaterialRecord()
        mat_plane.shader = "unlitLine"
        mat_plane.line_width = 2.0
        self.renderer.scene.add_geometry("plane", self.plane_geometry, mat_plane)

    def _crop_and_display(self, source_geometry, z_height):
        """Crop source_geometry up to z_height and display in scene.

        Args:
            source_geometry: Geometry to crop (original or downsampled)
            z_height: Crop upper bound along the up axis
        """
        if not self.renderer:
            return

        bbox = self.original_geometry.get_axis_aligned_bounding_box()
        min_b = list(bbox.get_min_bound())
        max_b = list(bbox.get_max_bound())

        ua = self._coord_sys.up_axis
        if self._coord_sys.up_direction == 1:
            min_b[ua] -= 100.0
            max_b[ua] = z_height
        else:
            min_b[ua] = z_height
            max_b[ua] += 100.0

        crop_box = o3d.geometry.AxisAlignedBoundingBox(
            min_bound=min_b,
            max_bound=max_b,
        )

        new_geometry = source_geometry.crop(crop_box)

        self.renderer.scene.remove_geometry("geometry")
        if not new_geometry.is_empty():
            self.geometry = new_geometry
            self.renderer.scene.add_geometry("geometry", self.geometry, self.material)

        self.render_scene()

    def update_slice_dragging(self, z_height):
        """Fast 3D update during slider drag using downsampled geometry.

        Falls back to full-resolution if downsampling is disabled.
        """
        if self._renderer_failed:
            return
        if not hasattr(self, 'original_geometry') or not self.original_geometry:
            return

        self._update_plane_indicator(z_height)

        source = self.downsampled_geometry or self.original_geometry
        self._crop_and_display(source, z_height)

    def update_slice_final(self, z_height):
        """Full-resolution 3D update when slider stops."""
        if self._renderer_failed:
            return
        if not hasattr(self, 'original_geometry') or not self.original_geometry:
            return

        self._update_plane_indicator(z_height)
        self._crop_and_display(self.original_geometry, z_height)

    def update_slice_plane(self, z_height):
        """Update the slice plane visualization (legacy, uses full-resolution)."""
        self.update_slice_final(z_height)

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
        

    def _add_axes_to_scene(self):
        """Add RGB coordinate axes (X=red, Y=green, Z=blue) at world origin (0,0,0)."""
        if not self.renderer or self._renderer_failed:
            return

        if hasattr(self, 'original_geometry') and self.original_geometry:
            bbox = self.original_geometry.get_axis_aligned_bounding_box()
            extent = bbox.get_max_bound() - bbox.get_min_bound()
            size = float(max(extent)) * 0.2
        else:
            size = self._axes_size

        points = [
            [0, 0, 0], [size, 0, 0],
            [0, 0, 0], [0, size, 0],
            [0, 0, 0], [0, 0, size],
        ]
        lines = [[0, 1], [2, 3], [4, 5]]
        colors = [[0.86, 0.2, 0.2], [0.2, 0.7, 0.2], [0.2, 0.2, 0.86]]

        axes_ls = o3d.geometry.LineSet()
        axes_ls.points = o3d.utility.Vector3dVector(points)
        axes_ls.lines = o3d.utility.Vector2iVector(lines)
        axes_ls.colors = o3d.utility.Vector3dVector(colors)

        self.renderer.scene.remove_geometry("origin_axes")
        mat = rendering.MaterialRecord()
        mat.shader = "unlitLine"
        mat.line_width = 3.0
        self.renderer.scene.add_geometry("origin_axes", axes_ls, mat)

    def _create_gradient_bg(self, w: int, h: int):
        """Create a top-to-bottom navy gradient as an Open3D Image for background."""
        top = np.array([18, 22, 35], dtype=np.float32)
        bot = np.array([38, 48, 72], dtype=np.float32)
        t = np.linspace(0.0, 1.0, h).reshape(-1, 1, 1)
        gradient = (top * (1.0 - t) + bot * t)             # shape (h, 1, 3)
        gradient = np.broadcast_to(gradient, (h, w, 3)).copy().astype(np.uint8)
        return o3d.geometry.Image(gradient)

    def _add_grid_to_scene(self):
        """Add ground plane grid at floor_level on the floor axes as a LineSet."""
        if not self.renderer or self._renderer_failed:
            return

        cs = self._coord_sys
        fh, fv = cs.floor_column_h(), cs.floor_column_v()

        if hasattr(self, 'original_geometry') and self.original_geometry:
            bbox = self.original_geometry.get_axis_aligned_bounding_box()
            min_b = bbox.get_min_bound()
            max_b = bbox.get_max_bound()
            extent = max(max_b[fh] - min_b[fh], max_b[fv] - min_b[fv])
        else:
            min_b = np.array([-5.0, -5.0, -5.0])
            max_b = np.array([5.0, 5.0, 5.0])
            extent = 10.0

        spacing = self._grid_spacing(extent)
        floor_z = cs.floor_level

        h0 = math.floor(min_b[fh] / spacing) * spacing
        h1 = math.ceil(max_b[fh] / spacing) * spacing
        v0 = math.floor(min_b[fv] / spacing) * spacing
        v1 = math.ceil(max_b[fv] / spacing) * spacing

        points, lines = [], []
        for h in np.arange(h0, h1 + spacing * 0.5, spacing):
            i = len(points)
            points += [cs.make_3d_point(h, v0, floor_z), cs.make_3d_point(h, v1, floor_z)]
            lines.append([i, i + 1])
        for v in np.arange(v0, v1 + spacing * 0.5, spacing):
            i = len(points)
            points += [cs.make_3d_point(h0, v, floor_z), cs.make_3d_point(h1, v, floor_z)]
            lines.append([i, i + 1])

        if not points:
            return

        grid_color = [0.255, 0.314, 0.451]   # muted blue-gray
        ls = o3d.geometry.LineSet()
        ls.points = o3d.utility.Vector3dVector(points)
        ls.lines = o3d.utility.Vector2iVector(lines)
        ls.colors = o3d.utility.Vector3dVector([grid_color] * len(lines))

        self.renderer.scene.remove_geometry("grid")
        mat = rendering.MaterialRecord()
        mat.shader = "unlitLine"
        mat.line_width = 1.0
        self.renderer.scene.add_geometry("grid", ls, mat)

    def _grid_spacing(self, extent: float) -> float:
        """Compute a clean grid spacing for the given scene extent (~10 divisions)."""
        if extent <= 0:
            return 1.0
        raw = extent / 10.0
        mag = 10.0 ** math.floor(math.log10(raw))
        n = raw / mag
        if n < 1.5:
            return mag
        elif n < 3.5:
            return 2.0 * mag
        elif n < 7.5:
            return 5.0 * mag
        return 10.0 * mag



