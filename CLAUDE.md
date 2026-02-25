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
