"""Map Alignment Tool — Main application window."""

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QToolBar,
    QFileDialog, QStatusBar, QMessageBox,
)
from PyQt6.QtGui import QAction
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


class AlignmentWindow(QMainWindow):
    """Main window for the map alignment tool."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Alignment Tool")
        self.resize(1200, 800)

        self._config = ConfigManager.instance()
        self._state = AlignmentState()
        self._last_dir = os.path.expanduser("~")

        # Full-resolution clouds for registration (not downsampled)
        self._ref_full = None
        self._src_full = None

        self._algorithm = PointToPointICP(
            max_correspondence_distance=self._config.get_ui_value(
                "map_align", "icp", "max_correspondence_distance"
            ),
            max_iteration=self._config.get_ui_value(
                "map_align", "icp", "max_iterations"
            ),
        )

        self._build_ui()
        self._build_toolbar()
        self._build_statusbar()
        self._connect_signals()
        self._auto_load_test_data()

    def _auto_load_test_data(self):
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
            self._statusbar.showMessage("Test data loaded (cloud_c → ref, mesh_d → src)", 3000)
        except Exception as e:
            self._statusbar.showMessage(f"Auto-load failed: {e}", 5000)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self._view = TopDownView(self._state)
        self._controls = ControlsPanel()

        layout.addWidget(self._view, stretch=1)
        layout.addWidget(self._controls, stretch=0)

    def _build_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._act_load_ref = QAction("Load Reference", self)
        self._act_load_ref.triggered.connect(self._load_reference)
        toolbar.addAction(self._act_load_ref)

        self._act_load_src = QAction("Load Source", self)
        self._act_load_src.triggered.connect(self._load_source)
        toolbar.addAction(self._act_load_src)

        toolbar.addSeparator()

        self._act_register = QAction("Auto Align", self)
        self._act_register.triggered.connect(self._run_registration)
        self._act_register.setEnabled(False)

        self._act_save = QAction("Save Annotations", self)
        self._act_save.triggered.connect(self._save_transform)
        self._act_save.setEnabled(False)
        toolbar.addAction(self._act_save)

        toolbar.addSeparator()

        self._act_reset = QAction("Reset", self)
        self._act_reset.triggered.connect(self._reset_transform)
        toolbar.addAction(self._act_reset)

    def _build_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._update_status()

    def _connect_signals(self):
        self._controls.transform_changed.connect(self._on_controls_transform_changed)
        self._view.transform_changed.connect(self._on_viewer_transform_changed)
        self._view.registration_requested.connect(self._run_registration)
        self._controls.color_mode_changed.connect(self._on_color_mode_changed)

    def _on_color_mode_changed(self, use_legend: bool):
        self._view.set_use_legend_colors(use_legend)

    # ─── File loading ───

    def _load_map(self, path: str) -> tuple:
        """Load a map file, returning (full_cloud, display_cloud, display_geom).

        full_cloud: PointCloud for ICP registration (no downsampling).
        display_cloud: PointCloud for fallback display (voxel downsampled).
        display_geom: native geometry (TriangleMesh or PointCloud) for rendering.
        """
        voxel_size = self._config.get_ui_value("map_align", "display", "voxel_size")
        wall_height = self._config.get_ui_value("map_align", "occupancy_grid", "wall_height")

        full = load_as_pointcloud(path, wall_height=wall_height)
        display = load_as_pointcloud(path, voxel_size=voxel_size, wall_height=wall_height)
        display_geom = load_as_geometry(path, wall_height=wall_height)
        return full, display, display_geom

    def _load_reference(self):
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
            self._statusbar.showMessage(f"Reference loaded: {os.path.basename(path)}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load reference:\n{e}")

    def _load_source(self):
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
            self._statusbar.showMessage(f"Source loaded: {os.path.basename(path)}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load source:\n{e}")

    # ─── Registration ───

    def _run_registration(self):
        if self._ref_full is None or self._src_full is None:
            return

        self._statusbar.showMessage("Running registration...")
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
            self._act_save.setEnabled(True)
            self._statusbar.showMessage(
                f"Registration done — fitness: {result.fitness:.4f}, RMSE: {result.inlier_rmse:.4f}",
                5000,
            )
        except Exception as e:
            QMessageBox.warning(self, "Registration Error", f"Registration failed:\n{e}")

    # ─── Save ───

    def _save_transform(self):
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
                return

        try:
            import numpy as np

            # Compute cloud bounds for coordinate convention conversion
            source_bounds = None
            if self._src_full is not None:
                pts = np.asarray(self._src_full.points)
                if len(pts) > 0:
                    source_bounds = (pts.min(axis=0).tolist(), pts.max(axis=0).tolist())

            reference_bounds = None
            if self._ref_full is not None:
                pts = np.asarray(self._ref_full.points)
                if len(pts) > 0:
                    reference_bounds = (pts.min(axis=0).tolist(), pts.max(axis=0).tolist())

            save_aligned_annotations(
                source_path=self._state.source_path,
                reference_path=self._state.reference_path,
                tf_src_to_ref=self._state.get_transform_4x4(),
                icp_fitness=self._state.icp_fitness,
                icp_rmse=self._state.icp_rmse,
                source_bounds=source_bounds,
                reference_bounds=reference_bounds,
            )
            self._statusbar.showMessage(f"Saved: {output_path}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save:\n{e}")

    # ─── Reset ───

    def _reset_transform(self):
        self._state.reset_transform()
        self._sync_controls_from_state()
        self._view.update_source()
        self._update_status()

    # ─── Controls ↔ State sync ───

    def _on_controls_transform_changed(self):
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

    def _on_viewer_transform_changed(self):
        """Viewer shortcut changed state → sync controls panel."""
        self._sync_controls_from_state()
        self._update_status()

    def _sync_controls_from_state(self):
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

    def _update_status(self):
        s = self._state
        self._statusbar.showMessage(
            f"tx={s.tx:.3f}  ty={s.ty:.3f}  tz={s.tz:.3f}"
            f"  R={s.roll_deg:.1f}°  P={s.pitch_deg:.1f}°  Y={s.yaw_deg:.1f}°"
            f"  |  ICP fitness={s.icp_fitness:.4f}  RMSE={s.icp_rmse:.4f}"
        )

    def _update_button_states(self):
        both_loaded = (
            self._state.reference_cloud is not None
            and self._state.source_cloud is not None
        )
        self._act_register.setEnabled(both_loaded)
        self._act_save.setEnabled(both_loaded)
