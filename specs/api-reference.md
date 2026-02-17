# API Reference

## Core Modules

### src.core.processor

#### SliceEngine

Point cloud processing and slicing engine.

```python
class SliceEngine:
    def __init__(self)
```

**Methods:**

##### load_data(pcd)
Loads Open3D PointCloud data.

**Parameters:**
- `pcd` (open3d.geometry.PointCloud): Point cloud object

**Returns:** None

---

##### get_z_range()
Gets the minimum and maximum Z coordinates of the loaded point cloud.

**Returns:** `tuple[float, float]` - (min_z, max_z)

---

##### slice_at_height(z_height, thickness=0.1)
Slices the point cloud at a given z_height with a certain thickness.

**Parameters:**
- `z_height` (float): Target height on Z-axis
- `thickness` (float): Thickness of the slice (default: 0.1)

**Returns:** `tuple[np.ndarray, np.ndarray]` - (points, colors)
- `points`: Nx3 numpy array of points within the slice
- `colors`: Nx3 numpy array of colors

---

##### project_to_image(points, pixel_size=0.01, padding=10)
Projects 3D points to a 2D density map / image.

**Parameters:**
- `points` (np.ndarray): Nx3 array of 3D points
- `pixel_size` (float): Size of one pixel in meters (default: 0.01)
- `padding` (int): Padding around the image in pixels (default: 10)

**Returns:** `tuple[np.ndarray, tuple, float]` - (image, bounds, scale)
- `image`: 2D numpy array (grayscale image)
- `bounds`: (min_x, min_y, max_x, max_y) in world coordinates
- `scale`: pixels per meter

---

### src.core.io

#### ProjectIO

Static methods for project file I/O operations.

```python
class ProjectIO:
    @staticmethod
    def save_project(project_data: ProjectData, file_path: str) -> None

    @staticmethod
    def load_project(file_path: str) -> ProjectData
```

**Methods:**

##### save_project(project_data, file_path)
Saves project data to JSON file.

**Parameters:**
- `project_data` (ProjectData): Project data to save
- `file_path` (str): Target file path

**Raises:** `IOError` if file cannot be written

---

##### load_project(file_path)
Loads project data from JSON file.

**Parameters:**
- `file_path` (str): Source file path

**Returns:** `ProjectData` - Loaded project data

**Raises:** `IOError` if file cannot be read, `ValueError` if JSON is invalid

---

### src.core.config

#### ConfigManager

Singleton configuration manager for YAML settings.

```python
class ConfigManager:
    @staticmethod
    def instance() -> ConfigManager

    def get_string(self, section: str, key: str, default: str = "") -> str

    def get_shortcut(self, section: str, key: str) -> str | None
```

**Methods:**

##### instance()
Gets the singleton instance.

**Returns:** `ConfigManager` - The singleton instance

---

##### get_string(section, key, default="")
Gets a string value from configuration.

**Parameters:**
- `section` (str): Configuration section
- `key` (str): Configuration key
- `default` (str): Default value if not found

**Returns:** `str` - Configuration value

---

##### get_shortcut(section, key)
Gets a keyboard shortcut from configuration.

**Parameters:**
- `section` (str): Configuration section
- `key` (str): Configuration key

**Returns:** `str | None` - Keyboard shortcut or None

---

## Data Models

### src.model.data

#### Point2D

2D coordinate representation.

```python
@dataclass
class Point2D:
    x: float
    y: float

    def to_tuple(self) -> tuple[float, float]

    @staticmethod
    def from_tuple(t: tuple[float, float]) -> Point2D
```

---

#### AnnotationBase

Base class for all annotations.

```python
@dataclass
class AnnotationBase:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = "default"
    z_min: float = 0.0
    z_max: float = 2.5

    def to_dict(self) -> dict
```

---

#### Wall

Wall annotation (line segment).

```python
@dataclass
class Wall(AnnotationBase):
    start: Point2D = field(default_factory=lambda: Point2D(0,0))
    end: Point2D = field(default_factory=lambda: Point2D(0,0))
    thickness: float = 0.1

    def to_dict(self) -> dict

    @staticmethod
    def from_dict(d: dict) -> Wall
```

---

#### Room

Room annotation (polygon).

```python
@dataclass
class Room(AnnotationBase):
    points: List[Point2D] = field(default_factory=list)
    name: str = "Room"
    room_type: str = "default"

    def to_dict(self) -> dict

    @staticmethod
    def from_dict(d: dict) -> Room
```

---

#### Object

Object annotation (bounding box).

```python
@dataclass
class Object(AnnotationBase):
    center: Point2D = field(default_factory=lambda: Point2D(0,0))
    width: float = 1.0
    height: float = 1.0
    rotation: float = 0.0
```

---

#### ProjectData

Complete project data structure.

```python
@dataclass
class ProjectData:
    walls: List[Wall] = field(default_factory=list)
    rooms: List[Room] = field(default_factory=list)
    objects: List[Object] = field(default_factory=list)
    version: str = "1.0"

    def to_dict(self) -> dict

    @staticmethod
    def from_dict(d: dict) -> ProjectData
```

---

## GUI Components

### src.gui.main_window

#### MainWindow

Main application window.

```python
class MainWindow(QMainWindow):
    def __init__(self)

    def load_point_cloud(self) -> None
    def save_project(self) -> None
    def open_project(self) -> None
    def on_slider_change(self, value: int) -> None
    def update_slice(self) -> None
```

