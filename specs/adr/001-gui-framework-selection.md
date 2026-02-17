# ADR-001: PyQt6 as GUI Framework

- **Date**: 2026-02-15
- **Status**: Accepted

## Context

The application requires a cross-platform GUI framework to build a desktop application with dual-view layout (3D and 2D), interactive controls, and standard UI components.

## Decision

Use PyQt6 as the primary GUI framework for the application.

## Consequences

- Provides mature and feature-rich GUI components including QGraphicsView for 2D canvas
- Built-in undo/redo stack (QUndoStack) for command pattern implementation
- Cross-platform support (Linux, Windows, macOS)
- Strong integration with Python ecosystem
- Requires PyQt6 license consideration for commercial use
