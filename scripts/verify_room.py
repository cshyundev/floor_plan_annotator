from PyQt6.QtWidgets import QApplication, QGraphicsScene
from src.gui.items import NodeItem, RoomItem
from src.core.config import ConfigManager
import sys

# Mock App
app = QApplication(sys.argv)
config = ConfigManager.instance()

# Check Config
print("Checking Room Config...")
types = config.get_value("rooms", "types")
assert "Living Room" in types
print(f"Room Types Found: {list(types.keys())}")

# Check RoomItem
print("Checking RoomItem...")
scene = QGraphicsScene()
n1 = NodeItem(0, 0)
n2 = NodeItem(100, 0)
n3 = NodeItem(100, 100)
nodes = [n1, n2, n3]
for n in nodes:
    scene.addItem(n)

room = RoomItem(nodes, room_type="Living Room", room_id="test_123")
scene.addItem(room)

# Check Visuals
print(f"Room Label: {room.get_label_text()}")
assert "Living Room" in room.get_label_text()

# Check Move Logic using setPos (simulates interaction)
print("Moving Node 1...")
n1.setPos(-50, -50)
path = room.path()
bounds = path.boundingRect()
print(f"Room Bounds: {bounds}")
assert bounds.contains(-50, -50)

# Check Undo Command (Manually Mocking)
from src.core.undo_commands import MoveNodesCommand
from PyQt6.QtGui import QUndoStack
from PyQt6.QtCore import QPointF

stack = QUndoStack()
# Assume interaction created this command
# Store initial state before move
initial_pos = [QPointF(0, 0), QPointF(100, 0), QPointF(100, 100)]
final_pos = [QPointF(-50, -50), QPointF(100, 0), QPointF(100, 100)]
cmd = MoveNodesCommand(nodes, initial_pos, final_pos)

print("Pushing Undo Command...")
stack.push(cmd) # This calls redo(), setting neg positions
assert n1.pos() == QPointF(-50, -50)

print("Undoing...")
stack.undo() # Should return to 0,0
print(f"Node 1 Pos: {n1.pos()}")
assert n1.pos() == QPointF(0, 0)

print("Redoing...")
stack.redo()
assert n1.pos() == QPointF(-50, -50)

print("Verification Passed!")
