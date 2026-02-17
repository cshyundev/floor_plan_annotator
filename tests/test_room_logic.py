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
    # Test Add
    key = "test_room"
    name = "Test Room"
    color = [100, 100, 100, 100]
    border = [50, 50, 50]
    
    # Ensure cleanup
    if key in config.get_room_types():
        config.delete_room_type(key)
        
    assert config.add_room_type(key, name, color, border) == True
    assert key in config.get_room_types()
    
    # Test Update
    new_name = "Updated Room"
    assert config.update_room_type(key, name=new_name) == True
    assert config.get_room_type(key)["name"] == new_name
    
    # Test Delete
    assert config.delete_room_type(key) == True
    assert key not in config.get_room_types()

def test_room_item_creation(qapp):
    nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10), NodeItem(0, 10)]
    room = RoomItem(nodes, room_type="living_room")
    assert room.room_type == "living_room"
    assert len(room.nodes) == 4

def test_change_room_type_command(qapp):
    nodes = [NodeItem(0, 0), NodeItem(10, 0), NodeItem(10, 10), NodeItem(0, 10)]
    room = RoomItem(nodes, room_type="living_room")
    
    cmd = ChangeRoomTypeCommand(room, "living_room", "kitchen")
    
    # Redo (Change to Kitchen)
    cmd.redo()
    assert room.room_type == "kitchen"
    
    # Undo (Revert to Living Room)
    cmd.undo()
    assert room.room_type == "living_room"

