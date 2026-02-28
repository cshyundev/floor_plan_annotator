# Floor Plan Annotator

## Commands
- Test: `python3 -m pytest tests/ -v`
- Run: `python3 -m src.main`

## Project rules
- Domain-specific coding rules are in `.claude/rules/`
- Always check `.claude/rules/` before modifying GUI or model code

## Dev Process

Plan → Implement → Commit.
- **Plan**: read related REQ in `specs/requirements/`, state affected REQ. New feature: `/add-req` first
- **Implement**: code + tests. `python3 -m pytest tests/ -v` must pass before commit
- **Commit**: update `/changelog`, then commit. Bug fix: `/changelog` only (no REQ update needed)

## Status Entries (`/status`)

When adding Bug / Improvement / Feature entries to `specs/status/index.md`:
- Focus on: **제목**, **관련 영역**, **관련 REQ**
- Do **not** describe solution methods or implementation approaches unless the user explicitly requests it
- 비고(Notes) column: symptom or brief context only

## When to Plan vs. Fix Directly

- **Fix directly**: trivial, isolated bug (single file, obvious cause, low risk)
- **Plan first**: if the fix touches multiple files, requires architectural decisions, or the root cause is unclear → always go through the Plan agent **even mid-task**. Do NOT rush into code changes.
