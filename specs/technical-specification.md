# Technical Specification

## System Architecture

The Floor Plan Annotator follows a layered architecture pattern:

```
┌─────────────────────────────────────┐
│        Presentation Layer           │
│   (PyQt6 GUI Components)            │
│  - MainWindow, Viewer3D, Canvas2D   │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│         Business Logic Layer        │
│   - SliceEngine (Processor)         │
│   - ConfigManager                   │
│   - UndoCommands                    │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│          Data Layer                 │
│   - Annotation Models (Wall, Room)  │
│   - ProjectIO                       │
└─────────────────────────────────────┘
```

## Core Components

### 1. GUI Layer (`src/gui/`)

#### MainWindow
- Central application window with menu bar, toolbar, and status bar
- Manages dual-view layout using QSplitter
- Coordinates communication between 3D viewer and 2D canvas
- Handles file operations (load point cloud, save/load project)

#### Viewer3D
- 3D point cloud visualization using Open3D
- Interactive camera controls (rotate, pan, zoom)
- Displays slice plane indicator at current height
- Supports various point cloud file formats

#### Canvas2D
- QGraphicsView-based 2D canvas for annotation
- Displays projected point cloud as background image
- Manages annotation items (walls, rooms) as QGraphicsItems
- Implements coordinate transformations (world ↔ screen)
- Emits signals for status updates and user interactions

#### Items (Graphics Items)
- WallItem: Line segment with handles for editing
- RoomItem: Polygon with vertex handles for editing
- Interactive selection, movement, and modification
- Visual feedback (hover, selection state)

#### Tools
- SelectTool: Select and manipulate existing annotations
- WallTool: Draw walls by clicking start and end points
- RoomTool: Draw room polygons by clicking vertices
- Tool-specific cursor and visual feedback

### 2. Business Logic Layer (`src/core/`)

#### SliceEngine (processor.py)
Point cloud processing and slicing engine.

**Key Methods:**
- `load_data(pcd)`: Load Open3D point cloud
- `get_z_range()`: Get min/max Z coordinates
- `slice_at_height(z, thickness)`: Extract points within Z range
- `project_to_image(points, pixel_size)`: Generate 2D density map

**Algorithm:**
1. Filter points by Z-axis range: `z_min ≤ z ≤ z_max`
2. Project to 2D: `(x, y)` coordinates
3. Rasterize to pixel grid with configurable resolution
4. Apply morphological dilation for clearer visualization
5. Return image with bounds and scale for coordinate mapping

#### ConfigManager (config.py)
Singleton configuration manager for YAML settings.

**Responsibilities:**
- Load configuration from YAML files
- Provide type-safe accessors (get_string, get_shortcut)
- Centralized configuration access throughout application

#### UndoCommands (undo_commands.py)
Command pattern implementation for undo/redo.

**Command Types:**
- AddItemCommand: Add new annotation
- MoveItemCommand: Move annotation
- DeleteItemCommand: Delete annotation
- ModifyItemCommand: Modify annotation properties

Each command implements `undo()` and `redo()` methods.

#### ProjectIO (io.py)
Handles serialization and deserialization of project files.

**Format:** JSON with the following structure:
```json
{
  "version": "1.0",
  "walls": [...],
  "rooms": [...],
  "objects": [...]
}
```

### 3. Data Layer (`src/model/`)

#### Data Models (data.py)
Python dataclasses representing annotation entities.

**Point2D:**
- `x: float, y: float`
- 2D coordinate representation

**AnnotationBase:**
- `id: str` (UUID)
- `category: str`
- `z_min: float, z_max: float` (vertical extent)

**Wall (extends AnnotationBase):**
- `start: Point2D`
- `end: Point2D`
- `thickness: float`

**Room (extends AnnotationBase):**
- `points: List[Point2D]` (polygon vertices)
- `name: str`
- `room_type: str`

**Object (extends AnnotationBase):**
- `center: Point2D`
- `width: float, height: float`
- `rotation: float`

**ProjectData:**
- `walls: List[Wall]`
- `rooms: List[Room]`
- `objects: List[Object]`
- `version: str`

All models provide `to_dict()` and `from_dict()` methods for JSON serialization.

## Coordinate Systems

### World Coordinates
- 3D space: (X, Y, Z) in meters
- Origin defined by point cloud data
- Z-axis represents vertical (height)

### Image Coordinates
- 2D raster: (row, column) in pixels
- Origin at top-left corner
- Y-axis inverted compared to world Y

### Canvas Coordinates
- QGraphicsView scene coordinates
- Maps directly to world (X, Y) coordinates
- Scale factor: pixels per meter

**Transformations:**
```python
# World to Image
img_x = (world_x - min_x) * scale + padding
img_y = (height - 1) - ((world_y - min_y) * scale + padding)

# Image to World
world_x = (img_x - padding) / scale + min_x
world_y = ((height - 1 - img_y) - padding) / scale + min_y
```

## Data Flow

### Point Cloud Loading
1. User selects file via QFileDialog
2. MainWindow calls Viewer3D.load_geometry()
3. Open3D loads point cloud
4. SliceEngine.load_data() extracts numpy arrays
5. Slider range updated based on Z bounds

### Slicing and Projection
1. User adjusts slider or inputs Z value
2. MainWindow.on_slider_change() triggered
3. SliceEngine.slice_at_height() filters points
4. SliceEngine.project_to_image() generates 2D image
5. Canvas2D.update_background() displays image
6. Viewer3D.update_slice_plane() shows plane in 3D

### Annotation Workflow
1. User selects tool (Wall/Room) from toolbar
2. Canvas2D.set_tool() activates drawing mode
3. User clicks on canvas to define geometry
4. Tool creates annotation object (Wall/Room)
5. AddItemCommand pushed to undo stack
6. GraphicsItem added to scene for visualization

### Save/Load Project
1. User triggers save/load action
2. ProjectIO.save_project() / load_project() called
3. Canvas2D provides/receives ProjectData
4. JSON serialization/deserialization
5. Canvas2D reconstructs graphics items from data

## Performance Considerations

### Point Cloud Processing
- NumPy vectorized operations for filtering and projection
- Configurable pixel size to balance quality vs. performance
- Morphological operations limited to small kernel sizes

### 2D Rendering
- QGraphicsView uses hardware acceleration when available
- Items cached as pixmaps for faster rendering
- Lazy updates to minimize unnecessary redraws

### Memory Management
- Point cloud data stored as numpy arrays (efficient)
- Graphics items created on-demand
- No duplicate storage of geometry data

## Extension Points

### Adding New Annotation Types
1. Define dataclass in `src/model/data.py`
2. Implement to_dict() / from_dict() methods
3. Create QGraphicsItem subclass in `src/gui/items.py`
4. Create drawing tool in `src/gui/tools.py`
5. Add undo commands in `src/core/undo_commands.py`
6. Update ProjectIO serialization

### Custom Visualization
- Override Canvas2D.update_background() for custom rendering
- Add processing steps in SliceEngine.project_to_image()
- Implement custom QGraphicsItem for specialized display

### Configuration
- Add entries to YAML config files
- Access via ConfigManager.get_*() methods
- No code changes required for UI strings or shortcuts

## Testing Strategy

### Unit Tests (`tests/`)
- Data model serialization/deserialization
- Coordinate transformations
- Slicing algorithm correctness
- Configuration loading

### Integration Tests
- Full workflow: load → slice → annotate → save → load
- Undo/Redo operation sequences
- Tool interactions and state transitions

### Manual Testing
- 3D visualization with various point cloud sizes
- UI responsiveness during heavy operations
- Cross-platform compatibility (Linux, Windows, macOS)
