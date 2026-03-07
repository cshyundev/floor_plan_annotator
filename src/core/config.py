
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
        self.custom_polygons = {}
        self.objects = {}
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
        self.custom_polygons = load_yaml("custom_polygons.yaml")
        self.objects = load_yaml("objects.yaml")

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
        elif category == "ui_config":
            return self._get_value(self.ui_config, keys)
        elif category == "shortcuts":
             return self._get_value(self.shortcuts, keys)
        elif category == "rooms":
             return self._get_value(self.rooms, keys)
        elif category == "custom_polygons":
             return self._get_value(self.custom_polygons, keys)
        elif category == "objects":
             return self._get_value(self.objects, keys)
        return None

    def get_ui_value(self, *keys):
        """Shorthand for get_value('ui_config', *keys). Raises KeyError if not found."""
        val = self._get_value(self.ui_config, keys)
        if val is None:
            raise KeyError(f"ui_config key not found: {'.'.join(str(k) for k in keys)}")
        return val

    def get_room_type(self, type_key):
        return self._get_value(self.rooms, ["types", type_key])

    def get_custom_polygon_type(self, type_key):
        return self._get_value(self.custom_polygons, ["types", type_key])

    def get_custom_polygon_types(self):
        return self.custom_polygons.get("types", {})

    def get_object_type(self, type_key):
        return self._get_value(self.objects, ["types", type_key])

    def get_object_types(self):
        return self.objects.get("types", {})

    def get_object_3d_defaults(self, type_key):
        """Return (elevation, height_3d) for the given object type."""
        type_conf = self.get_object_type(type_key)
        fallback_height = self.get_ui_value("annotation_3d", "object_height")
        if type_conf:
            elevation = type_conf.get("default_elevation", 0.0)
            height_3d = type_conf.get("default_3d_height", fallback_height)
        else:
            elevation = 0.0
            height_3d = fallback_height
        return elevation, height_3d

    def save_config(self, category):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_dir = os.path.join(project_root, "config")

            if category == "rooms":
                path = os.path.join(config_dir, "rooms.yaml")
                with open(path, 'w') as f:
                    yaml.dump(self.rooms, f, sort_keys=False)
            elif category == "custom_polygons":
                path = os.path.join(config_dir, "custom_polygons.yaml")
                with open(path, 'w') as f:
                    yaml.dump(self.custom_polygons, f, sort_keys=False)
            elif category == "objects":
                path = os.path.join(config_dir, "objects.yaml")
                with open(path, 'w') as f:
                    yaml.dump(self.objects, f, sort_keys=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def add_custom_polygon_type(self, key, color, border):
        if key in self.custom_polygons.get("types", {}):
            return False
        if "types" not in self.custom_polygons:
            self.custom_polygons["types"] = {}
        max_idx = max((v.get("index", 0) for v in self.custom_polygons["types"].values()), default=0)
        self.custom_polygons["types"][key] = {
            "color": color, "border": border, "index": max_idx + 1
        }
        self.save_config("custom_polygons")
        return True

    def update_custom_polygon_type(self, key, color=None, border=None):
        if key not in self.custom_polygons.get("types", {}):
            return False
        if color: self.custom_polygons["types"][key]["color"] = color
        if border: self.custom_polygons["types"][key]["border"] = border
        self.save_config("custom_polygons")
        return True

    def rename_custom_polygon_type(self, old_key, new_key):
        types = self.custom_polygons.get("types", {})
        if old_key not in types or new_key in types:
            return False
        types[new_key] = types.pop(old_key)
        if self.custom_polygons.get("default_type") == old_key:
            self.custom_polygons["default_type"] = new_key
        self.save_config("custom_polygons")
        return True

    def delete_custom_polygon_type(self, key):
        if key not in self.custom_polygons.get("types", {}):
            return False
        del self.custom_polygons["types"][key]
        self.save_config("custom_polygons")
        return True

    def add_object_type(self, key, color, border,
                        default_elevation=0.0, default_3d_height=0.5):
        if key in self.objects.get("types", {}):
            return False
        if "types" not in self.objects:
            self.objects["types"] = {}
        max_idx = max((v.get("index", 0) for v in self.objects["types"].values()), default=0)
        self.objects["types"][key] = {
            "color": color, "border": border, "index": max_idx + 1,
            "default_elevation": default_elevation, "default_3d_height": default_3d_height,
        }
        self.save_config("objects")
        return True

    def update_object_type(self, key, color=None, border=None,
                           default_elevation=None, default_3d_height=None):
        if key not in self.objects.get("types", {}):
            return False
        if color: self.objects["types"][key]["color"] = color
        if border: self.objects["types"][key]["border"] = border
        if default_elevation is not None:
            self.objects["types"][key]["default_elevation"] = default_elevation
        if default_3d_height is not None:
            self.objects["types"][key]["default_3d_height"] = default_3d_height
        self.save_config("objects")
        return True

    def rename_object_type(self, old_key, new_key):
        types = self.objects.get("types", {})
        if old_key not in types or new_key in types:
            return False
        types[new_key] = types.pop(old_key)
        if self.objects.get("default_type") == old_key:
            self.objects["default_type"] = new_key
        self.save_config("objects")
        return True

    def delete_object_type(self, key):
        if key not in self.objects.get("types", {}):
            return False
        del self.objects["types"][key]
        self.save_config("objects")
        return True

    def add_room_type(self, key, color, border):
        if key in self.rooms.get("types", {}):
            return False

        if "types" not in self.rooms:
            self.rooms["types"] = {}

        max_idx = max((v.get("index", 0) for v in self.rooms["types"].values()), default=0)

        self.rooms["types"][key] = {
            "color": color,
            "border": border,
            "index": max_idx + 1
        }
        self.save_config("rooms")
        return True

    def update_room_type(self, key, color=None, border=None):
        if key not in self.rooms.get("types", {}):
            return False

        if color: self.rooms["types"][key]["color"] = color
        if border: self.rooms["types"][key]["border"] = border

        self.save_config("rooms")
        return True

    def rename_room_type(self, old_key, new_key):
        types = self.rooms.get("types", {})
        if old_key not in types or new_key in types:
            return False
        types[new_key] = types.pop(old_key)
        if self.rooms.get("default_type") == old_key:
            self.rooms["default_type"] = new_key
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


def apply_theme(app, theme_path=None):
    """Apply QSS theme stylesheet to QApplication."""
    if theme_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        theme_path = os.path.join(project_root, "config", "theme.qss")
    if os.path.exists(theme_path):
        try:
            with open(theme_path, 'r') as f:
                qss = f.read()
            app.setStyleSheet(qss)
        except Exception as e:
            print(f"Warning: Failed to load theme: {e}")
