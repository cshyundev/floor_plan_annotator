from PyQt6.QtGui import QUndoCommand
from PyQt6.QtCore import QPointF
# Imports for type hinting if needed, but avoiding circular deps if they exist
# from src.gui.items import NodeItem 

class AddItemCommand(QUndoCommand):
    def __init__(self, scene, items, description="Add Items"):
        super().__init__()
        self.setText(description)
        self.scene = scene
        self.items = items
        
    def redo(self):
        for item in self.items:
            if item.scene() != self.scene:
                self.scene.addItem(item)
            
    def undo(self):
        for item in self.items:
            if item.scene() == self.scene:
                self.scene.removeItem(item)

class DeleteItemCommand(QUndoCommand):
    def __init__(self, scene, items, description="Delete Items"):
        super().__init__()
        self.setText(description)
        self.scene = scene
        self.items = items
        
    def redo(self):
        for item in self.items:
            if item.scene() == self.scene:
                self.scene.removeItem(item)
                
    def undo(self):
        for item in self.items:
            if item.scene() != self.scene:
                self.scene.addItem(item)

class MoveNodeCommand(QUndoCommand):
    def __init__(self, node, old_pos: QPointF, new_pos: QPointF):
        super().__init__()
        self.setText("Move Node")
        self.node = node
        self.old_pos = old_pos
        self.new_pos = new_pos
        
    def redo(self):
        self.node.setPos(self.new_pos)
        
    def undo(self):
        self.node.setPos(self.old_pos)

class MoveNodesCommand(QUndoCommand):
    def __init__(self, nodes, old_positions, new_positions):
        super().__init__(f"Move {len(nodes)} Nodes")
        self.nodes = nodes
        self.old_positions = old_positions
        self.new_positions = new_positions

    def undo(self):
        for i, node in enumerate(self.nodes):
            node.setPos(self.old_positions[i])

    def redo(self):
        for i, node in enumerate(self.nodes):
            node.setPos(self.new_positions[i])
