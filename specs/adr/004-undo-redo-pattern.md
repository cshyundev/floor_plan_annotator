# ADR-004: Command Pattern for Undo/Redo

- **Date**: 2026-02-15
- **Status**: Accepted

## Context

Users need to undo and redo annotation operations (adding, moving, deleting walls and rooms) during the annotation workflow.

## Decision

Implement undo/redo functionality using PyQt6's QUndoStack and QUndoCommand pattern.

## Consequences

- Consistent undo/redo behavior across all annotation operations
- Built-in keyboard shortcut support (Ctrl+Z, Ctrl+Y)
- Each modification operation implemented as a separate QUndoCommand subclass
- Stack-based history management handled by Qt framework
- Requires wrapping all modification operations in command objects
