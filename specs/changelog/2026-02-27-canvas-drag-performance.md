# 2026-02-27: 2D Canvas Drag Performance Optimization

- **Category**: Changed
- **Description**: Optimized 2D canvas interaction performance to reduce stuttering when dragging nodes, edges, and polygons.

## Optimizations Applied

1. **Batch polygon drag updates** — During polygon drag/rotate, `update_shape()` is now called once per frame instead of once per node (4x→1x for a 4-node polygon). Per-node snap computation is also suppressed during batch updates.
2. **Snap guide object pooling** — Guide line items are reused from a pool instead of being created and destroyed every frame, eliminating per-frame scene add/remove overhead.
3. **Qt viewport optimization** — Added `MinimalViewportUpdate` mode and `CacheBackground` to reduce redundant viewport repaints.
4. **ObjectItem trig caching** — Cached `_compute_corners()` and `_rotation_handle_pos()` results, eliminating repeated cos/sin calculations in `boundingRect()`, `shape()`, and `paint()`.
5. **Removed redundant `prepareGeometryChange()`** — `setPolygon()` already calls it internally; explicit calls in `mouseMoveEvent` were redundant.
6. **Undo/redo batch optimization** — `MoveNodesCommand` now batches node position updates to avoid cascading `update_shape()` calls.

## Measured Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Polygon `update_shape()` calls per 100 frames | 496 | 100 | 80% reduction |
| Polygon drag time (100 frames) | 9.8ms | 6.0ms | 39% faster |
| Node drag time (100 frames) | 28.1ms | 19.7ms | 30% faster |

## Files Changed

- `src/gui/items/polygon_base.py` — Batch update flag
- `src/gui/items/nodes.py` — itemChange batch guard
- `src/core/undo_commands.py` — MoveNodesCommand batch
- `src/gui/snap/snap_guide_manager.py` — Guide object pool
- `src/gui/canvas_2d.py` — Viewport optimization flags
- `src/gui/items/object_item.py` — Trig cache, prepareGeometryChange removal
- `tests/test_performance.py` — Performance benchmark (new)
- `tests/test_integration.py` — Fixed annotation item filter for guide pool compatibility
