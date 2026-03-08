# 9. 타입 관리

타입 관리자(Manage Types)를 사용하면 방, 구역, 객체의 타입 목록과 색상을 자유롭게 편집할 수 있습니다. 변경사항은 즉시 캔버스에 반영됩니다.

---

## 9.1 타입 관리자 열기

메뉴바에서 `Tools > Manage Types...` 선택

![타입 관리자 다이얼로그 — 세 탭(Room Types, Zone Types, Object Types)](images/09_type_manager_overview.png)

---

## 9.2 탭 구성

타입 관리자는 세 탭으로 구성됩니다.

| 탭 | 관리 대상 | 설정 파일 |
|----|-----------|-----------|
| **Room Types** | 방 어노테이션 타입 | `config/rooms.yaml` |
| **Zone Types** | 구역 어노테이션 타입 | `config/custom_polygons.yaml` |
| **Object Types** | 객체 어노테이션 타입 | `config/objects.yaml` |

---

## 9.3 타입 목록 보기

각 탭을 선택하면 현재 정의된 타입 목록이 표시됩니다. 각 타입 항목에는 다음 정보가 표시됩니다.

- **색상 미리보기**: 채우기 색상과 테두리 색상
- **타입 이름**

![Room Types 탭 — 타입 목록과 색상 미리보기](images/09_room_types_list.png)

---

## 9.4 타입 추가

1. 탭 하단의 **이름 입력 필드**에 새 타입 이름을 입력합니다.
2. **Add** 버튼을 클릭합니다.
3. 새 타입이 목록에 추가됩니다.

![타입 추가 — 이름 입력 후 Add 버튼 클릭](images/09_add_type.png)

> **참고**: 이미 존재하는 이름은 추가되지 않습니다.

---

## 9.5 색상 변경

타입의 채우기 색상 또는 테두리 색상을 변경합니다.

1. 목록에서 타입을 선택합니다.
2. **Fill Color** 또는 **Border Color** 버튼을 클릭합니다.
3. 색상 선택기에서 원하는 색상을 선택하고 확인합니다.
4. 캔버스의 모든 해당 타입 어노테이션이 즉시 새 색상으로 업데이트됩니다.

![색상 선택기 — RGB 및 투명도 설정](images/09_color_picker.png)

변경사항은 앱 재시작 없이 즉시 적용됩니다.

---

## 9.6 타입 삭제

1. 목록에서 삭제할 타입을 선택합니다.
2. **Delete** 버튼을 클릭합니다.
3. 확인 대화가 표시되면 확인합니다.

![타입 삭제 확인 다이얼로그](images/09_delete_type_confirm.png)

> **주의**: 삭제된 타입이 적용된 기존 어노테이션은 기본(폴백) 색상으로 표시됩니다. 어노테이션 자체는 삭제되지 않습니다.

---

## 9.7 Object Types 추가 설정

객체 타입에는 방/구역 타입과 달리 3D 관련 기본값이 추가로 있습니다.

| 설정 | 설명 | 예시 |
|------|------|------|
| **Default Elevation** | 객체 바닥이 바닥에서 얼마나 높은지 (미터) | 0.0 (바닥에 놓임) |
| **Default 3D Height** | 객체의 기본 높이 (미터) | 0.5 |

![Object Types — Elevation, 3D Height 설정 필드](images/09_object_type_settings.png)

새 객체를 그릴 때 해당 타입의 기본값이 자동으로 적용됩니다.

---

## 9.8 설정 파일과의 관계

타입 관리자에서 변경한 내용은 다음 파일에 즉시 저장됩니다.

```
config/
├── rooms.yaml          — 방 타입 정의
├── custom_polygons.yaml — 구역 타입 정의
└── objects.yaml        — 객체 타입 정의
```

이 파일들을 직접 편집할 수도 있지만, 타입 관리자를 사용하는 것이 권장됩니다. 파일을 직접 편집한 경우 프로그램을 재시작해야 변경사항이 반영됩니다.

---

## 9.9 기본 타입 목록

### 방 타입 (Room Types)

| 타입 키 | 표시 이름 |
|---------|----------|
| `living_room` | Living Room |
| `bedroom` | Bedroom |
| `master_room` | Master Room |
| `kitchen` | Kitchen |
| `bathroom` | Bathroom |
| `corridor` | Corridor |
| `entrance` | Entrance |
| `balcony` | Balcony |
| `utility` | Utility |

### 구역 타입 (Zone Types)

| 타입 키 | 표시 이름 |
|---------|----------|
| `clean_zone` | Clean Zone |
| `danger_zone` | Danger Zone |
| `complex_zone` | Complex Zone |
| `annotation` | annotation |

### 객체 타입 (Object Types)

| 타입 키 | 표시 이름 |
|---------|----------|
| `furniture` | Furniture |
| `table` | Table |
| `appliance` | Appliance |
| `obstacle` | Obstacle |

---

[← 8. 스냅 및 정렬](08_snap_align.md) | [다음: 파일 관리 →](10_file_management.md)
