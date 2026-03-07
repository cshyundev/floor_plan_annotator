import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF
from src.gui.items import RoomItem, NodeItem
from src.core.config import ConfigManager
from src.core.undo_commands import ChangeRoomTypeCommand

# Fixture for QApplication
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def config():
    return ConfigManager.instance()

def test_config_manager_room_types(config):
    # Test Add (name=key, no separate name parameter)
    key = "Test Room Type"
    color = [100, 100, 100, 100]
    border = [50, 50, 50]

    # Ensure cleanup
    if key in config.get_room_types():
        config.delete_room_type(key)

    assert config.add_room_type(key, color, border) == True
    assert key in config.get_room_types()

    # Test Rename
    new_key = "Updated Room Type"
    if new_key in config.get_room_types():
        config.delete_room_type(new_key)
    assert config.rename_room_type(key, new_key) == True
    assert new_key in config.get_room_types()
    assert key not in config.get_room_types()

    # Test Delete
    assert config.delete_room_type(new_key) == True
    assert new_key not in config.get_room_types()

def test_room_item_creation(qapp):
    nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10), NodeItem(0, 10)]
    room = RoomItem(nodes, room_type="Living Room")
    assert room.room_type == "Living Room"
    assert len(room.nodes) == 4

def test_change_room_type_command(qapp):
    nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10), NodeItem(0, 10)]
    room = RoomItem(nodes, room_type="Living Room")

    cmd = ChangeRoomTypeCommand(room, "Living Room", "Kitchen")

    # Redo (Change to Kitchen)
    cmd.redo()
    assert room.room_type == "Kitchen"

    # Undo (Revert to Living Room)
    cmd.undo()
    assert room.room_type == "Living Room"
