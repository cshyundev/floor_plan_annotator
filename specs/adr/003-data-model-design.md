# ADR-003: Dataclass-based Annotation Model

- **Date**: 2026-02-15
- **Status**: Accepted

## Context

The application needs to represent various annotation types (walls, rooms, objects) with structured data that can be serialized to JSON.

## Decision

Use Python dataclasses to define annotation models (Wall, Room, Object) with explicit serialization/deserialization methods.

## Consequences

- Clean and readable data structure definitions
- Type hints for better IDE support and code quality
- Explicit to_dict() and from_dict() methods for JSON serialization
- UUID-based unique identifiers for each annotation
- Easy to extend with new annotation types
