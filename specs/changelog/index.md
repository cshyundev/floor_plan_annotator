# Changelog Index

- 2026-02-26 [Fixed] Reset UI state on data load: re-enable slicing controls when loading 3D data after occupancy grid, clear stale projection cache when loading occupancy grid (BUG-001)
- 2026-02-26 [Changed] Updated status/index.md with BUG-001, IMP-002, IMP-003 entries
- 2026-02-25 [Added] Shared nodes between annotations: polygon drawing tools (room, custom polygon) reuse existing NodeItems on click, smart orphan detection on deletion preserves shared nodes, boundary edge tagging for correct load/delete behavior (FEAT-004, REQ-024)
- 2026-02-25 [Added] 2D slice color projection: project_to_image() colors parameter for topmost-point RGB rendering, Canvas2D RGB support, white default for colorless point clouds (IMP-001, REQ-023)
- 2026-02-25 [Added] Occupancy Grid Map loading and annotation support: ROS2 map_server format, 2D background, 3D block mesh, Map Info section, project save/load v3.0 (FEAT-003, REQ-021) ([detail](2026-02-25-occupancy-grid-map-support.md))
- 2026-02-25 [Added] Snap & Alignment Guide System with annotation precision convenience features (FEAT-002, REQ-020) ([detail](2026-02-25-snap-alignment-guide-system.md))
- 2026-02-25 [Changed] Removed auto-detect floor feature; floor level is now set manually via spinbox only (REQ-022)
- 2026-02-25 [Added] Coordinate system configuration support: ROS, OpenCV, OpenGL presets with custom option, manual floor level control, annotations stored in original coordinate system (FEAT-001, REQ-022)
- 2026-02-25 [Fixed] Auto-reactivate "Show Original 3D Data" checkbox when slice height changes (BUG-003, REQ-017)
- 2026-02-24 [Fixed] Type Editor list displays human-readable name instead of internal key, Add button shows input dialog, and new types get unique random colors (BUG-002, REQ-018)
- 2026-02-24 [Changed] Updated REQ-017 with auto-reactivation behavior for "Show Original 3D Data" checkbox on slice height change (BUG-003)
- 2026-02-24 [Added] REQ-020: Line Orthogonal Snapping — vertical/horizontal hints and snapping for all line-drawing tools (FEAT-002)
- 2026-02-24 [Added] REQ-021: Occupancy Grid Annotation — draft requirement for annotation on occupancy grids (FEAT-003)
- 2026-02-24 [Changed] Updated status/index.md with REQ references for BUG-003, FEAT-002, FEAT-003
