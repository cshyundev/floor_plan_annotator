"""Map Alignment Tool — Main application window (QDialog dual-mode)."""

import os

import numpy as np
import open3d as o3d
from PyQt6.QtWidgets import (
    QDialog, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QFileDialog, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt

from src.core.config import ConfigManager
from src.map_align.alignment_state import AlignmentState
from src.map_align.map_unifier import load_as_pointcloud, load_as_geometry
from src.map_align.registration import PointToPointICP
from src.map_align.annotation_saver import save_aligned_annotations
from src.map_align.widgets.topdown_view import TopDownView
from src.map_align.widgets.controls_panel import ControlsPanel


# Supported file filters
_3D_FILTER = "3D Data (*.ply *.pcd *.obj *.stl *.glb *.gltf)"
_MAP_FILTER = "Occupancy Grid (*.yaml *.yml)"
_ALL_FILTER = "All Supported (*.ply *.pcd *.obj *.stl *.glb *.gltf *.yaml *.yml)"


class AlignmentWindow(QDialog):
    """Map alignment dialog — standalone or embedded in main app.

    Standalone mode (source_path=None):
        Both "Load Reference" and "Load Source" buttons visible.
        "Save Annotations" button for output.

    Embedded mode (source_path provided):
        Source data injected from main app. "Load Source" hidden.
        "Apply" + "Cancel" buttons replace "Save Annotations".
        On Apply: saves annotations → self.accept().
        On Cancel: self.reject().
    """

    def __init__(
        self,
        source_path: str | None = None,
        source_cloud: o3d.geometry.PointCloud | None = None,
        source_geom: o3d.geometry.TriangleMesh | o3d.geometry.PointCloud | None = None,
        source_bounds: tuple[list, list] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Map Alignment Tool")
        self.resize(1200, 800)

        self._embedded = source_path is not None
        self._result_path: str | None = None
        self._source_bounds_override = source_bounds

        self._config = ConfigManager.instance()
        self._state = AlignmentState()
        self._last_dir = os.path.expanduser("~")

        # Full-resolution clouds for registration (not downsampled)
        self._ref_full: o3d.geometry.PointCloud | None = None
        self._src_full: o3d.geometry.PointCloud | None = None

        self._algorithm = PointToPointICP(
            max_correspondence_distance=self._config.get_ui_value(
                "map_align", "icp", "max_correspondence_distance"
            ),
            max_iteration=self._config.get_ui_value(
                "map_align", "icp", "max_iterations"
            ),
        )

        self._build_ui()
        self._connect_signals()

        if self._embedded:
            self._init_embedded_source(source_path, source_cloud, source_geom)
        else:
            self._auto_load_test_data()

    def result_path(self) -> str | None:
        """Return saved annotations.json path after Apply, or None."""
        return self._result_path

    # ─── Embedded source initialisation ───

    def _init_embedded_source(
        self,
        source_path: str,
        source_cloud: o3d.geometry.PointCloud | None,
        source_geom: o3d.geometry.TriangleMesh | o3d.geometry.PointCloud | None,
    ) -> None:
        """Load source data from main app into alignment state."""
        self._state.source_path = source_path

        if source_cloud is not None:
            self._src_full = source_cloud
            voxel_size = self._config.get_ui_value(
                "map_align", "display", "voxel_size",
            )
            self._state.source_cloud = source_cloud.voxel_down_sample(voxel_size)
        else:
            # Fallback: load from file
            self._src_full, display_cloud, src_geom = self._load_map(source_path)
            self._state.source_cloud = display_cloud
            source_geom = src_geom

        if source_geom is not None:
            self._state.source_geom = source_geom
        self._state.reset_transform()
        self._view.update_source()
        self._update_button_states()
        self._set_status(f"Source loaded: {os.path.basename(source_path)}")

    # ─── UI construction ───

    def _build_ui(self) -> None:
        """Build the dialog layout: button bar + content + status label."""
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Button bar (replaces QToolBar)
        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(0, 0, 0, 0)

        self._btn_load_ref = QPushButton("Load Reference")
        self._btn_load_ref.clicked.connect(self._load_reference)
        btn_bar.addWidget(self._btn_load_ref)

        self._btn_load_src = QPushButton("Load Source")
        self._btn_load_src.clicked.connect(self._load_source)
        btn_bar.addWidget(self._btn_load_src)
        if self._embedded:
            self._btn_load_src.setVisible(False)

        btn_bar.addSpacing(16)

        self._btn_register = QPushButton("Auto Align")
        self._btn_register.setEnabled(False)
        self._btn_register.clicked.connect(self._run_registration)
        btn_bar.addWidget(self._btn_register)

        if self._embedded:
            self._btn_apply = QPushButton("Apply")
            self._btn_apply.setEnabled(False)
            self._btn_apply.clicked.connect(self._apply_and_accept)
            btn_bar.addWidget(self._btn_apply)
        else:
            self._btn_save = QPushButton("Save Annotations")
            self._btn_save.setEnabled(False)
            self._btn_save.clicked.connect(self._save_transform)
            btn_bar.addWidget(self._btn_save)

        btn_bar.addSpacing(16)

        self._btn_reset = QPushButton("Reset")
        self._btn_reset.clicked.connect(self._reset_transform)
        btn_bar.addWidget(self._btn_reset)

        if self._embedded:
            self._btn_cancel = QPushButton("Cancel")
            self._btn_cancel.clicked.connect(self.reject)
            btn_bar.addWidget(self._btn_cancel)

        btn_bar.addStretch()
        root.addLayout(btn_bar)

        # Content: TopDownView + ControlsPanel
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        self._view = TopDownView(self._state)
        self._controls = ControlsPanel()
        content.addWidget(self._view, stretch=1)
        content.addWidget(self._controls, stretch=0)
        root.addLayout(content, stretch=1)

        # Status label (replaces QStatusBar)
        self._status_label = QLabel()
        root.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        """Wire up signals between controls, view, and state."""
        self._controls.transform_changed.connect(self._on_controls_transform_changed)
        self._view.transform_changed.connect(self._on_viewer_transform_changed)
        self._view.registration_requested.connect(self._run_registration)
        self._controls.color_mode_changed.connect(self._on_color_mode_changed)

    def _on_color_mode_changed(self, use_legend: bool) -> None:
        """Toggle legend coloring on the top-down view."""
        self._view.set_use_legend_colors(use_legend)

    # ─── Status helpers ───

    def _set_status(self, msg: str) -> None:
        """Display a message in the status label."""
        self._status_label.setText(msg)

    def _update_status(self) -> None:
        """Show current transform + ICP metrics in the status label."""
        s = self._state
        self._set_status(
            f"tx={s.tx:.3f}  ty={s.ty:.3f}  tz={s.tz:.3f}"
            f"  R={s.roll_deg:.1f}°  P={s.pitch_deg:.1f}°  Y={s.yaw_deg:.1f}°"
            f"  |  ICP fitness={s.icp_fitness:.4f}  RMSE={s.icp_rmse:.4f}"
        )

    # ─── Auto-load test data (standalone only) ───

    def _auto_load_test_data(self) -> None:
        """Auto-load test data for development convenience."""
        test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        ref_path = os.path.join(test_dir, "mesh_ref.ply")
        src_path = os.path.join(test_dir, "mesh_src.ply")

        if not (os.path.isfile(ref_path) and os.path.isfile(src_path)):
            return

        try:
            self._ref_full, display_ref, ref_geom = self._load_map(ref_path)
            self._state.reference_cloud = display_ref
            self._state.reference_geom = ref_geom
            self._state.reference_path = ref_path
            self._view.update_reference()

            self._src_full, display_src, src_geom = self._load_map(src_path)
            self._state.source_cloud = display_src
            self._state.source_geom = src_geom
            self._state.source_path = src_path
            self._state.reset_transform()
            self._view.update_source()

            self._update_button_states()
            self._set_status("Test data loaded (cloud_c → ref, mesh_d → src)")
        except Exception as e:
            self._set_status(f"Auto-load failed: {e}")

    # ─── File loading ───

    def _load_map(self, path: str) -> tuple:
        """Load a map file, returning (full_cloud, display_cloud, display_geom).

        full_cloud: PointCloud for ICP registration (no downsampling).
        display_cloud: PointCloud for fallback display (voxel downsampled).
        display_geom: native geometry (TriangleMesh or PointCloud) for rendering.
        """
        voxel_size = self._config.get_ui_value("map_align", "display", "voxel_size")
        wall_height = self._config.get_ui_value(
            "map_align", "occupancy_grid", "wall_height",
        )

        full = load_as_pointcloud(path, wall_height=wall_height)
        display = load_as_pointcloud(
            path, voxel_size=voxel_size, wall_height=wall_height,
        )
        display_geom = load_as_geometry(path, wall_height=wall_height)
        return full, display, display_geom

    def _load_reference(self) -> None:
        """Open file dialog to load the reference map."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Reference Map", self._last_dir,
            f"{_ALL_FILTER};;{_3D_FILTER};;{_MAP_FILTER}",
        )
        if not path:
            return

        self._last_dir = os.path.dirname(path)
        try:
            self._ref_full, display_cloud, ref_geom = self._load_map(path)
            self._state.reference_cloud = display_cloud
            self._state.reference_geom = ref_geom
            self._state.reference_path = path
            self._view.update_reference()
            self._update_button_states()
            self._set_status(f"Reference loaded: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.warning(
                self, "Load Error", f"Failed to load reference:\n{e}",
            )

    def _load_source(self) -> None:
        """Open file dialog to load the source map (standalone mode only)."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Source Map", self._last_dir,
            f"{_ALL_FILTER};;{_3D_FILTER};;{_MAP_FILTER}",
        )
        if not path:
            return

        self._last_dir = os.path.dirname(path)
        try:
            self._src_full, display_cloud, src_geom = self._load_map(path)
            self._state.source_cloud = display_cloud
            self._state.source_geom = src_geom
            self._state.source_path = path
            self._state.reset_transform()
            self._sync_controls_from_state()
            self._view.update_source()
            self._view.update_reference()  # Refit view
            self._update_button_states()
            self._set_status(f"Source loaded: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.warning(
                self, "Load Error", f"Failed to load source:\n{e}",
            )

    # ─── Registration ───

    def _run_registration(self) -> None:
        """Run ICP registration between source and reference clouds."""
        if self._ref_full is None or self._src_full is None:
            return

        self._set_status("Running registration...")
        try:
            result = self._algorithm.run(
                source=self._src_full,
                target=self._ref_full,
                initial_transform=self._state.get_transform_4x4(),
            )

            self._state.set_from_4x4(result.transform)
            self._state.icp_fitness = result.fitness
            self._state.icp_rmse = result.inlier_rmse

            self._sync_controls_from_state()
            self._view.update_source()
            self._update_status()
            self._update_button_states()
            self._set_status(
                f"Registration done — fitness: {result.fitness:.4f}, "
                f"RMSE: {result.inlier_rmse:.4f}",
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Registration Error", f"Registration failed:\n{e}",
            )

    # ─── Save / Apply ───

    def _compute_source_bounds(self) -> tuple[list, list] | None:
        """Compute source cloud bounds, preferring the override from main app."""
        if self._source_bounds_override is not None:
            return self._source_bounds_override
        if self._src_full is not None:
            pts = np.asarray(self._src_full.points)
            if len(pts) > 0:
                return (pts.min(axis=0).tolist(), pts.max(axis=0).tolist())
        return None

    def _compute_reference_bounds(self) -> tuple[list, list] | None:
        """Compute reference cloud bounds."""
        if self._ref_full is not None:
            pts = np.asarray(self._ref_full.points)
            if len(pts) > 0:
                return (pts.min(axis=0).tolist(), pts.max(axis=0).tolist())
        return None

    def _do_save(self) -> str | None:
        """Run save_aligned_annotations with overwrite confirmation.

        Returns the output path on success, or None if cancelled/failed.
        """
        source_dir = os.path.dirname(os.path.abspath(self._state.source_path))
        output_path = os.path.join(source_dir, "annotations.json")

        if os.path.isfile(output_path):
            reply = QMessageBox.question(
                self,
                "Overwrite",
                f"annotations.json already exists in:\n{source_dir}\n\nOverwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return None

        try:
            path = save_aligned_annotations(
                source_path=self._state.source_path,
                reference_path=self._state.reference_path,
                tf_src_to_ref=self._state.get_transform_4x4(),
                icp_fitness=self._state.icp_fitness,
                icp_rmse=self._state.icp_rmse,
                source_bounds=self._compute_source_bounds(),
                reference_bounds=self._compute_reference_bounds(),
            )
            return path
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save:\n{e}")
            return None

    def _save_transform(self) -> None:
        """Save annotations (standalone mode)."""
        path = self._do_save()
        if path:
            self._set_status(f"Saved: {path}")

    def _apply_and_accept(self) -> None:
        """Save annotations and close dialog with Accepted (embedded mode)."""
        path = self._do_save()
        if path:
            self._result_path = path
            self.accept()

    # ─── Reset ───

    def _reset_transform(self) -> None:
        """Reset transform to identity."""
        self._state.reset_transform()
        self._sync_controls_from_state()
        self._view.update_source()
        self._update_status()

    # ─── Controls ↔ State sync ───

    def _on_controls_transform_changed(self) -> None:
        """Controls panel spinbox changed → update state → update viewer."""
        vals = self._controls.get_transform_values()
        self._state.tx = vals["tx"]
        self._state.ty = vals["ty"]
        self._state.tz = vals["tz"]
        self._state.roll_deg = vals["roll_deg"]
        self._state.pitch_deg = vals["pitch_deg"]
        self._state.yaw_deg = vals["yaw_deg"]
        self._view.update_source()
        self._update_status()

    def _on_viewer_transform_changed(self) -> None:
        """Viewer shortcut changed state → sync controls panel."""
        self._sync_controls_from_state()
        self._update_status()

    def _sync_controls_from_state(self) -> None:
        """Push current state values into control panel spinboxes."""
        self._controls.set_transform_values(
            tx=self._state.tx,
            ty=self._state.ty,
            tz=self._state.tz,
            roll_deg=self._state.roll_deg,
            pitch_deg=self._state.pitch_deg,
            yaw_deg=self._state.yaw_deg,
        )

    # ─── UI updates ───

    def _update_button_states(self) -> None:
        """Enable/disable buttons based on loaded state."""
        both_loaded = (
            self._state.reference_cloud is not None
            and self._state.source_cloud is not None
        )
        self._btn_register.setEnabled(both_loaded)
        if self._embedded:
            self._btn_apply.setEnabled(both_loaded)
        else:
            self._btn_save.setEnabled(both_loaded)
