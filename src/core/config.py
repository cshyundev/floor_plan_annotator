
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
        self.ui_config = {}
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
        self.ui_config = load_yaml("ui_config.yaml")
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
            # First try colors.yaml, then fall back to ui_config.yaml
            # This maintains backward compatibility as UI settings were moved from colors to ui_config
            val = self._get_value(self.colors, keys)
            if val is None:
                val = self._get_value(self.ui_config, keys)
            return val
        elif category == "ui_config":
            return self._get_value(self.ui_config, keys)
        elif category == "shortcuts":
             return self._get_value(self.shortcuts, keys)
        elif category == "rooms":
             return self._get_value(self.rooms, keys)
        return None

    def get_room_type(self, type_key):
        return self._get_value(self.rooms, ["types", type_key])

    def save_config(self, category):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_dir = os.path.join(project_root, "config")
            
            if category == "rooms":
                path = os.path.join(config_dir, "rooms.yaml")
                with open(path, 'w') as f:
                    yaml.dump(self.rooms, f, sort_keys=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def add_room_type(self, key, name, color, border):
        if key in self.rooms.get("types", {}):
            return False
            
        if "types" not in self.rooms:
            self.rooms["types"] = {}
            
        # Auto index
        max_idx = 0
        for k, v in self.rooms["types"].items():
             max_idx = max(max_idx, v.get("index", 0))
             
        self.rooms["types"][key] = {
            "name": name,
            "color": color,
            "border": border,
            "index": max_idx + 1
        }
        self.save_config("rooms")
        return True

    def update_room_type(self, key, name=None, color=None, border=None):
        if key not in self.rooms.get("types", {}):
            return False
            
        if name: self.rooms["types"][key]["name"] = name
        if color: self.rooms["types"][key]["color"] = color
        if border: self.rooms["types"][key]["border"] = border
        
        self.save_config("rooms")
        return True

    def delete_room_type(self, key):
        if key not in self.rooms.get("types", {}):
            return False
            
        del self.rooms["types"][key]
        self.save_config("rooms")
        return True

    def get_room_types(self):
        return self.rooms.get("types", {})

    def _get_value(self, data, keys):
        curr = data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr
