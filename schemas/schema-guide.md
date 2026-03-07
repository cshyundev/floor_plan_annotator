# Annotation JSON Schema v1.0 Guide

## Metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Schema version. `"1.0"` |
| `data_type` | string | Yes | Source data type: `"point_cloud"`, `"mesh"`, `"occupancy_grid"` |
| `coordinate_system` | string | Yes | Coordinate system convention: `"ros"`, `"opencv"`, `"opengl"` |
| `floor_level` | number | No | Floor surface height along the up-axis (meters). Default `0.0`. Reference only. |
| `created_at` | string (ISO 8601) | No | Timestamp of the first save. Set once, never overwritten. |
| `modified_at` | string (ISO 8601) | No | Timestamp of the most recent save. |

## Source

Metadata about the source data that was annotated.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_name` | string | Yes | Source data file name (e.g., `"scan.ply"`) |
| `bounds_min` | Point3D | No | Min corner of the source data bounding box |
| `bounds_max` | Point3D | No | Max corner of the source data bounding box |
| `occupancy_grid` | object | No | ROS2 map_server params (only when `data_type` is `"occupancy_grid"`) |

### source.occupancy_grid

Cross-reference with the ROS2 map YAML.

| Field | Type | Description |
|-------|------|-------------|
| `resolution` | number | Meters per pixel |
| `origin` | [x, y, yaw] | Map origin |
| `negate` | 0 or 1 | Pixel value negation |
| `occupied_thresh` | number | Occupied probability threshold |
| `free_thresh` | number | Free probability threshold |

## Coordinate Convention

All coordinates are **absolute 3D values** in the original coordinate system (meters):

| `coordinate_system` | x | y | z |
|---------------------|---|---|---|
| `"ros"` | X | Y | Z (up) |
| `"opencv"` | X | Y | Z |
| `"opengl"` | X | Y | Z |

Point3D `[x, y, z]` maps directly to the 3D axes of the chosen coordinate system.

## Layout

All annotations live under the `layout` key.

### Wall

A wall is a pair of 3D points: `[start, end]`.

```json
[[1.159, 1.213, 0.0], [1.159, 4.099, 0.0]]
```

### Room

A closed polygon of 3D vertices with a semantic type. Last vertex connects back to first.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier |
| `type` | string | Yes | Room type: `"bedroom"`, `"kitchen"`, etc. |
| `points` | Point3D[] | Yes | Ordered polygon vertices (min 3) |

## Object

An oriented bounding box (OBB) in 3D space.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier |
| `type` | string | Yes | Object type: `"furniture"`, `"appliance"`, `"obstacle"`, etc. |
| `center` | Point3D | Yes | Center of the OBB |
| `extent` | [w, h, d] | Yes | Full size along local axes (meters) |
| `rotation` | [w, x, y, z] | Yes | Orientation as quaternion |

## Zone

A purpose-defined floor area (no-go, caution, restricted, etc.). Same structure as Room.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier |
| `type` | string | Yes | Zone purpose: `"no_go"`, `"caution"`, `"clean"`, `"restricted"`, etc. |
| `points` | Point3D[] | Yes | Ordered polygon vertices (min 3) |
