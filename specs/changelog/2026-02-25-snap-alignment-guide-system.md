# 2026-02-25: Snap & Alignment Guide System

- **Category**: Added
- **Description**: Implemented full snap and alignment guide system (FEAT-002, REQ-020) with the following features:
  - Global H/V angle snapping for all line-drawing tools (wall, room, custom polygon, object)
  - Relative parallel/perpendicular snapping against existing edges
  - Cross-object alignment guides (PPT-style) for drawing and dragging
  - Shift key toggle for snap on/off
  - EdgeItem hover: H/V status display with green/amber color feedback and status bar message
  - EdgeItem right-click context menu: Align Horizontal / Align Vertical
  - NodeItem right-click context menu: Make Perpendicular (Thales circle projection)
  - First-click alignment snap for wall tool
  - Configurable thresholds, angle sets, and guide colors via YAML config
