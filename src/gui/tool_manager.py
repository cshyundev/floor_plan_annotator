"""Tool management for Canvas2D."""

from PyQt6.QtWidgets import QGraphicsView
from src.gui.tools import SelectTool, DrawWallTool, DrawRoomTool
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

        # Create tool instances
        self.select_tool = SelectTool(canvas)
        self.wall_tool = DrawWallTool(canvas)
        self.room_tool = DrawRoomTool(canvas)

        self.current_tool = self.select_tool

    def set_tool(self, tool_name):
        """Switch to the specified tool.

        Args:
            tool_name: Name of the tool ("select", "wall", or "room")
        """
        # Cleanup previous tool's temp state before switching
        self._cleanup_current_tool()

        if tool_name == "select":
            self._activate_select_tool()
        elif tool_name == "wall":
            self._activate_wall_tool()
        elif tool_name == "room":
            self._activate_room_tool()

    def _cleanup_current_tool(self):
        """Clean up the current tool before switching."""
        if self.current_tool == self.room_tool:
            self.room_tool.cleanup()
        elif self.current_tool == self.wall_tool:
            self.wall_tool.current_start_node = None

    def _activate_select_tool(self):
        """Activate the select tool."""
        self.current_tool = self.select_tool
        self.canvas.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.canvas.status_message.emit(
            self._config.get_string("tools", "select", "status")
        )

    def _activate_wall_tool(self):
        """Activate the wall drawing tool."""
        self.current_tool = self.wall_tool
        self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.canvas.status_message.emit(
            self._config.get_string("tools", "wall", "status")
        )

    def _activate_room_tool(self):
        """Activate the room drawing tool."""
        self.current_tool = self.room_tool
        self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.canvas.status_message.emit(
            "Room Tool: Left Click to add points, Right Click to finish."
        )
