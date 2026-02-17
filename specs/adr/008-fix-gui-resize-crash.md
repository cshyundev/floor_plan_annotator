# ADR-008: Fix GUI Window Resize Crash and Open3D Initialization Failures

- **Date**: 2026-02-16
- **Status**: Accepted

## Context

The GUI application crashed with segmentation fault (exit code 139) when attempting to resize or maximize the window. Investigation revealed multiple issues:

1. **QImage Memory Management in Viewer3D**: The render_scene() method created QImage objects that referenced temporary numpy array memory (img_np.data). When the numpy array went out of scope, QImage had a dangling pointer, causing segmentation faults.

2. **QImage Memory Management in Canvas2D**: Similar issue where QImage referenced numpy array without owning the data.

3. **Open3D Import Crash**: In certain environments (headless, missing OpenGL/EGL support), importing Open3D's OffscreenRenderer causes immediate segmentation fault at the C++ level before Python exception handling can catch it.

4. **Expensive Renderer Recreation**: resizeEvent recreated the entire OffscreenRenderer on every resize, which is expensive and prone to crashes.

## Decision

Applied multi-layered fix strategy:

### 1. Fixed QImage Memory Issues

**Canvas2D:**
- Store numpy array copy as instance variable (`_background_data`)
- Create QImage from persistent data
- Call `.copy()` to ensure Qt owns the image data

**Viewer3D:**
- Store numpy array copy as instance variable (`_image_data`)
- Create QImage from persistent data
- Call `.copy()` to ensure Qt owns the data

### 2. Graceful Degradation for Open3D

- Created `Viewer3DStub` class that shows helpful error message when Open3D is unavailable
- Use subprocess to test if Open3D import will crash before attempting actual import
- MainWindow automatically uses stub implementation if Open3D fails
- 2D canvas continues to work normally even when 3D viewer is disabled

### 3. Enhanced Error Handling

- Added try-except blocks around all renderer operations in Viewer3D
- Added `_renderer_failed` flag to prevent repeated failure attempts
- Deferred renderer creation until widget is visible (showEvent)
- Added validation checks in resizeEvent (dimensions, visibility)

### 4. Improved Resize Handling

- Canvas2D: Proper fitInView with aspect ratio preservation
- Track user zoom state to preserve manual zoom levels
- Safe fallback with try-except around fitInView calls

## Consequences

### Positive

- ✓ Window resize/maximize now works without crashes
- ✓ Application runs in environments without Open3D/OpenGL support
- ✓ 2D canvas fully functional even when 3D viewer unavailable
- ✓ All 34 tests pass (100% success rate)
- ✓ Helpful error messages guide users when Open3D missing
- ✓ Real-world coordinates (meters) preserved during resize
- ✓ Graceful degradation improves robustness

### Negative

- Additional complexity with subprocess Open3D check (adds ~1 second startup time)
- Viewer3DStub adds a new file to maintain
- Some code duplication between Viewer3D and Viewer3DStub for interface compatibility

## Files Modified

- `src/gui/canvas_2d.py` - Fixed QImage memory management
- `src/gui/viewer_3d.py` - Fixed QImage memory, added error handling, deferred initialization
- `src/gui/viewer_3d_stub.py` (NEW) - Stub implementation for when Open3D unavailable
- `src/gui/main_window.py` - Subprocess Open3D check, graceful fallback to stub

## Technical Details

### Memory Management Fix

Before (causes segfault):
```python
img_np = np.asarray(self.renderer.render_to_image())
self.image = QImage(img_np.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
# img_np goes out of scope → dangling pointer in QImage
```

After (safe):
```python
img_np = np.asarray(self.renderer.render_to_image())
self._image_data = np.copy(img_np)  # Keep alive as instance variable
q_image = QImage(self._image_data.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
self.image = q_image.copy()  # Qt owns the data
```

### Open3D Import Protection

```python
def test_open3d_import():
    """Test if Open3D import will crash using a subprocess."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import open3d"],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False

VIEWER3D_AVAILABLE = test_open3d_import()
```
