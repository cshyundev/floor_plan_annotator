from src.core.config import ConfigManager
import os

# Create instance
config = ConfigManager.instance()

# Check shortcuts
print(f"Select: {config.get_shortcut('tools', 'select')}")
print(f"Wall: {config.get_shortcut('tools', 'wall')}")
print(f"Rect: {config.get_shortcut('tools', 'rect')}")

assert config.get_shortcut('tools', 'select') == "Esc"
assert config.get_shortcut('tools', 'wall') == "W"
assert config.get_shortcut('tools', 'rect') == "R"
print("Verification Passed!")
