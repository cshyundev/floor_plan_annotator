from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QFileDialog, QSlider, QLabel, QDockWidget, QToolBar, QStatusBar)
from PyQt6.QtGui import QAction, QIcon, QUndoStack
from PyQt6.QtCore import Qt
from src.gui.viewer_3d import Viewer3D
from src.gui.canvas_2d import Canvas2D
from src.core.processor import SliceEngine
import numpy as np

from src.core.config import ConfigManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        config = ConfigManager.instance()
        self.setWindowTitle(config.get_string("window", "title"))
        self.resize(1200, 800)
        
        # Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Splitter for 3D and 2D views
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # 3D Viewer
        self.viewer_3d = Viewer3D()
        self.splitter.addWidget(self.viewer_3d)
        
        # 2D Viewer
        self.canvas_2d = Canvas2D()
        self.splitter.addWidget(self.canvas_2d)
        
        # Set initial sizes
        self.splitter.setSizes([600, 600])
        
        # Helper
        self.undo_stack = QUndoStack(self)
        self.canvas_2d.set_undo_stack(self.undo_stack)
        
        # Controls (Dock)
        self.create_controls()
        
        # Data
        self.processor = SliceEngine()
        self.current_z = 0.0
        
        # Menu Bar
        self.create_menu()

    def create_menu(self):
        config = ConfigManager.instance()
        menubar = self.menuBar()
        file_menu = menubar.addMenu(config.get_string("menu", "file"))
        
        load_action = QAction(config.get_string("menu", "load_point_cloud"), self)
        load_action.triggered.connect(self.load_point_cloud)
        file_menu.addAction(load_action)
        
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
        
    def save_project(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON Files (*.json)")
        if file_path:
            from src.core.io import ProjectIO
            # 1. Get data from canvas
            project_data = self.canvas_2d.save_to_data()
            # 2. Save
            ProjectIO.save_project(project_data, file_path)
            print(f"Project saved to {file_path}")

    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "JSON Files (*.json)")
        if file_path:
            from src.core.io import ProjectIO
            # 1. Load data
            project_data = ProjectIO.load_project(file_path)
            # 2. Populate canvas
            self.canvas_2d.load_from_data(project_data)
            print(f"Project loaded from {file_path}")
            
    def create_controls(self):
        config = ConfigManager.instance()
        dock = QDockWidget(config.get_string("labels", "controls_dock"), self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel(config.get_string("labels", "slice_height")))
        self.z_slider = QSlider(Qt.Orientation.Horizontal)
        self.z_slider.setRange(0, 100) # 0 to 100% of height
        self.z_slider.valueChanged.connect(self.on_slider_change)
        layout.addWidget(self.z_slider)
        
        self.z_label = QLabel(config.get_string("labels", "z_value").format(0.0))
        layout.addWidget(self.z_label)
        
        layout.addStretch()
        dock.setWidget(widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        # Toolbar
        config = ConfigManager.instance()
        self.toolbar = QToolBar(config.get_string("labels", "toolbar"))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        select_action = QAction("Select", self)
        select_action.setShortcut(config.get_shortcut("tools", "select") or "Esc")
        select_action.triggered.connect(lambda: self.canvas_2d.set_tool("select"))
        self.toolbar.addAction(select_action)
        
        wall_action = QAction("Wall", self)
        wall_action.setShortcut(config.get_shortcut("tools", "wall") or "W")
        wall_action.triggered.connect(lambda: self.canvas_2d.set_tool("wall"))
        self.toolbar.addAction(wall_action)

        rect_action = QAction("Room (Polygon)", self)
        rect_action.setShortcut(config.get_shortcut("tools", "rect") or "R")
        rect_action.triggered.connect(lambda: self.canvas_2d.set_tool("room"))
        self.toolbar.addAction(rect_action)
        
        self.toolbar.addSeparator()
        
        undo_action = self.undo_stack.createUndoAction(self, config.get_string("undo", "undo"))
        undo_action.setShortcut(config.get_shortcut("edit", "undo") or "Ctrl+Z")
        self.toolbar.addAction(undo_action)
        
        redo_action = self.undo_stack.createRedoAction(self, config.get_string("undo", "redo"))
        redo_action.setShortcut(config.get_shortcut("edit", "redo") or "Ctrl+Y")
        self.toolbar.addAction(redo_action)
        
        # Status Bar
        self.setStatusBar(QStatusBar(self))
        self.canvas_2d.status_message.connect(self.statusBar().showMessage)
        
        # Auto-load dummy data for development
        import os
        dummy_paths = ["data/layout_dummy.ply", "layout_dummy.ply"]
        target_path = None
        for p in dummy_paths:
            if os.path.exists(p):
                target_path = p
                break
                
        if target_path:
            print(f"Auto-loading {target_path} for development...")
            # Use QTimer to delay load slightly to ensure window is ready
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, lambda: self.load_data(target_path))

    def load_data(self, file_path):
        self.viewer_3d.load_geometry(file_path)
        if self.viewer_3d.geometry:
            self.processor.load_data(self.viewer_3d.geometry)
            self.z_slider.setValue(50)
            self.on_slider_change(50)

    def on_slider_change(self, value):
        if not self.processor._points is None:
            min_z, max_z = self.processor.get_z_range()
            range_z = max_z - min_z
            self.current_z = min_z + (value / 100.0) * range_z
            config = ConfigManager.instance()
            self.z_label.setText(config.get_string("labels", "z_value").format(self.current_z))
            self.update_slice()

    def update_slice(self):
        # 1. Get Slice
        points, colors = self.processor.slice_at_height(self.current_z, thickness=0.1)
        
        # 2. Project
        img, bounds, scale = self.processor.project_to_image(points, pixel_size=0.02)
        
        # 3. Update 2D
        self.canvas_2d.update_background(img, bounds, scale)
        
        # 4. Update 3D (Show Plane)
        self.viewer_3d.update_slice_plane(self.current_z)

    def load_point_cloud(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Point Cloud", "", "Point Cloud Files (*.ply *.pcd *.obj *.stl)"
        )
        if file_path:
            self.load_data(file_path)
