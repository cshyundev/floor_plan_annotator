# ADR-005: Height-based Point Cloud Slicing

- **Date**: 2026-02-15
- **Status**: Accepted

## Context

The application needs to extract horizontal cross-sections from 3D point clouds to generate 2D floor plan projections.

## Decision

Implement slicing by filtering points within a Z-axis range (height ± thickness/2) and projecting to 2D with density-based image generation.

## Consequences

- Simple and efficient NumPy-based filtering using boolean masks
- Configurable slice thickness for capturing points around the target height
- 2D projection uses pixel-based accumulation with morphological dilation for clearer visualization
- Configurable pixel size for resolution control
- Coordinate transformation between world space and image space requires careful handling
