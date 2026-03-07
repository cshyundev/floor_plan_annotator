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
- BUG-003 fixed: 2D canvas projection and 3D viewer annotations missing after loading annotations.json

### Type Name = Key Unification — BUG-004, BUG-005 (2026-03-02)
- Type name is the key: removed separate `name` field from config YAML (BUG-004)
- New types use user-entered name directly as key instead of random UUID
- All builtin type keys migrated from snake_case to display name (e.g., `furniture` → `Furniture`)
- Legacy annotations.json backward compatible via `_LEGACY_TYPE_MAP` migration
- Duplicate name check on add and rename (BUG-005 resolved)
- Type rename via `editingFinished` signal with canvas item update

## TODO

### Bug

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| BUG-007 | Coordinate System의 Custom 옵션 제거 필요 | gui/coordinate_system_widget, core/coordinate_system | P1 | | 프리셋(ros/opencv/opengl)만 지원. Custom 좌표계 UI 및 로직 제거 |
| BUG-008 | config에 없는 type key 로드 시 경고 없음 | gui/data_serializer, model/data | P1 | | annotations.json에 config에 존재하지 않는 type key가 있을 때 무경고로 fallback 스타일 적용. 사용자에게 알림 필요 |
| BUG-009 | Custom Polygon 흔적이 아직도 존재 | - | P1 | |

### Improvement

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| IMP-005 | source.bounds 자동 입력 | model/data, main_window | P2 | REQ-028 | processor에서 3D bounding box 추출하여 source.bounds_min/max 자동 기록 |

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
