# Project Status

## Done

### Core Features (2026-02-15)
- 3D point cloud loading and visualization
- Height-based slicing with interactive slider control
- 2D floor plan projection with configurable resolution
- Wall annotation tool with line drawing
- Room annotation tool with polygon drawing
- Selection and editing of annotations
- Undo/Redo functionality with keyboard shortcuts
- Project save/load to JSON format
- Dual-view layout (3D + 2D) with resizable splitter
- YAML-based configuration system
- Status bar with tool feedback

### Development Infrastructure (2026-02-15)
- Python package structure with pyproject.toml
- UV-based dependency management
- Auto-load development data for testing

## TODO

### Bug

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| *(없음)* | | | | | |

### Improvement

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| IMP-002 | 슬라이싱 성능 최적화 | SliceEngine | - | REQ-003 | 포인트 수가 많을 때 버벅임 발생. 데이터 처리 효율화 필요 |

### Feature

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| FEAT-001 | 좌표계 설정 지원 | 3D Processing / Config | - | REQ-001 | 현재 ROS 좌표계만 지원. OpenCV, OpenGL 등 타 좌표계 대응 필요. 구체적 사항 추후 결정 |
| FEAT-002 | 2D Canvas에서 선분에 대해 수직, 수평에 대한 힌트와 보정 | 2D Canvas / Drawing Tools | - | REQ-020 | |
| FEAT-003 | Occupancy Grid에 대한 Annotation 기능 지원 | 2D Canvas / Annotation | - | REQ-021 | Draft — 상세 스펙 추후 정의 |

## In Progress

Currently no items in progress.

## On Hold

Currently no items on hold.
