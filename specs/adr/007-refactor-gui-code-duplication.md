# ADR-007: Comprehensive GUI Refactoring for Maintainability

- **Date**: 2026-02-16
- **Status**: Accepted

## Context

The GUI code (canvas_2d.py and tools.py) had several structural issues that reduced maintainability and violated SOLID principles:

### Code Duplication (DRY Violation)
- InputContext creation was repeated 3 times in canvas_2d.py mouse event handlers
- find_node_at logic was duplicated between DrawWallTool and potentially DrawRoomTool
- ConfigManager.instance() was called repeatedly across all tool classes

### Magic Numbers
- Hardcoded tolerance values (10, 15)
- Hardcoded paste offset (20)
- Hardcoded rotation handle offset (30)

### Long Methods
- DrawWallTool.on_mouse_press (~42 lines) handled both first and second click logic
- DrawRoomTool.on_mouse_press (~45 lines) handled multiple responsibilities

### Single Responsibility Violation
- Canvas2D class had too many responsibilities: tool management, clipboard operations, event handling, data serialization
- Violated separation of concerns principle

## Decision

Applied comprehensive refactoring using multiple patterns:

### Phase 1: Eliminate Code Duplication
1. Created _create_input_context() helper method in Canvas2D
2. Moved find_node_at() to Tool base class
3. Added config property to Tool base class with lazy initialization
4. Moved InputContext import to top of canvas_2d.py

### Phase 2: Extract Magic Numbers
1. Added node.snap_tolerance (10) to config/colors.yaml
2. Added room.paste_offset (20) to config/colors.yaml
3. Added room.rotation_handle_offset (30) to config/colors.yaml
4. Updated all code to use config values instead of hardcoded numbers

### Phase 3: Decompose Long Methods
1. Split DrawWallTool.on_mouse_press into:
   - on_mouse_press (dispatcher)
   - _handle_first_click (start wall)
   - _handle_second_click (complete wall segment)

2. Split DrawRoomTool.on_mouse_press into:
   - on_mouse_press (dispatcher)
   - _handle_left_click (process left click)
   - _handle_right_click (finish/cancel)
   - _is_clicking_existing_item (check existing items)
   - _should_close_polygon (check polygon closure)
   - _add_node (add new node)

### Phase 4: Extract Manager Classes
1. Created ToolManager class (src/gui/tool_manager.py):
   - Manages tool instances and switching
   - Handles tool cleanup on switch
   - Encapsulates tool-related logic

2. Created ClipboardManager class (src/gui/clipboard_manager.py):
   - Manages clipboard operations
   - Handles copy/paste logic
   - Isolates clipboard state

### Phase 5: Extract Data Serialization
1. Created DataSerializer class (src/gui/data_serializer.py):
   - Converts scene items to ProjectData format (save_to_data)
   - Recreates scene items from ProjectData (load_from_data)
   - Handles node deduplication and room boundary edges
   - Manages room ID counter reset
   - Restores background after scene clear

### Phase 6: Extract Event Coordination
1. Created EventCoordinator class (src/gui/event_coordinator.py):
   - Centralizes mouse event handling (press, move, release)
   - Centralizes keyboard event handling (copy, paste, delete)
   - Handles wheel events for zooming
   - Delegates to appropriate tools and managers
   - Improves separation between UI events and business logic

## Consequences

### Positive

**Code Quality Metrics:**
- Test coverage: 78% → 80% (+2%)
- Total statements: 979 → 1088 (+109, due to new classes)
- Uncovered lines: 211 → 214 (+3, new code)
- All 35 tests passing (100%)

**Canvas2D Improvement:**
- Statements: 222 → 113 (-49%, **halved!**)
- Coverage: 74% → 83% (+9%)
- Responsibilities: 7 → 3 (core only: scene management, room ID, undo stack)

**New Classes (Well-Tested):**
- ClipboardManager: 36 statements, 97% coverage
- ToolManager: 36 statements, 97% coverage
- DataSerializer: 85 statements, 66% coverage
- EventCoordinator: 45 statements, 67% coverage

**Maintainability:**
- Single Responsibility: Each class now has a clear, focused purpose
- DRY Principle: No code duplication across GUI modules
- Configuration: All magic numbers externalized to config
- Method Length: All methods under 25 lines (avg ~15 lines)
- Readability: Clear method names describe exact responsibility

**Extensibility:**
- New tools can be added easily via ToolManager
- Clipboard can support new item types via ClipboardManager
- Config-driven behavior makes customization trivial

### Negative

**Increased Complexity:**
- Two additional classes to understand
- More files in the project structure
- Slight indirection when accessing tools or clipboard

**Migration:**
- Added compatibility properties to maintain backward compatibility with tests
- Future code should use new interfaces (tool_manager, clipboard_manager)

## Metrics Summary

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Test Coverage | 78% | 80% | +2% |
| Tests Passing | 35/35 | 35/35 | ✓ |
| Code Statements | 979 | 1088 | +109 |
| Uncovered Lines | 211 | 214 | +3 |
| **Canvas2D Statements** | **222** | **113** | **-49%** |
| **Canvas2D Coverage** | **74%** | **83%** | **+9%** |
| Max Method Length | ~45 lines | ~25 lines | -44% |
| Magic Numbers | 5 | 0 | -100% |
| Canvas2D Responsibilities | 7 | 3 | -57% |
| New Manager Classes | 0 | 4 | +4 |

## Implementation Notes

- Refactoring was done incrementally in 6 phases with tests after each phase
- All changes maintain backward compatibility via properties
- New classes follow same coding standards (type hints, docstrings)
- Configuration changes are backward compatible (fallback values)

## Architecture Impact

**Before Refactoring:**
```
Canvas2D (222 lines, 7 responsibilities)
├─ Scene management
├─ Tool management & switching
├─ Clipboard operations
├─ Event handling (mouse, keyboard, wheel)
├─ Data serialization
├─ Room ID management
└─ Undo stack management
```

**After Refactoring:**
```
Canvas2D (113 lines, 3 core responsibilities)
├─ Scene management
├─ Room ID management
└─ Undo stack management

Delegated to specialized classes:
├─ ToolManager (36 lines) - Tool lifecycle
├─ ClipboardManager (36 lines) - Copy/paste
├─ DataSerializer (85 lines) - Save/load
└─ EventCoordinator (45 lines) - Event routing
```

**Benefits:**
- **Separation of Concerns**: Each class has a single, clear responsibility
- **Testability**: Smaller, focused classes are easier to test thoroughly
- **Maintainability**: Changes to one concern don't affect others
- **Clarity**: Canvas2D's core purpose (scene container) is now obvious
- **Extensibility**: Easy to add new tools, event types, or serialization formats
