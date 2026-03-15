"""3D viewer for map alignment.

Renders reference and source point clouds using Open3D OffscreenRenderer.
Source transform is controlled externally via the controls panel.
Camera supports orbit/pan/zoom via CameraMixin.
"""

import copy
import math

import numpy as np
import open3d as o3d
import open3d.visualization.rendering as rendering
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QImage, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal

from src.core.config import ConfigManager
from src.gui.viewer_3d_camera_mixin import CameraMixin
from src.map_align.alignment_state import AlignmentState


class TopDownView(CameraMixin, QWidget):
    """3D viewer with keyboard/scroll shortcuts for transform.

    Camera: Left-drag orbit, Mid-drag pan, Scroll zoom, F fit
    Transform: Arrow TX/TY, PgUp/Dn TZ, [ ] Yaw,
               Shift+Scroll Yaw, Ctrl+Scroll TZ
    """

    transform_changed = pyqtSignal()
    registration_requested = pyqtSignal()

    def __init__(self, state: AlignmentState, parent=None):
        super().__init__(parent)
        self._state = state
        self._config = ConfigManager.instance()

        # Renderer state
        self.renderer = None
        self.image = None
        self._image_data = None
        self._renderer_failed = False
        self._shown_once = False

        # Camera state (from config)
        eye = self._config.get_ui_value("map_align", "renderer", "camera_eye")
        center = self._config.get_ui_value("map_align", "renderer", "camera_center")
        up = self._config.get_ui_value("map_align", "renderer", "camera_up")
        self.camera_eye = np.array(eye, dtype=float)
        self.camera_center = np.array(center, dtype=float)
        self.camera_up = np.array(up, dtype=float)
        self.fov = self._config.get_ui_value("map_align", "renderer", "camera_fov")

        # Interaction state (camera only)
        self.last_mouse_pos = QPoint()
        self.is_rotating = False
        self.is_panning = False

        # Step sizes (defaults from config, overridden by controls panel)
        self.translate_step = self._config.get_ui_value(
            "map_align", "step_sizes", "translate_default"
        )
        self.rotate_step = self._config.get_ui_value(
            "map_align", "step_sizes", "rotate_default"
        )

        # Materials
        self._point_material = None
        self._mesh_material = None
        try:
            self._point_material = rendering.MaterialRecord()
            self._point_material.shader = "defaultUnlit"
            self._point_material.point_size = self._config.get_ui_value(
                "map_align", "renderer", "point_size"
            )

            self._mesh_material = rendering.MaterialRecord()
            self._mesh_material.shader = "defaultLit"
        except Exception as e:
            print(f"Warning: Failed to create material: {e}")
            self._renderer_failed = True

        # Color mode: True = legend colors (red/blue), False = original file colors
        self._use_legend_colors: bool = True

        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    # ─── Colors from config ───

    def _ref_color_rgb(self) -> list[float]:
        c = self._config.get_color("map_align", "reference")
        return [c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0]

    def _src_color_rgb(self) -> list[float]:
        c = self._config.get_color("map_align", "source")
        return [c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0]

    # ─── Renderer lifecycle ───

    def showEvent(self, event):
        super().showEvent(event)
        self._shown_once = True

        def create_renderer_delayed():
            if not self.renderer and not self._renderer_failed:
                w, h = self.width(), self.height()
                if w > 0 and h > 0:
                    self._create_renderer(w, h)

        QTimer.singleShot(200, create_renderer_delayed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._renderer_failed or not self._shown_once:
            return
        w, h = event.size().width(), event.size().height()
        if w > 0 and h > 0:
            self._create_renderer(w, h)

    def _create_renderer(self, w, h):
        try:
            if self.renderer is not None:
                try:
                    self.renderer.scene.clear_geometry()
                except Exception:
                    pass
                del self.renderer
                self.renderer = None

            self.renderer = rendering.OffscreenRenderer(w, h)
            bg_img = self._create_gradient_bg(w, h)
            self.renderer.scene.set_background([0.11, 0.137, 0.212, 1.0], bg_img)
            self.renderer.scene.scene.set_sun_light(
                [0.707, 0.0, -0.707], [1.0, 1.0, 1.0], 75000
            )
            self.renderer.scene.scene.enable_sun_light(True)

            self._rebuild_scene()
        except Exception as e:
            print(f"Warning: Alignment viewer renderer failed: {e}")
            self._renderer_failed = True
            self.renderer = None
            self.update()

    def _create_gradient_bg(self, w: int, h: int):
        """Create a vertical gradient background image for the 3D scene."""
        c_top = self._config.get_color("map_align", "background_top")
        c_bot = self._config.get_color("map_align", "background_bottom")
        top = np.array([c_top.red(), c_top.green(), c_top.blue()], dtype=np.float32)
        bot = np.array([c_bot.red(), c_bot.green(), c_bot.blue()], dtype=np.float32)
        t = np.linspace(0.0, 1.0, h).reshape(-1, 1, 1)
        gradient = (top * (1.0 - t) + bot * t)
        gradient = np.broadcast_to(gradient, (h, w, 3)).copy().astype(np.uint8)
        return o3d.geometry.Image(gradient)

    # ─── Scene management ───

    def _rebuild_scene(self):
        """Rebuild entire scene: grid, axes, reference, source."""
        if not self.renderer:
            return

        self.renderer.scene.clear_geometry()
        self._add_grid_to_scene()
        self._add_axes_to_scene()
        self._add_reference_to_scene()
        self._add_source_to_scene()
        self.render_scene()

    def _add_reference_to_scene(self):
        if not self.renderer:
            return
        self.renderer.scene.remove_geometry("reference")

        geom = self._state.reference_geom
        if geom is not None:
            self._add_geom_to_scene("reference", geom, self._ref_color_rgb())
            return

        # Fallback: point cloud only
        if self._state.reference_cloud is None:
            return
        if len(self._state.reference_cloud.points) == 0:
            return
        pcd = o3d.geometry.PointCloud(self._state.reference_cloud)
        if self._use_legend_colors or not pcd.has_colors():
            pcd.paint_uniform_color(self._ref_color_rgb())
        self.renderer.scene.add_geometry("reference", pcd, self._point_material)

    def _add_source_to_scene(self):
        if not self.renderer:
            return
        self.renderer.scene.remove_geometry("source")

        geom = self._state.get_transformed_source_geom()
        if geom is not None:
            self._add_geom_to_scene("source", geom, self._src_color_rgb())
            return

        # Fallback: point cloud only
        if self._state.source_cloud is None:
            return
        if len(self._state.source_cloud.points) == 0:
            return
        pts = self._state.get_transformed_source_points()
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pts)
        if self._use_legend_colors or not self._state.source_cloud.has_colors():
            pcd.paint_uniform_color(self._src_color_rgb())
        else:
            pcd.colors = self._state.source_cloud.colors
        self.renderer.scene.add_geometry("source", pcd, self._point_material)

    def _add_geom_to_scene(
        self,
        name: str,
        geom: o3d.geometry.TriangleMesh | o3d.geometry.PointCloud,
        legend_color: list[float],
    ) -> None:
        """Add a TriangleMesh or PointCloud to the scene with appropriate material."""
        if isinstance(geom, o3d.geometry.TriangleMesh):
            mesh = copy.deepcopy(geom)
            if self._use_legend_colors or not mesh.has_vertex_colors():
                mesh.paint_uniform_color(legend_color)
            self.renderer.scene.add_geometry(name, mesh, self._mesh_material)
        else:
            pcd = o3d.geometry.PointCloud(geom)
            if self._use_legend_colors or not pcd.has_colors():
                pcd.paint_uniform_color(legend_color)
            self.renderer.scene.add_geometry(name, pcd, self._point_material)

    def _add_axes_to_scene(self) -> None:
        """Add XYZ axes lines to the 3D scene."""
        if not self.renderer:
            return

        min_size = self._config.get_ui_value("map_align", "renderer", "axes_min_size")
        fallback_size = self._config.get_ui_value("map_align", "renderer", "axes_fallback_size")
        size = self._get_scene_extent() * 0.15
        if size < min_size:
            size = fallback_size

        points = [
            [0, 0, 0], [size, 0, 0],
            [0, 0, 0], [0, size, 0],
            [0, 0, 0], [0, 0, size],
        ]
        lines = [[0, 1], [2, 3], [4, 5]]
        colors = [[0.86, 0.2, 0.2], [0.2, 0.7, 0.2], [0.2, 0.2, 0.86]]

        axes = o3d.geometry.LineSet()
        axes.points = o3d.utility.Vector3dVector(points)
        axes.lines = o3d.utility.Vector2iVector(lines)
        axes.colors = o3d.utility.Vector3dVector(colors)

        self.renderer.scene.remove_geometry("axes")
        mat = rendering.MaterialRecord()
        mat.shader = "unlitLine"
        mat.line_width = self._config.get_ui_value(
            "map_align", "renderer", "axes_line_width"
        )
        self.renderer.scene.add_geometry("axes", axes, mat)

    def _add_grid_to_scene(self) -> None:
        """Add ground-plane grid lines to the 3D scene."""
        if not self.renderer:
            return

        min_extent = self._config.get_ui_value("map_align", "renderer", "grid_min_extent")
        fallback_extent = self._config.get_ui_value("map_align", "renderer", "grid_fallback_extent")
        extent = self._get_scene_extent()
        if extent < min_extent:
            extent = fallback_extent

        spacing = self._grid_spacing(extent)
        half = math.ceil(extent / spacing) * spacing

        points, lines = [], []
        for v in np.arange(-half, half + spacing * 0.5, spacing):
            i = len(points)
            points += [[v, -half, 0], [v, half, 0]]
            lines.append([i, i + 1])
            i = len(points)
            points += [[-half, v, 0], [half, v, 0]]
            lines.append([i, i + 1])

        if not points:
            return

        c = self._config.get_color("map_align", "grid_3d")
        grid_color = [c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0]
        ls = o3d.geometry.LineSet()
        ls.points = o3d.utility.Vector3dVector(points)
        ls.lines = o3d.utility.Vector2iVector(lines)
        ls.colors = o3d.utility.Vector3dVector([grid_color] * len(lines))

        self.renderer.scene.remove_geometry("grid")
        mat = rendering.MaterialRecord()
        mat.shader = "unlitLine"
        mat.line_width = self._config.get_ui_value(
            "map_align", "renderer", "grid_line_width"
        )
        self.renderer.scene.add_geometry("grid", ls, mat)

    def _get_points_from_geom(self, geom) -> np.ndarray | None:
        """Extract points from a TriangleMesh or PointCloud."""
        if geom is None:
            return None
        if isinstance(geom, o3d.geometry.TriangleMesh):
            verts = np.asarray(geom.vertices)
            return verts if len(verts) > 0 else None
        pts = np.asarray(geom.points)
        return pts if len(pts) > 0 else None

    def _get_scene_extent(self) -> float:
        """Get the max extent of all loaded geometry."""
        all_pts = []
        # Prefer display geometry, fall back to point clouds
        ref_pts = self._get_points_from_geom(self._state.reference_geom)
        if ref_pts is None and self._state.reference_cloud is not None and len(self._state.reference_cloud.points) > 0:
            ref_pts = np.asarray(self._state.reference_cloud.points)
        if ref_pts is not None:
            all_pts.append(ref_pts)

        src_geom = self._state.get_transformed_source_geom()
        if src_geom is not None:
            src_pts = self._get_points_from_geom(src_geom)
            if src_pts is not None:
                all_pts.append(src_pts)
        elif self._state.source_cloud is not None and len(self._state.source_cloud.points) > 0:
            all_pts.append(self._state.get_transformed_source_points())

        if not all_pts:
            return 10.0
        pts = np.vstack(all_pts)
        extent = pts.max(axis=0) - pts.min(axis=0)
        return float(max(extent))

    def _grid_spacing(self, extent: float) -> float:
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

    # ─── Public API (called by app.py) ───

    def set_use_legend_colors(self, enabled: bool) -> None:
        """Toggle between legend colors and original file colors."""
        self._use_legend_colors = enabled
        self._rebuild_scene()

    def update_reference(self) -> None:
        """Rebuild reference geometry and fit camera."""
        if not self.renderer:
            return
        self._add_reference_to_scene()
        self._fit_camera()
        self._add_grid_to_scene()
        self._add_axes_to_scene()
        self.render_scene()

    def update_source(self) -> None:
        """Rebuild source geometry with current transform."""
        if not self.renderer:
            return
        self._add_source_to_scene()
        self.render_scene()

    def _fit_camera(self) -> None:
        """Position camera to see all loaded geometry."""
        all_pts = []
        ref_pts = self._get_points_from_geom(self._state.reference_geom)
        if ref_pts is None and self._state.reference_cloud is not None and len(self._state.reference_cloud.points) > 0:
            ref_pts = np.asarray(self._state.reference_cloud.points)
        if ref_pts is not None:
            all_pts.append(ref_pts)

        src_geom = self._state.get_transformed_source_geom()
        if src_geom is not None:
            src_pts = self._get_points_from_geom(src_geom)
            if src_pts is not None:
                all_pts.append(src_pts)
        elif self._state.source_cloud is not None and len(self._state.source_cloud.points) > 0:
            all_pts.append(self._state.get_transformed_source_points())
        if not all_pts:
            return

        pts = np.vstack(all_pts)
        center = pts.mean(axis=0)
        extent = pts.max(axis=0) - pts.min(axis=0)
        max_ext = float(max(extent))

        coeff = self._config.get_ui_value("map_align", "renderer", "camera_fit_coefficient")
        self.camera_center = center.copy()
        self.camera_eye = center + np.array([0.0, -max_ext * coeff, max_ext * coeff])
        self.camera_up = np.array([0.0, 0.0, 1.0])

    # ─── Rendering ───

    def render_scene(self):
        if not self.renderer:
            return
        try:
            self.renderer.setup_camera(
                self.fov, self.camera_center, self.camera_eye, self.camera_up
            )
            img_np = np.asarray(self.renderer.render_to_image())
            self._image_data = np.copy(img_np)
            h, w, _ = self._image_data.shape
            q_image = QImage(
                self._image_data.data, w, h, 3 * w, QImage.Format.Format_RGB888
            )
            self.image = q_image.copy()
            self.update()
        except Exception as e:
            print(f"Warning: render_scene failed: {e}")

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(30, 30, 30))

            if self._renderer_failed:
                painter.setPen(QColor(200, 0, 0))
                font = QFont()
                font.setPointSize(12)
                painter.setFont(font)
                painter.drawText(
                    self.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    "3D Viewer Disabled\n\n"
                    "Open3D OffscreenRenderer failed to initialize.\n"
                    "This is likely due to missing OpenGL support.",
                )
            elif self.image:
                painter.drawImage(0, 0, self.image)
            else:
                painter.setPen(QColor(180, 180, 180))
                painter.drawText(
                    self.rect(), Qt.AlignmentFlag.AlignCenter, "No Data / Loading..."
                )
        except Exception as e:
            print(f"Warning: paintEvent failed: {e}")

    # ─── Mouse interaction (camera only) ───

    def mousePressEvent(self, event) -> None:
        """Start orbit (left-click) or pan (middle-click) camera interaction."""
        self.last_mouse_pos = event.pos()
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_rotating = True
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = True

    def mouseReleaseEvent(self, event) -> None:
        """End camera orbit/pan interaction."""
        self.is_panning = False
        self.is_rotating = False

    def mouseMoveEvent(self, event) -> None:
        """Handle camera orbit or pan based on active interaction mode."""
        dx = event.pos().x() - self.last_mouse_pos.x()
        dy = event.pos().y() - self.last_mouse_pos.y()
        self.last_mouse_pos = event.pos()

        if self.is_rotating:
            self.orbit_camera(dx, dy)
        elif self.is_panning:
            self.pan_camera(dx, dy)

    def wheelEvent(self, event) -> None:
        """Handle scroll: zoom (plain), yaw (Shift), translate Z (Ctrl)."""
        mods = event.modifiers()
        delta = event.angleDelta().y()
        sign = 1.0 if delta > 0 else -1.0

        if mods & Qt.KeyboardModifier.ShiftModifier:
            # Shift+Scroll: rotate yaw
            self._state.yaw_deg += sign * self.rotate_step
            self._emit_transform()
        elif mods & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+Scroll: translate Z
            self._state.tz += sign * self.translate_step
            self._emit_transform()
        else:
            self.zoom_camera(delta)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts for transform and camera control."""
        key = event.key()
        mods = event.modifiers()
        step = self.translate_step
        rot = self.rotate_step

        moved = False

        # Translation
        if key == Qt.Key.Key_Left:
            self._state.tx -= step
            moved = True
        elif key == Qt.Key.Key_Right:
            self._state.tx += step
            moved = True
        elif key == Qt.Key.Key_Up:
            self._state.ty += step
            moved = True
        elif key == Qt.Key.Key_Down:
            self._state.ty -= step
            moved = True
        elif key == Qt.Key.Key_PageUp:
            self._state.tz += step
            moved = True
        elif key == Qt.Key.Key_PageDown:
            self._state.tz -= step
            moved = True

        # Rotation
        elif key == Qt.Key.Key_BracketLeft:
            if mods & Qt.KeyboardModifier.ShiftModifier:
                self._state.roll_deg -= rot
            elif mods & Qt.KeyboardModifier.ControlModifier:
                self._state.pitch_deg -= rot
            else:
                self._state.yaw_deg -= rot
            moved = True
        elif key == Qt.Key.Key_BracketRight:
            if mods & Qt.KeyboardModifier.ShiftModifier:
                self._state.roll_deg += rot
            elif mods & Qt.KeyboardModifier.ControlModifier:
                self._state.pitch_deg += rot
            else:
                self._state.yaw_deg += rot
            moved = True

        # Auto Align
        elif key == Qt.Key.Key_R:
            self.registration_requested.emit()
            return
        elif key == Qt.Key.Key_F:
            self._fit_camera()
            self._rebuild_scene()
            return

        if moved:
            self._emit_transform()

    def _emit_transform(self):
        """Update source geometry and notify listeners."""
        self.update_source()
        self.transform_changed.emit()
