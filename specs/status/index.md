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
| BUG-001 | Wall 삭제 시 점만 삭제되고 선분이 남는 버그 | Wall 도구 | - | REQ-005 | Backspace로 점 삭제 시 연결된 EdgeItem도 함께 삭제해야 함 |
| BUG-002 | 카테고리 관리 추가/삭제 버그 | Type Editor | - | REQ-018 | 기존 카테고리 수정 처리 및 Add 버튼 동작 수정 필요. 구체적 사항 추후 결정 |

### Improvement

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| IMP-001 | 2D 캔버스 크기 고정 | Canvas2D / SliceEngine | - | REQ-004 | 슬라이싱 시 픽셀 그리드의 위치와 크기가 변동되지 않아야 함 |
| IMP-002 | 슬라이싱 성능 최적화 | SliceEngine | - | REQ-003 | 포인트 수가 많을 때 버벅임 발생. 데이터 처리 효율화 필요 |

### Feature

| ID | 제목 | 관련 영역 | 우선순위 | 관련 REQ | 비고 |
|----|------|----------|---------|---------|------|
| FEAT-001 | 좌표계 설정 지원 | 3D Processing / Config | - | REQ-001 | 현재 ROS 좌표계만 지원. OpenCV, OpenGL 등 타 좌표계 대응 필요. 구체적 사항 추후 결정 |

## In Progress

Currently no items in progress.

## On Hold

Currently no items on hold.
