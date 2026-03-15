from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QFileDialog, QSlider, QLabel, QDockWidget,
                             QToolBar, QStatusBar, QCheckBox, QComboBox, QPushButton,
                             QScrollArea, QMessageBox)
from PyQt6.QtGui import QAction, QActionGroup, QUndoStack
from PyQt6.QtCore import Qt
from src.gui.canvas_2d import Canvas2D
from src.gui.collapsible_section import CollapsibleSection
from src.gui.properties_panel import PropertiesPanel
from src.core.processor import SliceEngine
from src.core.map_loader import MapLoader
from src.core.map_mesh_generator import MapMeshGenerator
from src.model.data import MapMetadata
import numpy as np
import os

from src.core.config import ConfigManager
from src.core.coordinate_system import CoordinateSystem
from src.gui.coordinate_system_widget import CoordinateSystemWidget
from src.gui.recent_files_manager import RecentFilesManager
from src.gui.autosave_manager import AutosaveManager

# Try to import Viewer3D - let it fail naturally if Open3D doesn't work
# The Viewer3D class itself handles failures gracefully
try:
    from src.gui.viewer_3d import Viewer3D
    VIEWER3D_AVAILABLE = True
except Exception as e:
    print(f"Warning: Viewer3D import failed: {e}")
    print("Using stub implementation")
    from src.gui.viewer_3d_stub import Viewer3DStub as Viewer3D
    VIEWER3D_AVAILABLE = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        config = ConfigManager.instance()
        self.setWindowTitle(config.get_string("window", "title"))
        self.resize(
            config.get_ui_value("window", "width"),
            config.get_ui_value("window", "height")
        )

        # Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Splitter for 3D and 2D views
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # 3D Viewer (real implementation or stub if Open3D not available)
        self.viewer_3d = Viewer3D()
        self.splitter.addWidget(self.viewer_3d)

        # 2D Viewer
        self.canvas_2d = Canvas2D()
        self.splitter.addWidget(self.canvas_2d)

        # Set initial sizes
        self.splitter.setSizes([
            config.get_ui_value("window", "splitter_left"),
            config.get_ui_value("window", "splitter_right")
        ])

        # Helper
        self.undo_stack = QUndoStack(self)
        self.canvas_2d.set_undo_stack(self.undo_stack)

        # Type editor dialog (lazy-created)
        self._type_editor_dialog = None

        # Occupancy grid state
        self._map_metadata = None  # type: MapMetadata | None
        self._map_image_data = None  # type: np.ndarray | None

        # All-points projection cache (invalidated on data load / coord sys change)
        self._all_points_cache = None  # (img, bounds, scale) or None

        # Project lifecycle state (FEAT-006)
        self._current_file_path = None  # type: str | None  — annotations.json save path
        self._3d_file_path = None       # type: str | None  — currently loaded 3D data absolute path
        self._created_at = None         # type: str | None  — ISO 8601, preserved across saves

        # Recent files (FEAT-007)
        self._recent_mgr = RecentFilesManager(self)
        self._recent_mgr.file_selected.connect(self._open_recent_file)

        # Controls (Dock)
        self.create_controls()

        # Data
        self.processor = SliceEngine()
        self.current_z = 0.0

        # Annotation synchronization (2D to 3D)
        from src.core.annotation_sync import AnnotationSync3D
        self.annotation_sync = AnnotationSync3D(
            self.viewer_3d,
            self.processor,
            ConfigManager.instance()
        )

        # Re-sync annotations once the 3D renderer is ready (it is created asynchronously
        # via a 200ms timer in Viewer3D.showEvent, so annotations added before that point
        # are silently dropped by add_*_geometry()).
        self.viewer_3d.on_renderer_ready = lambda: \
            self.annotation_sync.update_all_annotations(self.canvas_2d.scene)

        # Connect undo stack changes to sync + properties refresh
        self.undo_stack.indexChanged.connect(self.on_undo_stack_changed)
        self.undo_stack.indexChanged.connect(
            lambda: self.properties_panel._on_selection_changed()
        )
        # Dirty state tracking (FEAT-006)
        self.undo_stack.cleanChanged.connect(self._on_dirty_changed)

        # Menu Bar
        self.create_menu()

        # Auto-save (FEAT-009)
        self._autosave_mgr = AutosaveManager(
            self,
            get_save_data=self._get_autosave_data,
            get_file_path=lambda: self._current_file_path,
            is_dirty=lambda: not self.undo_stack.isClean(),
        )

    # ── Lifecycle helpers (FEAT-006) ────────────────────────────────────────

    def _on_dirty_changed(self, clean: bool) -> None:
        self._update_title_bar()

    def _update_title_bar(self) -> None:
        dirty = not self.undo_stack.isClean()
        if self._current_file_path:
            name = os.path.basename(self._current_file_path)
        elif self._3d_file_path:
            name = os.path.basename(self._3d_file_path)
        else:
            name = None
        title = "Floor Plan Annotator"
        if name:
            title += f" \u2014 {name}"
        if dirty:
            title += " *"
        self.setWindowTitle(title)

    def _confirm_discard_changes(self) -> bool:
        """If there are unsaved changes, prompt Save / Discard / Cancel.

        Returns True if it is safe to proceed (saved or discarded), False if cancelled.
        """
        if self.undo_stack.isClean():
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "저장하지 않은 변경사항이 있습니다. 저장할까요?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self.save_project()
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        else:
            return False

    def create_menu(self):
        config = ConfigManager.instance()
        menubar = self.menuBar()
        file_menu = menubar.addMenu(config.get_string("menu", "file"))

        load_action = QAction(config.get_string("menu", "load_point_cloud"), self)
        load_action.triggered.connect(self.load_point_cloud)
        file_menu.addAction(load_action)

        load_occ_action = QAction(config.get_string("menu", "load_occupancy_grid"), self)
        load_occ_action.triggered.connect(self.load_occupancy_grid)
        file_menu.addAction(load_occ_action)

        recent_menu = file_menu.addMenu("Recent Files")
        self._recent_mgr.set_menu(recent_menu)

        file_menu.addSeparator()

        save_proj_action = QAction(config.get_string("menu", "save_project"), self)
        save_proj_action.setShortcut(config.get_shortcut("file", "save_project") or "Ctrl+S")
        save_proj_action.triggered.connect(self.save_project)
        file_menu.addAction(save_proj_action)

        save_as_action = QAction(config.get_string("menu", "save_project_as"), self)
        save_as_action.setShortcut(config.get_shortcut("file", "save_project_as") or "Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction(config.get_string("menu", "exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        self._act_import_align = QAction("Import Annotations from Map...", self)
        self._act_import_align.setEnabled(False)
        self._act_import_align.triggered.connect(self._open_alignment_dialog)
        tools_menu.addAction(self._act_import_align)

        tools_menu.addSeparator()

        manage_types_action = QAction("Manage Types...", self)
        manage_types_action.triggered.connect(self._open_type_editor)
        tools_menu.addAction(manage_types_action)

        tools_menu.addSeparator()

        prefs_action = QAction("Preferences...", self)
        prefs_action.triggered.connect(self._open_preferences)
        tools_menu.addAction(prefs_action)

    # ── Recent Files (FEAT-007) — delegated to RecentFilesManager ────────

    def _open_recent_file(self, path: str) -> None:
        if not os.path.exists(path):
            self._recent_mgr.remove(path)
            self.statusBar().showMessage(
                f"File not found: {os.path.basename(path)}", 4000
            )
            return
        if not self._confirm_discard_changes():
            return
        self.load_data(path)

    def _load_project_file(self, path: str) -> None:
        from src.core.io import ProjectIO
        try:
            proj = ProjectIO.load_project(path)
        except Exception as e:
            QMessageBox.critical(self, "Open Error", str(e))
            return
        self._current_file_path = path
        self.undo_stack.clear()
        self.canvas_2d.background_item = None
        self.canvas_2d.load_from_data(proj)
        if proj.coordinate_system:
            cs = proj.coordinate_system
            self.coord_sys_widget.set_coordinate_system(cs)
            self._apply_coordinate_system(cs)
        if proj.map_metadata:
            self._restore_data_source(proj.map_metadata, path)
        elif self.processor._points is not None:
            self._update_2d_slice()
        self.undo_stack.setClean()
        self.annotation_sync.update_all_annotations(self.canvas_2d.scene)
        self._update_title_bar()

    # ── End Recent Files ───────────────────────────────────────────────────

    # ── Auto-save (FEAT-009) — delegated to AutosaveManager ───────────────

    def _get_autosave_data(self):
        """Build project data for autosave."""
        from datetime import datetime, timezone
        project_data = self.canvas_2d.save_to_data()
        project_data.coordinate_system = self.coord_sys_widget.current_coordinate_system()
        if self._map_metadata is not None:
            project_data.map_metadata = self._map_metadata
        if not self._created_at:
            self._created_at = datetime.now(timezone.utc).isoformat()
        project_data.created_at = self._created_at
        project_data.modified_at = datetime.now(timezone.utc).isoformat()
        return project_data

    def _open_preferences(self) -> None:
        from src.gui.preferences_dialog import PreferencesDialog
        dlg = PreferencesDialog(self)
        if dlg.exec():
            dlg.save_settings()
            self._autosave_mgr.load_settings()

    # ── End Auto-save ──────────────────────────────────────────────────────

    def _do_save(self, path: str) -> bool:
        """Write annotations to *path*. Sets _current_file_path and marks stack clean.

        Returns True on success, False on error.
        """
        from src.core.io import ProjectIO
        from datetime import datetime, timezone
        try:
            project_data = self.canvas_2d.save_to_data()
            project_data.coordinate_system = self.coord_sys_widget.current_coordinate_system()

            # data_type
            if self._map_image_data is not None:
                project_data.data_type = "occupancy_grid"
            elif self._3d_file_path:
                ext = os.path.splitext(self._3d_file_path)[1].lower()
                project_data.data_type = "mesh" if ext in ('.glb', '.gltf') else "point_cloud"
            else:
                project_data.data_type = "point_cloud"

            # timestamps
            if not self._created_at:
                self._created_at = datetime.now(timezone.utc).isoformat()
            project_data.created_at = self._created_at
            project_data.modified_at = datetime.now(timezone.utc).isoformat()

            # source (map_metadata)
            if self._map_metadata is not None:
                self._map_metadata.image_path = MapLoader.make_relative_path(
                    self._map_metadata.image_path_absolute, path
                )
                project_data.map_metadata = self._map_metadata
            ProjectIO.save_project(project_data, path)
            self._current_file_path = path
            self.undo_stack.setClean()
            self._update_title_bar()
            if self._3d_file_path:
                self._recent_mgr.add(self._3d_file_path)
            self._autosave_mgr.delete_autosave()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            return False

    def save_project(self) -> bool:
        """Save to the current annotations path, deriving it automatically if needed."""
        if self._current_file_path:
            return self._do_save(self._current_file_path)
        if self._3d_file_path:
            folder = os.path.dirname(self._3d_file_path)
            path = os.path.join(folder, "annotations.json")
            return self._do_save(path)
        return self.save_project_as()

    def save_project_as(self) -> bool:
        """Always open a file dialog to choose the save path."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Annotations As", "", "JSON Files (*.json)"
        )
        if path:
            return self._do_save(path)
        return False

    def closeEvent(self, event) -> None:
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def _detect_annotations_for_3d_file(self, data_file_path: str) -> None:
        """Auto-detect and load annotations.json in the same folder as *data_file_path*.

        Skipped when _current_file_path is already set.
        Validates pairing by comparing the stored image_path basename with the loaded file.
        """
        if self._current_file_path is not None:
            return
        folder = os.path.dirname(data_file_path)
        candidate = os.path.join(folder, "annotations.json")
        if not os.path.exists(candidate):
            return
        from src.core.io import ProjectIO
        try:
            proj = ProjectIO.load_project(candidate)
        except Exception:
            return
        if proj.map_metadata and proj.map_metadata.image_path:
            stored_basename = os.path.basename(proj.map_metadata.image_path)
            current_basename = os.path.basename(data_file_path)
            if stored_basename != current_basename:
                QMessageBox.warning(
                    self, "Annotation Mismatch",
                    f"annotations.json 이 다른 데이터({stored_basename})와 연결되어 있습니다.\n"
                    f"자동으로 불러오지 않습니다."
                )
                return
        # Pairing validated — load annotations into scene
        self.canvas_2d.background_item = None
        self.canvas_2d.load_from_data(proj)
        if proj.coordinate_system:
            cs = proj.coordinate_system
            self.coord_sys_widget.set_coordinate_system(cs)
            self._apply_coordinate_system(cs)
        self._current_file_path = candidate
        self.undo_stack.setClean()
        # BUG-003: restore 2D background after load_from_data() cleared the scene.
        # background_item was set to None before load_from_data() (required to prevent
        # segfault from stale C++ pixmap), so update_background() must be called again.
        if self.processor._points is not None:
            self._update_2d_slice()
        # Sync loaded annotations to 3D viewer (not triggered by load_from_data itself).
        self.annotation_sync.update_all_annotations(self.canvas_2d.scene)
        self._update_title_bar()

    def create_controls(self):
        config = ConfigManager.instance()

        # ── Right Dock: Properties + View Controls ──
        dock = QDockWidget(config.get_string("labels", "controls_dock"), self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        dock.setMinimumWidth(280)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)

        main_layout.addWidget(self._build_properties_section(config))
        main_layout.addWidget(self._build_coordinate_section())
        main_layout.addWidget(self._build_map_info_section())
        main_layout.addWidget(self._build_view_section(config))
        main_layout.addWidget(self._build_annotation_section())

        manage_btn = QPushButton("Manage Types...")
        manage_btn.setStyleSheet("margin: 8px;")
        manage_btn.clicked.connect(self._open_type_editor)
        main_layout.addWidget(manage_btn)
        main_layout.addStretch()

        scroll.setWidget(container)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self._build_toolbar(config)

        # Status Bar
        self.setStatusBar(QStatusBar(self))
        self.canvas_2d.status_message.connect(self.statusBar().showMessage)
        self.canvas_2d.unknown_types_warning.connect(self._on_unknown_types)

        # Load bundled sample data on startup (can be disabled in Preferences)
        from PyQt6.QtCore import QSettings, QTimer
        if QSettings().value("startup/autoload_sample", defaultValue=True, type=bool):
            sample_path = "data/sample/sample.ply"
            if os.path.exists(sample_path):
                QTimer.singleShot(1000, lambda: self.load_data(sample_path))

    def _build_properties_section(self, config):
        self.properties_panel = PropertiesPanel(self.canvas_2d)
        self.properties_panel.connect_scene(self.canvas_2d.scene)
        section = CollapsibleSection("Properties")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.properties_panel)
        section.set_content_layout(layout)
        return section

    def _build_coordinate_section(self):
        self.coord_sys_widget = CoordinateSystemWidget()
        self.coord_sys_widget.coordinate_system_changed.connect(
            self._on_coordinate_system_changed
        )
        section = CollapsibleSection("Coordinate System")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.coord_sys_widget)
        section.set_content_layout(layout)
        return section

    def _build_map_info_section(self):
        self._map_info_section = CollapsibleSection("Map Info")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        self._map_info_file_label = QLabel("File: —")
        self._map_info_resolution_label = QLabel("Resolution: —")
        self._map_info_origin_label = QLabel("Origin: —")
        self._map_info_size_label = QLabel("Size: —")
        self._map_info_block_height_label = QLabel("Block Height: —")
        for lbl in [self._map_info_file_label, self._map_info_resolution_label,
                    self._map_info_origin_label, self._map_info_size_label,
                    self._map_info_block_height_label]:
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
        self._map_info_section.set_content_layout(layout)
        self._map_info_section.setVisible(False)
        return self._map_info_section

    def _build_view_section(self, config):
        section = CollapsibleSection("View Controls")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)

        layout.addWidget(QLabel(config.get_string("labels", "slice_height")))
        self.z_slider = QSlider(Qt.Orientation.Horizontal)
        self.z_slider.setRange(0, 100)
        self.z_slider.valueChanged.connect(self.on_slider_change)
        self.z_slider.sliderPressed.connect(self._on_slider_pressed)
        self.z_slider.sliderReleased.connect(self._on_slider_released)
        self._slider_dragging = False
        layout.addWidget(self.z_slider)

        from PyQt6.QtCore import QTimer
        self._3d_final_timer = QTimer()
        self._3d_final_timer.setSingleShot(True)
        self._3d_final_timer.setInterval(150)
        self._3d_final_timer.timeout.connect(self._update_3d_final)

        self.z_label = QLabel(config.get_string("labels", "z_value").format(0.0))
        layout.addWidget(self.z_label)

        layout.addWidget(QLabel("Projection"))
        self.projection_mode_combo = QComboBox()
        self.projection_mode_combo.addItems(["Slice", "All Points"])
        self.projection_mode_combo.currentIndexChanged.connect(self._on_projection_mode_changed)
        layout.addWidget(self.projection_mode_combo)

        self.geometry_visible_checkbox = QCheckBox("Show Original 3D Data")
        self.geometry_visible_checkbox.setChecked(True)
        self.geometry_visible_checkbox.stateChanged.connect(self.on_geometry_visibility_changed)
        layout.addWidget(self.geometry_visible_checkbox)

        section.set_content_layout(layout)
        return section

    def _build_annotation_section(self):
        section = CollapsibleSection("Annotation Visibility")
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)

        self._anno_checkboxes = {}
        for category, label in [("room", "Room"), ("wall", "Wall"),
                                 ("custom_polygon", "Zone"),
                                 ("object", "Object")]:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, cat=category: self._on_anno_visibility_changed(cat, state)
            )
            layout.addWidget(cb)
            self._anno_checkboxes[category] = cb

        section.set_content_layout(layout)
        return section

    def _build_toolbar(self, config):
        self.toolbar = QToolBar(config.get_string("labels", "toolbar"))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.setExclusive(True)

        tool_defs = [
            ("select", "Select", "tools", "select", "Esc"),
            None,
            ("wall", "Wall", "tools", "wall", "W"),
            ("room", "Room", "tools", "rect", "R"),
            ("custom_polygon", "Zone", "tools", "custom_polygon", "Z"),
            ("object", "Object", "tools", "object", "O"),
        ]

        self._tool_actions = {}
        for item in tool_defs:
            if item is None:
                self.toolbar.addSeparator()
                continue
            tool_name, label, sc_group, sc_key, default_key = item
            shortcut = config.get_shortcut(sc_group, sc_key) or default_key
            action = QAction(f"{label} ({shortcut})", self)
            action.setCheckable(True)
            action.setShortcut(shortcut)
            action.setToolTip(f"{label} ({shortcut})")
            action.triggered.connect(lambda checked, tn=tool_name: self._on_tool_action(tn))
            self.tool_action_group.addAction(action)
            self.toolbar.addAction(action)
            self._tool_actions[tool_name] = action

        self._tool_actions["select"].setChecked(True)
        self.canvas_2d.tool_changed.connect(self._sync_toolbar_to_tool)

        self.toolbar.addSeparator()

        delete_shortcut_raw = config.get_shortcut("tools", "delete") or "Delete"
        if isinstance(delete_shortcut_raw, list):
            delete_shortcut = delete_shortcut_raw[0]
        else:
            delete_shortcut = delete_shortcut_raw
        delete_action = QAction(f"Delete ({delete_shortcut})", self)
        delete_action.setShortcut(delete_shortcut)
        delete_action.setToolTip(f"Delete ({delete_shortcut})")
        delete_action.triggered.connect(self.canvas_2d.delete_selected_items)
        self.toolbar.addAction(delete_action)

        self.toolbar.addSeparator()

        undo_shortcut = config.get_shortcut("edit", "undo") or "Ctrl+Z"
        undo_action = self.undo_stack.createUndoAction(self, f"{config.get_string('undo', 'undo')} ({undo_shortcut})")
        undo_action.setShortcut(undo_shortcut)
        undo_action.setToolTip(f"Undo ({undo_shortcut})")
        self.toolbar.addAction(undo_action)

        redo_shortcut = config.get_shortcut("edit", "redo") or "Ctrl+Y"
        redo_action = self.undo_stack.createRedoAction(self, f"{config.get_string('undo', 'redo')} ({redo_shortcut})")
        redo_action.setShortcut(redo_shortcut)
        redo_action.setToolTip(f"Redo ({redo_shortcut})")
        self.toolbar.addAction(redo_action)

    def _on_tool_action(self, tool_name):
        self.canvas_2d.set_tool(tool_name)

    def _sync_toolbar_to_tool(self, tool_name):
        action = self._tool_actions.get(tool_name)
        if action:
            action.setChecked(True)

    def _open_type_editor(self):
        from src.gui.type_editor_dialog import TypeEditorDialog
        if self._type_editor_dialog is None:
            self._type_editor_dialog = TypeEditorDialog(self.canvas_2d, parent=self)
            # Connect config changes to properties panel refresh
            self._type_editor_dialog.room_editor.config_changed.connect(
                lambda: self.properties_panel._on_selection_changed()
            )
            self._type_editor_dialog.custom_polygon_editor.config_changed.connect(
                lambda: self.properties_panel._on_selection_changed()
            )
            self._type_editor_dialog.object_editor.config_changed.connect(
                lambda: self.properties_panel._on_selection_changed()
            )
        self._type_editor_dialog.exec()

    def _import_annotations(self, path: str) -> None:
        """Load annotations from *path* into the current scene without reloading 3D data."""
        from src.core.io import ProjectIO
        try:
            proj = ProjectIO.load_project(path)
        except Exception as e:
            QMessageBox.critical(self, "Open Error", str(e))
            return
        self._current_file_path = path
        self.undo_stack.clear()
        self.canvas_2d.background_item = None
        self.canvas_2d.load_from_data(proj)
        if proj.coordinate_system:
            cs = proj.coordinate_system
            self.coord_sys_widget.set_coordinate_system(cs)
            self._apply_coordinate_system(cs)
        # Skip _restore_data_source — 3D data is already loaded
        if self.processor._points is not None:
            self._update_2d_slice()
        self.undo_stack.setClean()
        self.annotation_sync.update_all_annotations(self.canvas_2d.scene)
        self._update_title_bar()

    def _open_alignment_dialog(self) -> None:
        """Open the map alignment dialog to import annotations from a reference map."""
        if not self._3d_file_path:
            return
        if not self._confirm_discard_changes():
            return

        from src.map_align.app import AlignmentWindow
        from src.map_align.map_unifier import load_as_pointcloud

        source_cloud = load_as_pointcloud(self._3d_file_path)
        source_geom = self.viewer_3d.original_geometry
        source_bounds = self.processor.get_bounds_3d()

        dlg = AlignmentWindow(
            source_path=self._3d_file_path,
            source_cloud=source_cloud,
            source_geom=source_geom,
            source_bounds=source_bounds,
            parent=self,
        )
        if dlg.exec() == AlignmentWindow.DialogCode.Accepted:
            path = dlg.result_path()
            if path:
                self._import_annotations(path)
                self.statusBar().showMessage(
                    "Annotations imported from reference map.", 5000,
                )

    def load_data(self, file_path):
        """Load 3D data from file (point cloud or mesh, including GLB/GLTF).

        Also records the file path in _map_metadata so it is preserved
        in the project JSON and can be restored on next open (REQ-031).
        """
        # Reset UI state (e.g. re-enable slicing controls disabled by occupancy grid)
        self._set_3d_controls_for_point_cloud()

        # Apply current coordinate system before loading
        cs = self.coord_sys_widget.current_coordinate_system()
        self._apply_coordinate_system(cs)

        self.viewer_3d.load_geometry(file_path)
        if self.viewer_3d.original_geometry:
            self.processor.load_data(self.viewer_3d.original_geometry)
            self._all_points_cache = None
            self.canvas_2d._scene_initialized = False

            # Initialize annotation sync system
            self.annotation_sync.initialize_geometry(self.viewer_3d.original_geometry)

            self.z_slider.setValue(50)
            self.on_slider_change(50)

            # Track data source path for project save/restore (REQ-031)
            from src.model.data import MapMetadata
            meta = MapMetadata()
            meta.image_path = os.path.basename(file_path)
            meta.image_path_absolute = os.path.abspath(file_path)
            bounds = self.processor.get_bounds_3d()
            if bounds is not None:
                meta.bounds_min, meta.bounds_max = bounds
            self._map_metadata = meta

            # Auto-detect annotations.json in the same folder (FEAT-006)
            self._3d_file_path = os.path.abspath(file_path)
            self._recent_mgr.add(self._3d_file_path)
            self._detect_annotations_for_3d_file(self._3d_file_path)
            self._update_title_bar()
            self._act_import_align.setEnabled(True)

    def on_slider_change(self, value):
        if not self.processor._points is None:
            min_z, max_z = self.processor.get_z_range()
            range_z = max_z - min_z
            self.current_z = min_z + (value / 100.0) * range_z
            config = ConfigManager.instance()
            self.z_label.setText(config.get_string("labels", "z_value").format(self.current_z))

            # Always update 2D immediately (~22ms)
            self._update_2d_slice()

            # 3D update: fast preview during drag, debounced full-res otherwise
            if self._slider_dragging:
                self.viewer_3d.update_slice_dragging(self.current_z)
            else:
                # Keyboard/wheel changes: debounce to avoid lag
                self._3d_final_timer.start()

    def _on_slider_pressed(self):
        self._slider_dragging = True

    def _on_slider_released(self):
        self._slider_dragging = False
        self._3d_final_timer.start()

    def _update_2d_slice(self):
        """Update 2D slice visualization (fast path, always runs)."""
        bounds_2d = self.processor.get_bounds_2d()

        if self.projection_mode_combo.currentIndex() == 1:  # All Points
            if self._all_points_cache is None:
                points, colors = self.processor.get_all_points()
                img, bounds, scale = self.processor.project_to_image(
                    points, pixel_size=0.02, fixed_bounds=bounds_2d, colors=colors
                )
                self._all_points_cache = (img, bounds, scale)
            img, bounds, scale = self._all_points_cache
        else:  # Slice
            points, colors = self.processor.slice_at_height(self.current_z, thickness=0.1)
            img, bounds, scale = self.processor.project_to_image(
                points, pixel_size=0.02, fixed_bounds=bounds_2d, colors=colors
            )

        self.canvas_2d.update_background(img, bounds, scale)
        self.annotation_sync.set_world_bounds(bounds)

    def _on_projection_mode_changed(self, index):
        """Handle projection mode combo change."""
        self._update_2d_slice()

    def _update_3d_final(self):
        """Full-resolution 3D update (called after slider stops)."""
        self.viewer_3d.update_slice_final(self.current_z)
        # Auto-reactivate "Show Original 3D Data" checkbox (BUG-003 / REQ-017)
        if not self.geometry_visible_checkbox.isChecked():
            self.geometry_visible_checkbox.setChecked(True)

    def update_slice(self):
        """Update the full slice visualization (2D + 3D full-res)."""
        self._update_2d_slice()
        self.viewer_3d.update_slice_plane(self.current_z)
        if not self.geometry_visible_checkbox.isChecked():
            self.geometry_visible_checkbox.setChecked(True)

    def load_point_cloud(self):
        if not self._confirm_discard_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open 3D Data", "",
            "3D Data Files (*.ply *.pcd *.obj *.stl *.glb *.gltf);;All Files (*)"
        )
        if file_path:
            self._current_file_path = None
            self.undo_stack.clear()
            self.load_data(file_path)

    def on_undo_stack_changed(self):
        """
        Resync all annotations after any undo stack change.

        This is triggered by:
        - Room creation (AddItemCommand)
        - Room drag completion (MoveNodesCommand)
        - Room type change (ChangeRoomTypeCommand)
        - Item deletion (DeleteItemCommand)
        - Undo/redo operations
        """
        if self.annotation_sync:
            self.annotation_sync.update_all_annotations(self.canvas_2d.scene)

    def _on_unknown_types(self, entries: list[str]):
        """Warn the user about type keys not found in config after loading."""
        from PyQt6.QtWidgets import QMessageBox
        unique = sorted(set(entries))
        text = "\n".join(f"• {e}" for e in unique)
        QMessageBox.warning(
            self, "Unknown Annotation Types",
            f"The following types are not defined in config and will use fallback style:\n\n{text}",
        )

    def _on_anno_visibility_changed(self, category: str, state: int):
        """Handle annotation category visibility checkbox change."""
        from PyQt6.QtCore import Qt
        visible = (state == Qt.CheckState.Checked.value)
        self.annotation_sync.set_category_visibility(category, visible)

    def _on_coordinate_system_changed(self, cs: CoordinateSystem):
        """Handle coordinate system change from widget."""
        self._apply_coordinate_system(cs)
        # Re-render if data is loaded
        if self.processor._points is not None:
            self.on_slider_change(self.z_slider.value())
            self.annotation_sync.update_all_annotations(self.canvas_2d.scene)

    def _apply_coordinate_system(self, cs: CoordinateSystem):
        """Push a coordinate system to processor, viewer, and annotation sync."""
        self.processor.set_coordinate_system(cs)
        self.viewer_3d.set_coordinate_system(cs)
        self.annotation_sync.set_coordinate_system(cs)
        self._all_points_cache = None

    def load_occupancy_grid(self):
        """Load a ROS2 occupancy grid map (YAML or image)."""
        if not self._confirm_discard_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Occupancy Grid", "",
            "Map Files (*.yaml *.yml *.pgm *.png);;YAML Files (*.yaml *.yml);;Image Files (*.pgm *.png)"
        )
        if not file_path:
            return
        self._current_file_path = None
        self.undo_stack.clear()

        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext in ('.yaml', '.yml'):
                metadata = MapLoader.parse_yaml(file_path)
                image_path = metadata.image_path_absolute
            else:
                # Image file — try to find companion YAML
                yaml_path = MapLoader.find_yaml_for_image(file_path)
                if yaml_path:
                    metadata = MapLoader.parse_yaml(yaml_path)
                    image_path = metadata.image_path_absolute
                else:
                    # No YAML found — show manual metadata dialog
                    from src.gui.map_metadata_dialog import MapMetadataDialog
                    dlg = MapMetadataDialog(self)
                    if dlg.exec() != MapMetadataDialog.DialogCode.Accepted:
                        return
                    metadata = dlg.get_metadata()
                    metadata.image_path_absolute = os.path.abspath(file_path)
                    metadata.image_path = os.path.basename(file_path)
                    image_path = metadata.image_path_absolute

            image_data = MapLoader.load_image(image_path, metadata)
            bounds = MapLoader.compute_bounds(metadata)
            scale = MapLoader.compute_scale(metadata)
            self._apply_occupancy_grid(image_data, metadata, bounds, scale)

        except (FileNotFoundError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load occupancy grid:\n{e}")

    def _apply_occupancy_grid(self, image_data, metadata, bounds, scale):
        """Apply loaded occupancy grid data to the scene and 3D viewer."""
        # Clear scene and undo stack
        self.canvas_2d.background_item = None
        self.undo_stack.clear()
        self.canvas_2d.scene.clear()
        self.canvas_2d._scene_initialized = False
        self._all_points_cache = None
        # Setup display
        self._setup_occupancy_grid_display(image_data, metadata, bounds, scale)

    # File extensions treated as 3D data (point cloud / mesh), not occupancy grid
    _3D_EXTENSIONS = frozenset({'.ply', '.pcd', '.obj', '.stl', '.glb', '.gltf'})

    def _restore_data_source(self, metadata, project_path):
        """Dispatch data-source restoration by file extension (REQ-031).

        Occupancy grid images (.pgm, .png + yaml metadata) → _restore_occupancy_grid()
        3D data files (.ply, .pcd, .obj, .stl, .glb, .gltf) → _restore_3d_data()
        """
        from pathlib import Path
        ext = Path(metadata.image_path).suffix.lower()
        if ext in self._3D_EXTENSIONS:
            self._restore_3d_data(metadata, project_path)
        else:
            self._restore_occupancy_grid(metadata, project_path)

    def _restore_3d_data(self, metadata, project_path):
        """Restore a PLY/GLB/GLTF/OBJ data source saved in project metadata.

        Resolves data path: relative → absolute → user selection fallback.
        """
        from pathlib import Path
        project_dir = os.path.dirname(os.path.abspath(project_path))

        data_path = None
        rel_candidate = os.path.normpath(os.path.join(project_dir, metadata.image_path))
        if metadata.image_path and os.path.exists(rel_candidate):
            data_path = rel_candidate
        elif metadata.image_path_absolute and os.path.exists(metadata.image_path_absolute):
            data_path = metadata.image_path_absolute
        else:
            data_path, _ = QFileDialog.getOpenFileName(
                self, "Locate 3D Data File",
                project_dir,
                "3D Data Files (*.ply *.pcd *.obj *.stl *.glb *.gltf);;All Files (*)"
            )
            if not data_path:
                print("3D data file not found — skipping data source restoration")
                self._set_3d_controls_for_point_cloud()
                return

        # Update metadata with resolved absolute path before load_data() overwrites it
        metadata.image_path_absolute = os.path.abspath(data_path)
        self.load_data(data_path)
        # Restore original relative image_path (load_data sets only basename)
        self._map_metadata.image_path = metadata.image_path

    def _restore_occupancy_grid(self, metadata, project_path):
        """Restore occupancy grid from saved project metadata.

        Resolves image path: relative → absolute → user selection fallback.
        """
        project_dir = os.path.dirname(os.path.abspath(project_path))

        # Try relative path first, then absolute, then ask user
        image_path = None
        rel_candidate = os.path.normpath(os.path.join(project_dir, metadata.image_path))
        if metadata.image_path and os.path.exists(rel_candidate):
            image_path = rel_candidate
        elif metadata.image_path_absolute and os.path.exists(metadata.image_path_absolute):
            image_path = metadata.image_path_absolute
        else:
            image_path, _ = QFileDialog.getOpenFileName(
                self, "Locate Map Image",
                project_dir,
                "Image Files (*.pgm *.png);;All Files (*)"
            )
            if not image_path:
                print("Map image not found — skipping occupancy grid restoration")
                self._set_3d_controls_for_point_cloud()
                return

        try:
            metadata.image_path_absolute = os.path.abspath(image_path)
            image_data = MapLoader.load_image(image_path, metadata)
            bounds = MapLoader.compute_bounds(metadata)
            scale = MapLoader.compute_scale(metadata)
            self._setup_occupancy_grid_display(image_data, metadata, bounds, scale)
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(self, "Warning", f"Failed to restore occupancy grid:\n{e}")
            self._set_3d_controls_for_point_cloud()

    def _setup_occupancy_grid_display(self, image_data, metadata, bounds, scale):
        """Common setup for occupancy grid display (2D background + 3D mesh + UI)."""
        config = ConfigManager.instance()

        self._map_metadata = metadata
        self._map_image_data = image_data

        # Coordinate system → ROS
        cs = CoordinateSystem.ros()
        self.coord_sys_widget.set_coordinate_system(cs)
        self._apply_coordinate_system(cs)

        # 2D background
        self.canvas_2d.update_background(image_data, bounds, scale)
        self.annotation_sync.set_world_bounds(bounds)

        # 3D block mesh
        block_height = config.get_ui_value("occupancy_grid", "block_height")
        mesh = MapMeshGenerator.generate_mesh(image_data, metadata, block_height)
        self.viewer_3d.set_geometry(mesh)

        # UI state
        self.z_slider.setEnabled(False)
        self.projection_mode_combo.setEnabled(False)
        self.z_label.setText("Z: N/A (occupancy grid)")
        self.geometry_visible_checkbox.setEnabled(True)
        self.geometry_visible_checkbox.setChecked(True)
        self._update_map_info(metadata, block_height)

        # Auto-detect annotations.json in the same folder (FEAT-006)
        if metadata.image_path_absolute:
            self._3d_file_path = metadata.image_path_absolute
            self._recent_mgr.add(metadata.image_path_absolute)
            self._detect_annotations_for_3d_file(metadata.image_path_absolute)
            self._update_title_bar()

    def _set_3d_controls_for_point_cloud(self):
        """Re-enable 3D controls for point cloud mode."""
        self.z_slider.setEnabled(True)
        self.projection_mode_combo.setEnabled(True)
        self.annotation_sync.set_enabled(True)
        self._map_metadata = None
        self._map_image_data = None
        self._map_info_section.setVisible(False)

    def _update_map_info(self, metadata, block_height):
        """Update Map Info section labels."""
        fname = os.path.basename(metadata.image_path_absolute) if metadata.image_path_absolute else metadata.image_path
        w, h = metadata.image_width, metadata.image_height
        res = metadata.resolution
        self._map_info_file_label.setText(f"File: {fname}")
        self._map_info_resolution_label.setText(f"Resolution: {res} m/px")
        self._map_info_origin_label.setText(f"Origin: ({metadata.origin_x}, {metadata.origin_y})")
        self._map_info_size_label.setText(f"Size: {w}\u00d7{h} px ({w * res:.1f}\u00d7{h * res:.1f} m)")
        self._map_info_block_height_label.setText(f"Block Height: {block_height} m")
        self._map_info_section.setVisible(True)

    def on_geometry_visibility_changed(self, state):
        """
        Handle geometry visibility checkbox change.

        Args:
            state: Qt.CheckState (Checked = show, Unchecked = hide)
        """
        from PyQt6.QtCore import Qt
        visible = (state == Qt.CheckState.Checked.value)
        self.viewer_3d.set_geometry_visibility(visible)
