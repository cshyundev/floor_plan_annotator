from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QFileDialog, QSlider, QLabel, QDockWidget,
                             QToolBar, QStatusBar, QCheckBox, QPushButton, QScrollArea,
                             QMessageBox)
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

        # Connect undo stack changes to sync + properties refresh
        self.undo_stack.indexChanged.connect(self.on_undo_stack_changed)
        self.undo_stack.indexChanged.connect(
            lambda: self.properties_panel._on_selection_changed()
        )

        # Menu Bar
        self.create_menu()

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

        file_menu.addSeparator()

        open_proj_action = QAction(config.get_string("menu", "open_project"), self)
        open_proj_action.setShortcut(config.get_shortcut("file", "open_project") or "Ctrl+O")
        open_proj_action.triggered.connect(self.open_project)
        file_menu.addAction(open_proj_action)

        save_proj_action = QAction(config.get_string("menu", "save_project"), self)
        save_proj_action.setShortcut(config.get_shortcut("file", "save_project") or "Ctrl+S")
        save_proj_action.triggered.connect(self.save_project)
        file_menu.addAction(save_proj_action)

        file_menu.addSeparator()

        exit_action = QAction(config.get_string("menu", "exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        manage_types_action = QAction("Manage Types...", self)
        manage_types_action.triggered.connect(self._open_type_editor)
        edit_menu.addAction(manage_types_action)

    def save_project(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON Files (*.json)")
        if file_path:
            from src.core.io import ProjectIO
            # 1. Get data from canvas
            project_data = self.canvas_2d.save_to_data()
            # 2. Attach coordinate system
            project_data.coordinate_system = self.coord_sys_widget.current_coordinate_system()
            # 3. Attach map metadata with relative path
            if self._map_metadata is not None:
                meta_copy = MapMetadata.from_dict(self._map_metadata.to_dict())
                meta_copy.image_path = MapLoader.make_relative_path(
                    self._map_metadata.image_path_absolute, file_path
                )
                project_data.map_metadata = meta_copy
            # 4. Save
            ProjectIO.save_project(project_data, file_path)
            print(f"Project saved to {file_path}")

    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "JSON Files (*.json)")
        if file_path:
            from src.core.io import ProjectIO
            # 1. Load data
            project_data = ProjectIO.load_project(file_path)
            # 2. Restore coordinate system
            cs = project_data.coordinate_system
            self.coord_sys_widget.set_coordinate_system(cs)
            self._apply_coordinate_system(cs)
            # 3. Clear dangling background pointer before scene.clear()
            self.canvas_2d.background_item = None
            # 4. Populate canvas
            self.canvas_2d.load_from_data(project_data)
            # 5. Restore occupancy grid if present
            if project_data.map_metadata is not None:
                self._restore_occupancy_grid(project_data.map_metadata, file_path)
            else:
                # Point cloud mode — ensure 3D controls are fully enabled
                self._set_3d_controls_for_point_cloud()
            print(f"Project loaded from {file_path}")

    def create_controls(self):
        config = ConfigManager.instance()

        # ── Right Dock: Properties + View Controls ──
        dock = QDockWidget(config.get_string("labels", "controls_dock"), self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        dock.setMinimumWidth(280)

        # Scrollable container for the dock
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)

        # Section 1: Properties
        self.properties_panel = PropertiesPanel(self.canvas_2d)
        self.properties_panel.connect_scene(self.canvas_2d.scene)

        props_section = CollapsibleSection("Properties")
        props_layout = QVBoxLayout()
        props_layout.setContentsMargins(0, 0, 0, 0)
        props_layout.addWidget(self.properties_panel)
        props_section.set_content_layout(props_layout)
        main_layout.addWidget(props_section)

        # Section 2: Coordinate System
        self.coord_sys_widget = CoordinateSystemWidget()
        self.coord_sys_widget.coordinate_system_changed.connect(
            self._on_coordinate_system_changed
        )

        cs_section = CollapsibleSection("Coordinate System")
        cs_layout = QVBoxLayout()
        cs_layout.setContentsMargins(0, 0, 0, 0)
        cs_layout.addWidget(self.coord_sys_widget)
        cs_section.set_content_layout(cs_layout)
        main_layout.addWidget(cs_section)

        # Section 3: Map Info (hidden until occupancy grid loaded)
        self._map_info_section = CollapsibleSection("Map Info")
        map_info_layout = QVBoxLayout()
        map_info_layout.setContentsMargins(8, 4, 8, 4)
        self._map_info_file_label = QLabel("File: —")
        self._map_info_resolution_label = QLabel("Resolution: —")
        self._map_info_origin_label = QLabel("Origin: —")
        self._map_info_size_label = QLabel("Size: —")
        self._map_info_block_height_label = QLabel("Block Height: —")
        for lbl in [self._map_info_file_label, self._map_info_resolution_label,
                    self._map_info_origin_label, self._map_info_size_label,
                    self._map_info_block_height_label]:
            lbl.setWordWrap(True)
            map_info_layout.addWidget(lbl)
        self._map_info_section.set_content_layout(map_info_layout)
        self._map_info_section.setVisible(False)
        main_layout.addWidget(self._map_info_section)

        # Section 4: View Controls
        view_section = CollapsibleSection("View Controls")
        view_layout = QVBoxLayout()
        view_layout.setContentsMargins(8, 4, 8, 4)

        view_layout.addWidget(QLabel(config.get_string("labels", "slice_height")))
        self.z_slider = QSlider(Qt.Orientation.Horizontal)
        self.z_slider.setRange(0, 100)
        self.z_slider.valueChanged.connect(self.on_slider_change)
        self.z_slider.sliderPressed.connect(self._on_slider_pressed)
        self.z_slider.sliderReleased.connect(self._on_slider_released)
        self._slider_dragging = False
        view_layout.addWidget(self.z_slider)

        # Debounce timer for full-resolution 3D update after slider stops
        from PyQt6.QtCore import QTimer
        self._3d_final_timer = QTimer()
        self._3d_final_timer.setSingleShot(True)
        self._3d_final_timer.setInterval(150)
        self._3d_final_timer.timeout.connect(self._update_3d_final)

        self.z_label = QLabel(config.get_string("labels", "z_value").format(0.0))
        view_layout.addWidget(self.z_label)

        self.geometry_visible_checkbox = QCheckBox("Show Original 3D Data")
        self.geometry_visible_checkbox.setChecked(True)
        self.geometry_visible_checkbox.stateChanged.connect(self.on_geometry_visibility_changed)
        view_layout.addWidget(self.geometry_visible_checkbox)

        view_section.set_content_layout(view_layout)
        main_layout.addWidget(view_section)

        # Section 3: Annotation Visibility
        anno_section = CollapsibleSection("Annotation Visibility")
        anno_layout = QVBoxLayout()
        anno_layout.setContentsMargins(8, 4, 8, 4)

        self._anno_checkboxes = {}
        for category, label in [("room", "Room"), ("wall", "Wall"),
                                 ("custom_polygon", "Custom Polygon"),
                                 ("object", "Object")]:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda state, cat=category: self._on_anno_visibility_changed(cat, state)
            )
            anno_layout.addWidget(cb)
            self._anno_checkboxes[category] = cb

        anno_section.set_content_layout(anno_layout)
        main_layout.addWidget(anno_section)

        # Manage Types button
        manage_btn = QPushButton("Manage Types...")
        manage_btn.setStyleSheet("margin: 8px;")
        manage_btn.clicked.connect(self._open_type_editor)
        main_layout.addWidget(manage_btn)

        main_layout.addStretch()

        scroll.setWidget(container)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        # ── Toolbar (checkable tool buttons) ──
        self.toolbar = QToolBar(config.get_string("labels", "toolbar"))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        # Tool action group (exclusive — only one tool active at a time)
        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.setExclusive(True)

        tool_defs = [
            ("select", "Select", "tools", "select", "Esc"),
            None,  # separator after Select
            ("wall", "Wall", "tools", "wall", "W"),
            ("room", "Room", "tools", "rect", "R"),
            ("custom_polygon", "Polygon", "tools", "custom_polygon", "P"),
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

        # Default: select tool checked
        self._tool_actions["select"].setChecked(True)

        # Sync toolbar when tool changes via keyboard or other means
        self.canvas_2d.tool_changed.connect(self._sync_toolbar_to_tool)

        self.toolbar.addSeparator()

        delete_shortcut_raw = config.get_shortcut("tools", "delete") or "Delete"
        # Handle list of shortcuts (e.g. ["Delete", "Backspace"])
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

        # Status Bar
        self.setStatusBar(QStatusBar(self))
        self.canvas_2d.status_message.connect(self.statusBar().showMessage)

        # Auto-load dummy data for development
        dummy_paths = ["data/layout_dummy.ply", "layout_dummy.ply"]
        target_path = None
        for p in dummy_paths:
            if os.path.exists(p):
                target_path = p
                break

        if target_path:
            print(f"Auto-loading {target_path} for development...")
            # Use QTimer to delay load to ensure window and renderer are ready
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self.load_data(target_path))

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

    def load_data(self, file_path):
        """Load 3D data from file."""
        # Apply current coordinate system before loading
        cs = self.coord_sys_widget.current_coordinate_system()
        self._apply_coordinate_system(cs)

        self.viewer_3d.load_geometry(file_path)
        if self.viewer_3d.geometry:
            self.processor.load_data(self.viewer_3d.geometry)
            self.canvas_2d._scene_initialized = False

            # Initialize annotation sync system
            self.annotation_sync.initialize_geometry(self.viewer_3d.geometry)

            self.z_slider.setValue(50)
            self.on_slider_change(50)

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
        points, colors = self.processor.slice_at_height(self.current_z, thickness=0.1)
        bounds_2d = self.processor.get_bounds_2d()
        img, bounds, scale = self.processor.project_to_image(points, pixel_size=0.02, fixed_bounds=bounds_2d)
        self.canvas_2d.update_background(img, bounds, scale)
        self.annotation_sync.set_world_bounds(bounds)

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
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Point Cloud", "", "Point Cloud Files (*.ply *.pcd *.obj *.stl)"
        )
        if file_path:
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

    def load_occupancy_grid(self):
        """Load a ROS2 occupancy grid map (YAML or image)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Occupancy Grid", "",
            "Map Files (*.yaml *.yml *.pgm *.png);;YAML Files (*.yaml *.yml);;Image Files (*.pgm *.png)"
        )
        if not file_path:
            return

        # Warn if existing annotations (not just background pixmap)
        from src.gui.items import RoomItem, EdgeItem, CustomPolygonItem, ObjectItem
        annotation_types = (RoomItem, EdgeItem, CustomPolygonItem, ObjectItem)
        has_annotations = any(
            isinstance(item, annotation_types)
            for item in self.canvas_2d.scene.items()
        )
        if has_annotations:
            reply = QMessageBox.question(
                self, "Load Occupancy Grid",
                "Loading an occupancy grid will clear the current scene.\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

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
        """Apply loaded occupancy grid data to the scene and 3D viewer.

        Args:
            image_data: Grayscale numpy array (H, W), uint8.
            metadata: MapMetadata instance.
            bounds: (min_x, min_y, max_x, max_y) world bounds.
            scale: Pixels per meter.
        """
        config = ConfigManager.instance()

        # Cache state
        self._map_metadata = metadata
        self._map_image_data = image_data

        # Clear scene and undo stack
        self.canvas_2d.background_item = None
        self.undo_stack.clear()
        self.canvas_2d.scene.clear()
        self.canvas_2d._scene_initialized = False

        # Set coordinate system to ROS
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

        # Disable Z slider (slicing not meaningful for occupancy grid)
        self.z_slider.setEnabled(False)
        self.z_label.setText("Z: N/A (occupancy grid)")

        # Disable annotation sync (no point cloud annotation geometry needed)
        self.annotation_sync.set_enabled(False)

        # Show Original 3D Data checkbox remains functional
        self.geometry_visible_checkbox.setEnabled(True)
        self.geometry_visible_checkbox.setChecked(True)

        # Update Map Info section
        self._update_map_info(metadata, block_height)

    def _restore_occupancy_grid(self, metadata, project_path):
        """Restore occupancy grid from saved project metadata.

        Resolves image path: relative → absolute → user selection fallback.

        Args:
            metadata: MapMetadata from project file.
            project_path: Path to the project JSON file.
        """
        config = ConfigManager.instance()
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

            # Cache state
            self._map_metadata = metadata
            self._map_image_data = image_data

            # Set coordinate system to ROS
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

            # Disable Z slider
            self.z_slider.setEnabled(False)
            self.z_label.setText("Z: N/A (occupancy grid)")

            # Disable annotation sync
            self.annotation_sync.set_enabled(False)

            # Show Original 3D Data checkbox remains functional
            self.geometry_visible_checkbox.setEnabled(True)
            self.geometry_visible_checkbox.setChecked(True)

            # Update Map Info
            self._update_map_info(metadata, block_height)

        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(self, "Warning", f"Failed to restore occupancy grid:\n{e}")
            self._set_3d_controls_for_point_cloud()

    def _set_3d_controls_for_point_cloud(self):
        """Re-enable 3D controls for point cloud mode."""
        self.z_slider.setEnabled(True)
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
