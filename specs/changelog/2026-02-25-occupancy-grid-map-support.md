# 2026-02-25: Occupancy Grid Map Loading and Annotation Support

- **Category**: Added
- **Description**: Implemented FEAT-003 / REQ-021 — load ROS2 map_server compatible occupancy grid maps (YAML + PGM/PNG), display as 2D canvas background, generate 3D block mesh (floor + occupied cell blocks) for the 3D viewer, and annotate with existing tools (wall, room, custom polygon, object). Includes manual metadata input dialog as fallback when no YAML is found, Map Info section in control dock, project save/load with map metadata (v3.0 format, backward compatible with v2.0), and Z slider disabled in occupancy grid mode while "Show Original 3D Data" toggle remains active.

## Files Added
- `src/core/map_loader.py` — YAML parsing, image loading, bounds/scale computation, pixel classification
- `src/core/map_mesh_generator.py` — Occupied cell to 3D block mesh generation
- `src/gui/map_metadata_dialog.py` — Manual metadata input dialog
- `data/test_map.yaml`, `data/test_map.png` — Mock ROS2 occupancy grid for testing
- `tests/test_map_loader.py` — MapLoader tests (30 tests)
- `tests/test_map_mesh_generator.py` — MapMeshGenerator tests (16 tests)

## Files Modified
- `src/model/data.py` — Added MapMetadata dataclass, ProjectData v3.0 with map_metadata field
- `src/gui/main_window.py` — Menu action, loading logic, save/load with map metadata, Map Info section
- `src/gui/viewer_3d.py` — Added set_geometry() for pre-created meshes
- `src/core/annotation_sync.py` — Added enabled flag to skip 3D sync in occupancy grid mode
- `config/strings.yaml` — Added load_occupancy_grid menu string
- `config/ui_config.yaml` — Added occupancy_grid.block_height setting
- `tests/test_model_data.py` — Added MapMetadata and ProjectData v3.0 tests (7 tests)
