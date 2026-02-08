from PyQt6.QtCore import QPointF, QPoint, Qt

class InputContext:
    """
    Encapsulates input state for tools, decoupling them from raw Qt events.
    """
    def __init__(self, 
                 scene_pos: QPointF, 
                 screen_pos: QPoint, 
                 buttons: Qt.MouseButton = Qt.MouseButton.NoButton, 
                 modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
                 delta: int = 0):
        self.scene_pos = scene_pos
        self.screen_pos = screen_pos
        self.buttons = buttons
        self.modifiers = modifiers
        self.delta = delta # For wheel events
