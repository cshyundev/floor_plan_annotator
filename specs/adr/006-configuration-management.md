# ADR-006: YAML-based Configuration

- **Date**: 2026-02-15
- **Status**: Accepted

## Context

The application needs configurable UI labels, keyboard shortcuts, and application settings that can be easily modified without code changes.

## Decision

Use YAML configuration files managed by a ConfigManager singleton for application settings.

## Consequences

- Human-readable configuration format
- Centralized configuration access through singleton pattern
- Support for internationalization through configurable UI labels
- Customizable keyboard shortcuts
- Requires YAML parser dependency (PyYAML)
