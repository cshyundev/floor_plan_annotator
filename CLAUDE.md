# Floor Plan Annotator

## Commands
- Test: `python3 -m pytest tests/ -v`
- Run: `python3 -m src.main`

## Project rules
- Domain-specific coding rules are in `.claude/rules/`
- Always check `.claude/rules/` before modifying GUI or model code

## 필수 개발 프로세스

모든 코드 변경 시 아래 단계를 순서대로 따른다.

### Step 1: 계획 (Plan)
- 코드 변경 전 Plan 모드로 진입
- `specs/requirements/index.md`에서 관련 요구사항(REQ-XXX)을 찾아 읽기
- 영향받는 REQ 번호를 사용자에게 명시
- 기존 요구사항과의 충돌 여부 확인

### Step 2: 요구사항 업데이트 (Specs)
- 새 기능이면 `/add-req` 스킬로 요구사항 추가
- 기존 기능 변경이면 해당 REQ 문서 업데이트
- 버그 수정은 REQ 업데이트 불필요 (changelog만 기록)

### Step 3: 개발 (Code)
- `.claude/rules/` 규칙 준수
- 한 번에 하나의 기능/버그만 처리
- 변경 완료 후 커밋

### Step 4: 테스트 (Test)
- `python3 -m pytest tests/ -v` 실행하여 전체 테스트 통과 확인
- 새 기능이면 테스트 케이스 추가 (senior-test-engineer 에이전트 활용)
- 테스트 실패 시 Step 3으로 돌아가 수정

### Step 5: 검증 및 리팩토링 (Verify)
- spec-compliance-reviewer 에이전트로 스펙 준수 검증
- `/changelog` 스킬로 변경 이력 기록
- 필요 시 `/refactor` 스킬로 리팩토링 점검
