from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from src.gui.tool_manager import ToolManager
from src.gui.clipboard_manager import ClipboardManager
from src.gui.data_serializer import DataSerializer
from src.gui.event_coordinator import EventCoordinator
from src.core.config import ConfigManager
from src.core.input_context import InputContext

class Canvas2D(QGraphicsView):
    status_message = pyqtSignal(str)
    tool_changed = pyqtSignal(str)

    def __init__(self, main_window=None):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Items
        self.background_item = None
        self._background_data = None  # Store original data for resize
        self._background_origin = None  # (min_x, min_y, max_x, max_y)
        self._background_scale = None  # pixels per meter

        # View state
        self._user_has_zoomed = False  # Track if user manually zoomed
        self._fit_in_view_on_resize = True  # Whether to auto-fit on resize
        self._scene_initialized = False  # True after first background load

        # Sequential ID counters
        self._next_room_id = 0
        self._next_custom_polygon_id = 0
        self._next_object_id = 0

        # Tool Manager
        self.tool_manager = ToolManager(self)

        # Clipboard Manager
        self.clipboard_manager = ClipboardManager(self)

        # Data Serializer
        self.data_serializer = DataSerializer(self)

        # Event Coordinator
        self.event_coordinator = EventCoordinator(self)

        # Enable smooth transformations
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Canvas background color from config
        config = ConfigManager.instance()
        canvas_bg = config.get_color("canvas", "background")
        self.setBackgroundBrush(canvas_bg)
        self.scene.setBackgroundBrush(canvas_bg)

        # Set view properties for better resize handling
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

    @property
    def current_tool(self):
        """Get the current active tool."""
        return self.tool_manager.current_tool

    @property
    def select_tool(self):
        """Get the select tool (for compatibility)."""
        return self.tool_manager.select_tool

    @property
    def wall_tool(self):
        """Get the wall tool (for compatibility)."""
        return self.tool_manager.wall_tool

    @property
    def room_tool(self):
        """Get the room tool (for compatibility)."""
        return self.tool_manager.room_tool

    @property
    def _clipboard(self):
        """Get clipboard data (for compatibility)."""
        return self.clipboard_manager._clipboard

    def set_undo_stack(self, stack):
        self._undo_stack = stack
        
    def push_command(self, command):
        stack = self._undo_stack
        if stack is not None:
            stack.push(command)
        else:
            command.redo()


    def next_room_id(self):
        """Return the next sequential room ID and increment counter."""
        rid = self._next_room_id
        self._next_room_id += 1
        return str(rid)

    def next_custom_polygon_id(self):
        """Return the next sequential custom polygon ID and increment counter."""
        pid = self._next_custom_polygon_id
        self._next_custom_polygon_id += 1
        return str(pid)

    def next_object_id(self):
        """Return the next sequential object ID and increment counter."""
        oid = self._next_object_id
        self._next_object_id += 1
        return str(oid)

    def set_tool(self, tool_name):
        """Switch to the specified tool.

        Args:
            tool_name: Name of the tool ("select", "wall", or "room")
        """
        self.tool_manager.set_tool(tool_name)
        self.tool_changed.emit(tool_name)
            
    def _is_within_bounds(self, scene_pos):
        """Check if a scene position is within the background image bounds."""
        if self.background_item is None:
            return False
        return self.background_item.sceneBoundingRect().contains(scene_pos)

    def _create_input_context(self, event):
        """Create an InputContext from a QMouseEvent."""
        return InputContext(
            scene_pos=self.mapToScene(event.pos()),
            screen_pos=event.pos(),
            buttons=event.buttons(),
            modifiers=event.modifiers()
        )

    def update_background(self, image_data, origin, scale):
        """
        Updates the background image.

        Args:
            image_data: numpy array (grayscale)
            origin: (min_x, min_y, max_x, max_y) in world coords (meters)
            scale: pixels per meter

        Note:
            Scene coordinates are in meters (real-world coordinates).
            The background image is scaled and positioned to match real-world coordinates.
        """
        if image_data is None:
            return

        # Store original data for potential resize handling
        # CRITICAL: Make a copy of numpy array to prevent segfault
        import numpy as np
        self._background_data = np.copy(image_data)  # Deep copy!
        self._background_origin = origin
        self._background_scale = scale

        # Create QImage from numpy array
        # Use the copied data to prevent segfault when original is garbage collected
        height, width = self._background_data.shape
        bytes_per_line = width

        # Create QImage from copied data
        q_image = QImage(
            self._background_data.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_Grayscale8
        )
        # Make another copy to ensure QImage owns its data
        q_image = q_image.copy()
        pixmap = QPixmap.fromImage(q_image)

        # Remove old background if exists
        if self.background_item:
            self.scene.removeItem(self.background_item)

        # Create background item
        self.background_item = QGraphicsPixmapItem(pixmap)
        config = ConfigManager.instance()
        self.background_item.setZValue(config.get_ui_value("background", "z_value"))

        # Position and scale background to match real-world coordinates
        # origin = (min_x, min_y, max_x, max_y) in meters
        # Image width in meters = (max_x - min_x)
        # Image height in meters = (max_y - min_y)
        min_x, min_y, max_x, max_y = origin
        world_width = max_x - min_x
        world_height = max_y - min_y

        # Scale factor: pixels to meters
        # If image is 1000px and represents 10m, scale_x = 1000/10 = 100 px/m
        # QGraphicsItem scale should be meters/pixel = 1/scale
        scale_x = world_width / width
        scale_y = world_height / height

        self.background_item.setScale(1.0)  # Reset scale first
        self.background_item.setPos(min_x, min_y)
        self.background_item.setTransform(
            self.background_item.transform().scale(scale_x, scale_y)
        )

        self.scene.addItem(self.background_item)

        # Only set scene rect and fit view on first load; preserve zoom/pan on subsequent slices
        if not self._scene_initialized:
            margin = max(world_width, world_height) * 0.1
            self.scene.setSceneRect(
                min_x - margin,
                min_y - margin,
                world_width + 2 * margin,
                world_height + 2 * margin
            )
            self._user_has_zoomed = False
            self._fit_in_view_on_resize = True
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._scene_initialized = True
        
    def resizeEvent(self, event):
        """Handle window resize to maintain proper view of the scene.

        This ensures that real-world coordinates (meters) remain consistent
        regardless of window size changes.

        Note:
            If the user has manually zoomed, we preserve their zoom level.
            Press 'F' to reset view and re-enable auto-fit on resize.
        """
        super().resizeEvent(event)

        # Only auto-fit if user hasn't manually zoomed and scene is valid
        try:
            if self._fit_in_view_on_resize:
                rect = self.scene.sceneRect()
                if rect.isValid() and not rect.isEmpty() and rect.width() > 0 and rect.height() > 0:
                    self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            # Prevent crashes from fitInView failures
            print(f"Warning: fitInView failed in resizeEvent: {e}")

    def showEvent(self, event):
        """Handle initial show event to set up proper view."""
        super().showEvent(event)

        # Initial fit to view if scene has content
        try:
            rect = self.scene.sceneRect()
            if rect.isValid() and not rect.isEmpty() and rect.width() > 0 and rect.height() > 0:
                self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            # Prevent crashes from fitInView failures
            print(f"Warning: fitInView failed in showEvent: {e}")

    def wheelEvent(self, event):
        """Zoom with mouse wheel.

        Note:
            User zoom disables auto-fit on resize. Press 'F' to reset.
        """
        # Mark that user has manually zoomed
        self._user_has_zoomed = True
        self._fit_in_view_on_resize = False

        self.event_coordinator.handle_wheel(event)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        self.event_coordinator.handle_mouse_press(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        self.event_coordinator.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        self.event_coordinator.handle_mouse_release(event)
        super().mouseReleaseEvent(event)
        self._filter_rubberband_selection()

    def _filter_rubberband_selection(self):
        """Remove non-annotation and child items from rubber-band selection."""
        from src.gui.items import RoomItem, CustomPolygonItem, ObjectItem, EdgeItem, NodeItem
        VALID_TYPES = (RoomItem, CustomPolygonItem, ObjectItem, EdgeItem, NodeItem)
        for item in self.scene.selectedItems():
            if not isinstance(item, VALID_TYPES) or item.parentItem() is not None:
                item.setSelected(False)

    def keyPressEvent(self, event):
        """Handle keyboard events."""
        # Check for 'F' key to reset view
        if event.key() == Qt.Key.Key_F:
            self.reset_view()
            return

        handled = self.event_coordinator.handle_key_press(event)
        if handled:
            return
        super().keyPressEvent(event)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        self._draw_origin_axes(painter, rect)

    def _draw_origin_axes(self, painter, rect):
        """Draw X (red) and Y (green) axes through scene origin (0, 0)."""
        # Pen width stays visually thin regardless of zoom level
        scale = self.transform().m11()
        pen_width = 1.0 / scale if scale > 0 else 1.0

        config = ConfigManager.instance()
        painter.setPen(QPen(config.get_color("axes", "x"), pen_width))
        painter.drawLine(QPointF(rect.left(), 0.0), QPointF(rect.right(), 0.0))

        painter.setPen(QPen(config.get_color("axes", "y"), pen_width))
        painter.drawLine(QPointF(0.0, rect.top()), QPointF(0.0, rect.bottom()))

    def reset_view(self):
        """Reset view to fit entire scene.

        This re-enables auto-fit on resize and fits the current scene to view.
        """
        self._user_has_zoomed = False
        self._fit_in_view_on_resize = True

        if self.scene.sceneRect().isValid() and not self.scene.sceneRect().isEmpty():
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
    def copy_selection(self):
        """Copy selected items to clipboard."""
        self.clipboard_manager.copy_selection()

    def paste_clipboard(self):
        """Paste clipboard items."""
        self.clipboard_manager.paste_clipboard()

    def delete_selected_items(self):
        from src.gui.items import RoomItem, NodeItem, CustomPolygonItem, ObjectItem
        from src.core.undo_commands import DeleteItemCommand

        selected = self.scene.selectedItems()
        if not selected:
            return

        # Collect all items to delete
        items_to_delete = set(selected)
        for item in selected:
            if isinstance(item, (RoomItem, CustomPolygonItem)):
                for node in item.nodes:
                    items_to_delete.add(node)
                    for edge in list(node.edges):
                        items_to_delete.add(edge)
            elif isinstance(item, NodeItem):
                for edge in list(item.edges):
                    items_to_delete.add(edge)

        cmd = DeleteItemCommand(self.scene, list(items_to_delete), "Delete Items")
        self.push_command(cmd)

    def update_all_rooms(self):
        from src.gui.items import RoomItem
        for item in self.scene.items():
            if isinstance(item, RoomItem):
                item.update_style()
                item.update_overlay()

    def update_all_custom_polygons(self):
        from src.gui.items import CustomPolygonItem
        for item in self.scene.items():
            if isinstance(item, CustomPolygonItem):
                item.update_style()
                item.update_overlay()

    def update_all_objects(self):
        from src.gui.items import ObjectItem
        for item in self.scene.items():
            if isinstance(item, ObjectItem):
                item.update_style()

    def save_to_data(self):
        """Save canvas data to ProjectData format.

        Returns:
            ProjectData instance containing all walls and rooms
        """
        return self.data_serializer.save_to_data()

    def load_from_data(self, data):
        """Load canvas data from ProjectData format.

        Args:
            data: ProjectData instance to load
        """
        self.data_serializer.load_from_data(data)
