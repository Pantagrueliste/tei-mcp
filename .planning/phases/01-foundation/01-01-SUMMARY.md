---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [uv, frozen-dataclass, httpx, pytest, tei-odd]

# Dependency graph
requires: []
provides:
  - "Python package skeleton installable via uv sync"
  - "Frozen dataclasses: ElementDef, ClassDef, MacroDef, ModuleDef"
  - "Async download logic with TEI_ODD_PATH env var override and URL fallback"
  - "Test infrastructure: conftest fixtures, test_odd.xml TEI ODD fixture"
affects: [01-02, phase-2]

# Tech tracking
tech-stack:
  added: [fastmcp>=3.1.0, httpx>=0.27, pytest>=8.0, pytest-asyncio>=0.24, hatchling]
  patterns: [frozen-dataclass, async-download-with-fallback, tdd]

key-files:
  created:
    - pyproject.toml
    - src/tei_mcp/__init__.py
    - src/tei_mcp/__main__.py
    - src/tei_mcp/models.py
    - src/tei_mcp/download.py
    - src/tei_mcp/data/.gitkeep
    - tests/conftest.py
    - tests/fixtures/test_odd.xml
    - tests/test_models.py
    - tests/test_download.py
  modified:
    - .gitignore

key-decisions:
  - "Used stdlib dataclasses with frozen=True for immutable data models (no pydantic needed)"
  - "TEI_ODD_PATH validates file existence before returning path"
  - "Test fixture includes multilingual gloss/desc (en + de) for downstream language filtering tests"

patterns-established:
  - "Frozen dataclass pattern: all parsed entities use @dataclass(frozen=True) with tuple fields"
  - "Download fallback pattern: try URLs in order, catch HTTPError, raise RuntimeError on total failure"
  - "TDD workflow: write failing tests first, then implement, verify green"

requirements-completed: [BOOT-01, BOOT-04, XCUT-02]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 1 Plan 01: Project Scaffold and Download Logic Summary

**Python package with frozen TEI data models, async p5subset.xml download with env var override and URL fallback, and 15 passing TDD tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T21:26:40Z
- **Completed:** 2026-03-14T21:29:34Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Scaffolded tei-mcp Python package with uv, fastmcp, httpx, and pytest dev deps
- Created four frozen dataclasses (ElementDef, ClassDef, MacroDef, ModuleDef) enforcing immutability
- Implemented async download logic with TEI_ODD_PATH env var override and two-URL fallback chain
- Built test infrastructure with realistic TEI ODD XML fixture (3 elements, 2 classes, 1 macro, 2 modules)

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold and frozen data models** - `e7e3998` (feat)
2. **Task 2: Download logic with env var override and URL fallback** - `920f4c6` (feat)

_Note: TDD tasks -- tests written first (RED), then implementation (GREEN), committed together._

## Files Created/Modified
- `pyproject.toml` - Project config with fastmcp, httpx deps, console script, pytest config
- `src/tei_mcp/__init__.py` - Package init with version
- `src/tei_mcp/__main__.py` - python -m tei_mcp support
- `src/tei_mcp/models.py` - Frozen dataclasses for ElementDef, ClassDef, MacroDef, ModuleDef
- `src/tei_mcp/download.py` - ODD file download with env var override and URL fallback
- `src/tei_mcp/data/.gitkeep` - Preserves data directory in repo
- `.gitignore` - Excludes p5subset.xml, __pycache__, .venv, etc.
- `tests/conftest.py` - test_odd_path and odd_xml_bytes fixtures
- `tests/fixtures/test_odd.xml` - Realistic TEI ODD XML with multilingual gloss/desc
- `tests/test_models.py` - 8 tests for frozen dataclass immutability and field storage
- `tests/test_download.py` - 7 tests for env var, download, fallback, and error scenarios

## Decisions Made
- Used stdlib dataclasses with frozen=True rather than pydantic -- simpler, no extra dependency, sufficient for immutable data contracts
- TEI_ODD_PATH validates file existence before returning path (raises FileNotFoundError with clear message)
- Test fixture includes both xml:lang="en" and xml:lang="de" gloss/desc on the `p` element to support downstream language filtering tests

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Package skeleton ready for parser (01-02) to add parser.py, store.py, server.py
- Frozen dataclasses provide the data contracts the parser will populate
- Download logic provides the file acquisition the server lifespan will call
- Test fixture ready for parser integration tests

## Self-Check: PASSED

All 11 created files verified present. Both task commits (e7e3998, 920f4c6) verified in git log. 15/15 tests passing.

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