**Key Attributes:**
- `viewer_3d` (Viewer3D): 3D point cloud viewer
- `canvas_2d` (Canvas2D): 2D annotation canvas
- `processor` (SliceEngine): Point cloud processor
- `undo_stack` (QUndoStack): Undo/redo stack
- `current_z` (float): Current slice height

---

### src.gui.viewer_3d

#### Viewer3D

3D point cloud visualization widget.

```python
class Viewer3D(QWidget):
    def load_geometry(self, file_path: str) -> None
    def update_slice_plane(self, z_height: float) -> None
```

**Attributes:**
- `geometry` (open3d.geometry.PointCloud): Loaded point cloud

---

### src.gui.canvas_2d

#### Canvas2D

2D annotation canvas.

```python
class Canvas2D(QGraphicsView):
    status_message = pyqtSignal(str)

    def set_undo_stack(self, stack: QUndoStack) -> None
    def set_tool(self, tool_name: str) -> None
    def update_background(self, image: np.ndarray, bounds: tuple, scale: float) -> None
    def save_to_data(self) -> ProjectData
    def load_from_data(self, project_data: ProjectData) -> None
```

**Key Methods:**

##### set_tool(tool_name)
Sets the active drawing tool.

**Parameters:**
- `tool_name` (str): Tool name ("select", "wall", "room")

---

##### update_background(image, bounds, scale)
Updates the background image from point cloud projection.

**Parameters:**
- `image` (np.ndarray): Grayscale image array
- `bounds` (tuple): (min_x, min_y, max_x, max_y) in world coordinates
- `scale` (float): Pixels per meter

---

##### save_to_data()
Exports current annotations to ProjectData.

**Returns:** `ProjectData` - Current project state

---

##### load_from_data(project_data)
Imports annotations from ProjectData.

**Parameters:**
- `project_data` (ProjectData): Project data to load

---

### src.gui.items

#### WallItem

Graphics item representing a wall.

```python
class WallItem(QGraphicsItem):
    def __init__(self, wall: Wall)

    def set_selected(self, selected: bool) -> None
    def get_wall(self) -> Wall
```

---

#### RoomItem

Graphics item representing a room.

```python
class RoomItem(QGraphicsItem):
    def __init__(self, room: Room)

    def set_selected(self, selected: bool) -> None
    def get_room(self) -> Room
```

---

### src.gui.tools

#### Tool (Abstract Base)

Base class for drawing tools.

```python
class Tool:
    def mouse_press(self, event: QGraphicsSceneMouseEvent) -> None
    def mouse_move(self, event: QGraphicsSceneMouseEvent) -> None
    def mouse_release(self, event: QGraphicsSceneMouseEvent) -> None
    def activate(self) -> None
    def deactivate(self) -> None
```

---

#### SelectTool

Selection and manipulation tool.

```python
class SelectTool(Tool):
    pass
```

---

#### WallTool

Wall drawing tool.

```python
class WallTool(Tool):
    pass
```

**Usage:**
1. Click to set start point
2. Move mouse to preview
3. Click to set end point and create wall

---

#### RoomTool

Room (polygon) drawing tool.

```python
class RoomTool(Tool):
    pass
```

**Usage:**
1. Click to add vertices
2. Double-click or press Enter to close polygon
3. Esc to cancel

---

## Undo Commands

### src.core.undo_commands

#### AddItemCommand

Command for adding a new annotation.

```python
class AddItemCommand(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, item: QGraphicsItem)

    def undo(self) -> None
    def redo(self) -> None
```

---

#### MoveItemCommand

Command for moving an annotation.

```python
class MoveItemCommand(QUndoCommand):
    def __init__(self, item: QGraphicsItem, old_pos: QPointF, new_pos: QPointF)

    def undo(self) -> None
    def redo(self) -> None
```

---

#### DeleteItemCommand

Command for deleting an annotation.

```python
class DeleteItemCommand(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, item: QGraphicsItem)

    def undo(self) -> None
    def redo(self) -> None
```

---

## Configuration File Format

### config.yaml

```yaml
window:
  title: "Floor Plan Annotator"

menu:
  file: "File"
  load_point_cloud: "Load Point Cloud..."
  open_project: "Open Project..."
  save_project: "Save Project..."
  exit: "Exit"

labels:
  controls_dock: "Controls"
  slice_height: "Slice Height"
  z_value: "Z = {:.2f} m"
  toolbar: "Tools"

undo:
  undo: "Undo"
  redo: "Redo"

shortcuts:
  file:
    open_project: "Ctrl+O"
    save_project: "Ctrl+S"

  edit:
    undo: "Ctrl+Z"
    redo: "Ctrl+Y"

  tools:
    select: "Esc"
    wall: "W"
    rect: "R"
```

---

## Project File Format

### project.json

```json
{
  "version": "1.0",
  "walls": [
    {
      "id": "uuid-string",
      "category": "default",
      "z_min": 0.0,
      "z_max": 2.5,
      "start": {"x": 0.0, "y": 0.0},
      "end": {"x": 5.0, "y": 0.0},
      "thickness": 0.15
    }
  ],
  "rooms": [
    {
      "id": "uuid-string",
      "category": "default",
      "z_min": 0.0,
      "z_max": 2.5,
      "points": [
        {"x": 0.0, "y": 0.0},
        {"x": 5.0, "y": 0.0},
        {"x": 5.0, "y": 4.0},
        {"x": 0.0, "y": 4.0}
      ],
      "name": "Living Room",
      "room_type": "living"
    }
  ],
  "objects": []
}
```
