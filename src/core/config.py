
import yaml
import os
from PyQt6.QtGui import QColor

class ConfigManager:
    _instance = None
    
    @staticmethod
    def instance():
        if ConfigManager._instance is None:
            ConfigManager._instance = ConfigManager()
        return ConfigManager._instance

    def __init__(self):
        self.colors = {}
        self.strings = {}
        self.shortcuts = {}
        self.rooms = {}
        self.load_configs()
        
    def load_configs(self):
        # Determine config path relative to project root
        # Assuming src/core/config.py location, go up 2 levels
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        config_dir = os.path.join(project_root, "config")
        
        def load_yaml(filename):
            path = os.path.join(config_dir, filename)
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
            else:
                print(f"Config file not found: {path}")
            return {}

        self.colors = load_yaml("colors.yaml")
        self.strings = load_yaml("strings.yaml")
        self.shortcuts = load_yaml("shortcuts.yaml")
        self.rooms = load_yaml("rooms.yaml")

    def get_color(self, *keys):
        val = self._get_value(self.colors, keys)
        if val:
            if isinstance(val, list):
                if len(val) == 3:
                     return QColor(val[0], val[1], val[2])
                elif len(val) == 4:
                     return QColor(val[0], val[1], val[2], val[3])
            elif isinstance(val, str):
                return QColor(val)
        return QColor(255, 0, 255) # Fallback Magenta
    
    def get_string(self, *keys):
        """
        Retrieve string from config.
        Usage: get_string("window", "title")
        """
        val = self._get_value(self.strings, keys)
        return str(val) if val is not None else "???"

    def get_shortcut(self, *keys):
        """
        Retrieve shortcut string.
        """
        return self._get_value(self.shortcuts, keys)

    def get_value(self, category, *keys):
        if category == "colors":
            return self._get_value(self.colors, keys)
        elif category == "shortcuts":
             return self._get_value(self.shortcuts, keys)
        elif category == "rooms":
             return self._get_value(self.rooms, keys)
        return None

    def get_room_type(self, type_key):
        return self._get_value(self.rooms, ["types", type_key])

    def _get_value(self, data, keys):
        curr = data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr
