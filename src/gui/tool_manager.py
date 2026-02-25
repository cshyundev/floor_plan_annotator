"""Tool management for Canvas2D."""

from PyQt6.QtWidgets import QGraphicsView
from src.gui.tools import SelectTool, DrawWallTool, DrawRoomTool, DrawCustomPolygonTool, DrawObjectTool
from src.core.config import ConfigManager


class ToolManager:
    """Manages drawing tools for the canvas."""

    def __init__(self, canvas):
        """Initialize tool manager.

        Args:
            canvas: Canvas2D instance that owns these tools
        """
        self.canvas = canvas
        self._config = ConfigManager.instance()

        # Data-driven tool registry
        self._tools: dict = {
            "select": SelectTool(canvas),
            "wall": DrawWallTool(canvas),
            "room": DrawRoomTool(canvas),
            "custom_polygon": DrawCustomPolygonTool(canvas),
            "object": DrawObjectTool(canvas),
        }

        self.current_tool = self._tools["select"]

    # --- Backward-compatible properties ---

    @property
    def select_tool(self):
        return self._tools["select"]

    @property
    def wall_tool(self):
        return self._tools["wall"]

    @property
    def room_tool(self):
        return self._tools["room"]

    @property
    def custom_polygon_tool(self):
        return self._tools["custom_polygon"]

    @property
    def object_tool(self):
        return self._tools["object"]

    # --- Public API ---

    def register_tool(self, name: str, tool) -> None:
        """Register a new tool under the given name.

        Args:
            name: Tool identifier string
            tool: Tool instance (must implement on_mouse_press/move/release)
        """
        self._tools[name] = tool

    def set_tool(self, tool_name: str) -> None:
        """Switch to the specified tool.

        Args:
            tool_name: Name of the tool to activate
        """
        self._cleanup_current_tool()
        if tool_name in self._tools:
            self._activate_tool(tool_name)

    # --- Internal helpers ---

    def _cleanup_current_tool(self):
        """Clean up the current tool's transient state before switching."""
        tool = self.current_tool
        if hasattr(tool, 'cleanup'):
            tool.cleanup()
        elif hasattr(tool, 'current_start_node'):
            tool.current_start_node = None
        # Always clear snap guides when switching tools
        if hasattr(self.canvas, 'snap_manager'):
            self.canvas.snap_manager.clear_guides()

    def _activate_tool(self, name: str) -> None:
        """Activate a registered tool by name."""
        self.current_tool = self._tools[name]

        if name == "select":
            self.canvas.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.canvas.status_message.emit(
                self._config.get_string("tools", "select", "status")
            )
        else:
            self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
            if name == "wall":
                self.canvas.status_message.emit(
                    self._config.get_string("tools", "wall", "status")
                )
            elif name == "room":
                self.canvas.status_message.emit(
                    "Room Tool: Left Click to add points, Right Click to finish."
                )
            else:
                self.canvas.status_message.emit(f"{name.capitalize()} tool active.")
