# 2. 데이터 로드

어노테이션을 시작하기 전에 평면도의 기반이 될 3D 데이터를 불러옵니다. 세 가지 데이터 형식을 지원합니다.

---

## 2.1 포인트 클라우드 로드

### 지원 형식

| 확장자 | 설명 |
|--------|------|
| `.ply` | Polygon File Format (가장 일반적) |
| `.pcd` | Point Cloud Data (ROS 표준) |
| `.obj` | Wavefront OBJ |
| `.stl` | STereoLithography |

### 로드 방법

1. 메뉴바에서 `File > Load Point Cloud` 선택
2. 파일 선택 다이얼로그에서 포인트 클라우드 파일 선택
3. 로드 완료 후 3D 뷰어에 포인트 클라우드가 표시됨

![포인트 클라우드 로드 다이얼로그](images/02_load_pointcloud_dialog.png)

![포인트 클라우드가 3D 뷰어에 표시된 상태](images/02_pointcloud_loaded.png)

> **참고**: 같은 폴더에 `annotations.json` 파일이 있으면 자동으로 불러올지 확인합니다.

---

## 2.2 메시 데이터 로드 (GLB/GLTF)

텍스처가 포함된 3D 메시를 로드합니다.

### 지원 형식

| 확장자 | 설명 |
|--------|------|
| `.glb` | GL Binary (텍스처 포함 단일 파일) |
| `.gltf` | GL Transmission Format |

### 로드 방법

1. `File > Load Point Cloud`를 선택한 후 `.glb` 또는 `.gltf` 파일 선택
2. 텍스처 색상이 3D 뷰어에 표시됨

![GLB 메시가 3D 뷰어에 표시된 상태 — 텍스처 색상 포함](images/02_mesh_loaded.png)

---

## 2.3 점유 그리드 맵 로드 (ROS2)

ROS2 `map_server`가 생성한 2D 맵을 로드합니다.

### 필요한 파일

| 파일 | 설명 |
|------|------|
| `.yaml` | 맵 메타데이터 (해상도, 원점 등) |
| `.pgm` 또는 `.png` | 맵 이미지 파일 |

두 파일은 같은 폴더에 있어야 합니다.

### 로드 방법

1. `File > Load Occupancy Grid` 선택
2. `.yaml` 파일 선택
3. 2D 캔버스 배경에 맵 이미지가 표시되고, 3D 뷰어에도 블록 형태로 표시됨

![점유 그리드 로드 다이얼로그](images/02_load_occupancy_dialog.png)

![점유 그리드가 2D 캔버스 배경으로 표시된 상태](images/02_occupancy_loaded.png)

---

## 2.4 높이 슬라이싱 (Z 슬라이더)

포인트 클라우드 또는 메시 데이터를 로드한 후, 3D 뷰어 아래의 **Z 슬라이더**로 특정 높이의 단면을 추출하여 2D 캔버스 배경으로 활용할 수 있습니다.

![Z 슬라이더 위치 — 3D 뷰어 하단](images/02_z_slider.png)

### 슬라이더 조작

| 조작 | 동작 |
|------|------|
| 슬라이더 드래그 | 슬라이스 높이 변경 |
| 슬라이스 평면이 3D 뷰어에 표시됨 | 현재 높이를 시각적으로 확인 |

### 표시 모드

슬라이더 옆의 드롭다운에서 표시 모드를 선택합니다.

| 모드 | 설명 |
|------|------|
| **Slice** | 현재 Z 높이 근방의 포인트만 2D로 표시 |
| **All Points** | 전체 포인트를 위에서 내려다본 형태로 표시 |

![Slice 모드와 All Points 모드 비교](images/02_slice_vs_all.png)

---

## 2.5 좌표계 선택

3D 데이터의 좌표계에 맞게 설정합니다. 우측 도크 패널의 **Coordinate System** 섹션에서 선택합니다.

![Coordinate System 패널](images/02_coordinate_system.png)

| 프리셋 | 설명 |
|--------|------|
| **ROS** | Z축이 위쪽 (로봇 공학 표준) |
| **OpenCV** | Y축이 아래쪽 |
| **OpenGL** | Y축이 위쪽 |
| **Custom** | 수동으로 축 매핑 설정 |

> **권장**: ROS 데이터는 ROS, 일반 3D 파일은 OpenGL을 사용하세요.

---

## 2.6 프로젝트 파일 자동 감지

3D 데이터를 로드할 때 같은 폴더에 `annotations.json` 파일이 있으면 자동으로 감지합니다.

- **파일이 있고 유효한 경우**: 이전에 작업한 어노테이션을 불러올지 묻는 창이 표시됩니다.
- **파일이 없는 경우**: 새 프로젝트로 시작합니다.

![이전 어노테이션 파일 감지 확인 다이얼로그](images/02_autofind_dialog.png)

---

[← 1. 인터페이스 개요](01_overview.md) | [다음: 벽 어노테이션 →](03_wall_annotation.md)
