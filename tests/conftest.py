"""
Shared fixtures for E2E / functional tests.

All E2E tests use REAL components (Canvas2D, ToolManager, EventCoordinator,
tools, items, undo stack). Only modal popups are stubbed.

Run: QT_QPA_PLATFORM=offscreen python3 -m pytest tests/e2e/ -v
"""
import os
from unittest.mock import patch

import numpy as np
import pytest
from PyQt6.QtCore import QPointF, QPoint, Qt
from PyQt6.QtGui import QUndoStack

from src.gui.canvas_2d import Canvas2D
from src.core.input_context import InputContext
from src.gui.items import NodeItem, EdgeItem, RoomItem, CustomPolygonItem, ObjectItem


# ---------------------------------------------------------------------------
# QApplication — ensure offscreen platform before any Qt objects
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def ensure_offscreen():
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def undo_stack():
    return QUndoStack()


@pytest.fixture
def canvas(qtbot, undo_stack):
    """Fully wired Canvas2D with undo stack and dummy background (0-10m)."""
    c = Canvas2D()
    c.set_undo_stack(undo_stack)
    img = np.zeros((500, 500), dtype=np.uint8)
    c.update_background(img, (0.0, 0.0, 10.0, 10.0), 50.0)
    qtbot.addWidget(c)
    c.show()
    qtbot.waitExposed(c)
    return c


# ---------------------------------------------------------------------------
# Helper: InputContext factory
# ---------------------------------------------------------------------------
def make_context(x, y, buttons=Qt.MouseButton.LeftButton,
                 modifiers=Qt.KeyboardModifier.NoModifier):
    """Create an InputContext with scene coordinates (meters)."""
    return InputContext(
        scene_pos=QPointF(x, y),
        screen_pos=QPoint(int(x * 50), int(y * 50)),
        buttons=buttons,
        modifiers=modifiers,
    )


# ---------------------------------------------------------------------------
# Helper: scene item queries
# ---------------------------------------------------------------------------
def items_of_type(canvas, item_type):
    return [i for i in canvas.scene.items() if isinstance(i, item_type)]


def annotation_items(canvas):
    return [i for i in canvas.scene.items() if i is not canvas.background_item]


# ---------------------------------------------------------------------------
# Helper: draw actions
# ---------------------------------------------------------------------------
def draw_wall(canvas, x1, y1, x2, y2):
    """Draw a single wall segment. Wall tool uses on_mouse_press for both clicks."""
    canvas.set_tool("wall")
    tool = canvas.tool_manager.wall_tool
    tool.on_mouse_press(make_context(x1, y1))
    tool.on_mouse_press(make_context(x2, y2))
    canvas.set_tool("select")


def draw_room(canvas, points, room_type="living_room"):
    """Draw a room polygon. Mocks _select_room_type to avoid modal dialog."""
    canvas.set_tool("room")
    tool = canvas.tool_manager.room_tool

    for x, y in points:
        ctx = make_context(x, y)
        tool.on_mouse_press(ctx)
        tool.on_mouse_release(ctx)

    # Right-click to finish (>= 3 nodes triggers _finish_polygon via _handle_right_click)
    with patch.object(tool, "_select_room_type", return_value=room_type):
        tool.on_mouse_press(make_context(0, 0, buttons=Qt.MouseButton.RightButton))

    canvas.set_tool("select")


def draw_custom_polygon(canvas, points, polygon_type="clean_zone"):
    """Draw a custom polygon. Mocks _select_custom_polygon_type."""
    canvas.set_tool("custom_polygon")
    tool = canvas.tool_manager.custom_polygon_tool

    for x, y in points:
        ctx = make_context(x, y)
        tool.on_mouse_press(ctx)
        tool.on_mouse_release(ctx)

    with patch.object(tool, "_select_custom_polygon_type", return_value=polygon_type):
        tool.on_mouse_press(make_context(0, 0, buttons=Qt.MouseButton.RightButton))

    canvas.set_tool("select")


def draw_object(canvas, x1, y1, x2, y2, object_type="furniture"):
    """Draw an object via click-drag. Mocks _select_object_type."""
    canvas.set_tool("object")
    tool = canvas.tool_manager.object_tool

    tool.on_mouse_press(make_context(x1, y1))
    tool.on_mouse_move(make_context(x2, y2))

    with patch.object(tool, "_select_object_type", return_value=object_type):
        tool.on_mouse_release(make_context(x2, y2))

    canvas.set_tool("select")


# ---------------------------------------------------------------------------
# Helper: selection & keyboard
# ---------------------------------------------------------------------------
def select_item(canvas, item):
    canvas.scene.clearSelection()
    item.setSelected(True)


def press_key(canvas, key, modifiers=Qt.KeyboardModifier.NoModifier):
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent
    event = QKeyEvent(QEvent.Type.KeyPress, key, modifiers)
    canvas.keyPressEvent(event)
