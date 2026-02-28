# Project Status

## Done

### Core Features (2026-02-15)
- 3D point cloud loading and visualization
- Height-based slicing with interactive slider control
- 2D floor plan projection with configurable resolution
- Wall annotation tool with line drawing
- Room annotation tool with polygon drawing
- Selection and editing of annotations
- Undo/Redo functionality with keyboard shortcuts
- Project save/load to JSON format
- Dual-view layout (3D + 2D) with resizable splitter
- YAML-based configuration system
- Status bar with tool feedback

### Coordinate System Support (2026-02-25)
- Multi-convention coordinate system support (ROS, OpenCV, OpenGL, Custom)
- Manual floor level configuration via spinbox
- Annotations stored in original data coordinate system
- Coordinate system metadata in project files (v2.0)

### Snap & Alignment Guide System (2026-02-26)
- Global H/V angle snapping for all line-drawing tools
- Relative parallel/perpendicular snapping against existing edges
- Cross-object alignment guides (PPT-style) for drawing and dragging
- Shift key toggle for snap on/off
- Configurable thresholds, angle sets, and guide colors
- EdgeItem hover: H/V status display with color feedback
- EdgeItem context menu: Align to Horizontal/Vertical
- NodeItem context menu: Make Perpendicular (Thales circle) — supports wall and polygon nodes
- First-click alignment snap for wall tool
- PolygonItem (Room/CustomPolygon) context menu: Align nearest edge to Horizontal/Vertical (IMP-002)
- PolygonItem hover: nearest edge H/V status display in status bar (IMP-002)
- ObjectItem rotation: angle snap to 0°/90°/180°/270° with guide lines (IMP-003)
- Shared geometry utilities extracted to `geometry_utils.py` for EdgeItem/PolygonItem reuse

### Occupancy Grid Map Support (2026-02-25)
- ROS2 map_server format loading (YAML + PGM/PNG)
- 2D canvas background display with world-coordinate mapping
- 3D block mesh generation (floor + occupied cell blocks)
- Manual metadata input dialog (fallback when no YAML)
- Map Info section in control dock
- Project save/load with map metadata (v3.0 format, backward compatible)
- Annotation tools work on occupancy grid without modification

### 2D Slice Color Projection (IMP-001) (2026-02-25)
- Color-aware 2D projection using topmost point color per pixel (REQ-023)
- Coordinate-system-aware height sorting (works with ROS, OpenCV, OpenGL)
- Nearest-neighbor color dilation for wall thickness
- Occupancy grid mode unaffected (uses separate grayscale path)

### Shared Nodes Between Annotations (FEAT-004) (2026-02-25)
- Polygon drawing tools (room, custom polygon) reuse existing NodeItems on click (REQ-024)
- Smart orphan detection on deletion preserves shared nodes
- Boundary edge tagging for correct load/delete behavior

### GLB/GLTF Mesh Support (REQ-031) (2026-02-28)
- trimesh-based GLB/GLTF loading with UV-texture-to-vertex-color baking
- Height slicing and 2D color projection work with mesh data (BUG-002 fixed)
- scene.dump() for correct multi-node transform handling
- Dense tessellation sample data (0.05 m grid) for reliable slice testing
- Renderer-independent geometry loading: 2D canvas works even if 3D renderer fails

### Object 3D Properties (FEAT-005) (2026-02-26)
- Per-type default elevation and 3D height in `objects.yaml` (REQ-025)
- Per-instance override via Properties Panel spinboxes
- Ctrl+Wheel for 3D Height, Ctrl+Shift+Wheel for Elevation adjustment
- 3D viewer: per-object z_min/z_max wireframe rendering
- Type change resets to new type's 3D defaults with undo support
- Backward compatible project load (old files use type defaults)

### Development Infrastructure (2026-02-15)
- Python package structure with pyproject.toml
- UV-based dependency management
- Auto-load development data for testing

### Project Lifecycle Management — FEAT-006 (2026-02-28)
- New/Save/Save As with annotations.json fixed-name convention (REQ-026, REQ-030)
- Dirty state tracking via QUndoStack.cleanChanged → title bar feedback
- Auto-detect annotations.json on 3D data load with pairing validation
- Bidirectional entry: open 3D file first or open annotations.json first
- Unsaved-change confirmation on New / Load / app close

## TODO

### Bug

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| BUG-003 | annotations.json 불러온 후 2D canvas projection 없음 | main_window | P0 | REQ-026 | 배경 슬라이스 이미지 미표시 |

### Improvement

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| *(없음)* | | | | | |

### Feature

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| FEAT-007 | Recent Files | main_window | P1 | REQ-027 | QSettings, 최근 5개, Clear 기능 |
| FEAT-008 | Project JSON Schema v4.0 | model/data, core/io | P1 | REQ-028 | project_name, 타임스탬프 추가, image_path_absolute 제거 |
| FEAT-009 | Auto-save Recovery | main_window, core/io | P2 | REQ-029 | 5분 주기 자동 저장, 크래시 복구 |

## In Progress

Currently no items in progress.

## On Hold

Currently no items on hold.
