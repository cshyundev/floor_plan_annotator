# ADR-009: Reorganize Configuration Files

- **Date**: 2026-02-16
- **Status**: Accepted

## Context

The original colors.yaml file contained not just color settings but also various UI configuration values including dimensions (sizes in meters/pixels), behavior settings (zoom limits, snap tolerance, hover scale), and rendering order (z_values). This mixed multiple concerns in a single file, making it harder to understand and maintain.

## Decision

Split the configuration into two files:
1. colors.yaml - Contains only color settings for all UI elements (grid, nodes, walls, rooms, background)
2. ui_config.yaml - Contains all other UI settings including dimensions, behavior parameters, and rendering order

Updated ConfigManager to load both files and maintain backward compatibility. When code requests values via get_value("colors", ...), the manager checks colors.yaml first, then falls back to ui_config.yaml. This ensures all existing code continues to work without modification.

## Consequences

Positive:
- Improved organization and separation of concerns
- colors.yaml now clearly contains only color values
- ui_config.yaml groups related non-color settings together
- Backward compatible - no code changes required
- Easier to find and modify specific types of settings
- Better file names reflect actual content

Negative:
- Two config files to manage instead of one
- Need to know which file contains which setting when adding new config values
