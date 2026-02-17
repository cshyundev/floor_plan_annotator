# Floor Plan Annotator - Specifications

This directory contains the complete specification documentation for the Floor Plan Annotator project.

## Project Overview

Floor Plan Annotator is a desktop application that enables users to create 2D floor plan annotations from 3D point cloud data. The tool provides an interactive dual-view interface with a 3D point cloud viewer and a 2D canvas for drawing and editing floor plan elements.

## Key Capabilities

- **3D Point Cloud Processing**: Load and visualize point cloud data from common formats (PLY, PCD, OBJ, STL)
- **Interactive Slicing**: Extract horizontal cross-sections at any height with real-time preview
- **2D Annotation**: Draw and edit walls (line segments) and rooms (polygons) on the floor plan
- **Project Management**: Save and load annotation projects with all metadata preserved
- **User-Friendly Interface**: Dual-view layout, undo/redo support, and keyboard shortcuts

## Technology Stack

- **GUI Framework**: PyQt6
- **3D Processing**: Open3D
- **Scientific Computing**: NumPy, SciPy
- **Geometry Operations**: Shapely
- **Configuration**: PyYAML
- **Python Version**: 3.10+

## Document Structure

### [Requirements](requirements/index.md)
Detailed functional requirements for the application, including all implemented features and capabilities.

### [Architecture Decision Records (ADR)](adr/index.md)
Key architectural and design decisions made during development, including:
- GUI framework selection
- 3D visualization library choice
- Data model design
- Undo/Redo pattern implementation
- Slicing algorithm approach
- Configuration management

### [Project Status](status/index.md)
Current development status, including completed features and ongoing work.

### [Changelog](changelog/index.md)
Version history and release notes (to be maintained).

### [Technical Specification](technical-specification.md)
Detailed system architecture, component design, data flow, and implementation details.

### [API Reference](api-reference.md)
Complete API documentation for all core modules, data models, GUI components, and file formats.

### [Coding Standards](coding-standards.md)
Python coding standards, style guide, and quality requirements for the project.

## Project Structure

```
floor_plan_annotator/
├── src/
│   ├── main.py              # Application entry point
│   ├── gui/                 # GUI components
│   │   ├── main_window.py   # Main application window
│   │   ├── viewer_3d.py     # 3D point cloud viewer
│   │   ├── canvas_2d.py     # 2D annotation canvas
│   │   ├── items.py         # Graphics items (walls, rooms)
│   │   └── tools.py         # Drawing tools
│   ├── core/                # Core business logic
│   │   ├── processor.py     # Point cloud slicing engine
│   │   ├── io.py           # Project file I/O
│   │   ├── config.py       # Configuration manager
│   │   └── undo_commands.py # Undo/redo commands
│   └── model/              # Data models
│       └── data.py         # Annotation data structures
├── config/                 # Configuration files
├── data/                   # Sample data
├── tests/                  # Unit tests
└── specs/                  # This documentation
```

## Getting Started

See the main [README.md](../README.md) for installation and usage instructions.
