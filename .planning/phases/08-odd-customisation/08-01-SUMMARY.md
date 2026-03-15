---
phase: 08-odd-customisation
plan: 01
subsystem: api
tags: [xml, odd, customisation, dataclasses, pure-function]

requires:
  - phase: 04-content-models
    provides: OddStore with elements, classes, macros, modules dicts
provides:
  - apply_customisation pure function for ODD-based store filtering
  - moduleRef include/except element filtering
  - elementSpec delete and change (attribute modifications)
affects: [08-02-server-integration]

tech-stack:
  added: []
  patterns: [deep-copy-then-filter, frozen-dataclass-replace-merge]

key-files:
  created:
    - src/tei_mcp/customisation.py
    - tests/test_customisation.py
    - tests/fixtures/test_custom.odd
  modified:
    - tests/fixtures/test_odd.xml
    - tests/test_parser.py

key-decisions:
  - "Deep copy + filter pattern for constrained OddStore (not build from scratch)"
  - "Only filter elements dict; leave classes, macros, modules untouched"
  - "attDef mode=change merges fields (not replaces) using dataclasses.replace"

patterns-established:
  - "Pure function customisation: apply_customisation(base_store, odd_path) -> OddStore"
  - "schemaSpec found via .iter() to handle nested ODD documents"

requirements-completed: [ODDS-02, ODDS-03, ODDS-04, ODDS-05]

duration: 2min
completed: 2026-03-15
---

# Phase 8 Plan 1: ODD Customisation Core Logic Summary

**Pure function apply_customisation with moduleRef include/except filtering, elementSpec delete, and attDef change/delete/add using deep-copy-then-filter pattern**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T15:50:32Z
- **Completed:** 2026-03-15T15:52:50Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- apply_customisation returns a new OddStore constrained by ODD moduleRef and elementSpec directives
- moduleRef with include/except correctly filters elements per module
- elementSpec mode=delete removes elements; mode=change modifies attributes (valList restriction, delete, add)
- Base store provably unchanged after customisation (immutability via deep copy)
- 10 unit tests covering all customisation behaviors

## Task Commits

Each task was committed atomically:

1. **Task 1: Test fixture and failing tests (RED)** - `1115e72` (test)
2. **Task 2: Implement apply_customisation (GREEN)** - `bbf092e` (feat)

## Files Created/Modified
- `src/tei_mcp/customisation.py` - Core customisation logic: apply_customisation, _compute_allowed_elements, _apply_element_change, _modify_att_def
- `tests/test_customisation.py` - 10 unit tests covering moduleRef, elementSpec, attDef, immutability, error handling
- `tests/fixtures/test_custom.odd` - Minimal ODD customisation fixture with nested schemaSpec
- `tests/fixtures/test_odd.xml` - Added rend attribute to p element for valList restriction testing
- `tests/test_parser.py` - Updated attribute count assertion for new rend attribute

## Decisions Made
- Deep copy + filter pattern chosen over build-from-scratch (simpler, preserves all base data)
- Only elements dict is filtered; classes, macros, modules left untouched (OddStore BFS naturally skips missing elements)
- attDef mode=change uses merge semantics via dataclasses.replace (only overrides fields present in customisation)
- schemaSpec found via .iter() to handle ODD files nested inside full TEI document structure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added rend attribute to test_odd.xml fixture**
- **Found during:** Task 1 (test fixture creation)
- **Issue:** Plan specified attDef ident="rend" mode="change" for valList restriction test, but base store's p element had no rend attribute
- **Fix:** Added rend attDef to p in test_odd.xml with semi-closed valList (italic, bold, underline, strikethrough); updated test_parser.py assertion from 1 to 2 attributes
- **Files modified:** tests/fixtures/test_odd.xml, tests/test_parser.py
- **Verification:** Full test suite (211 tests) passes
- **Committed in:** 1115e72 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary fixture adjustment to support planned test scenarios. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- apply_customisation ready for server integration (08-02)
- Function signature matches planned load_customisation tool pattern
- All 211 tests pass (no regressions)

---
*Phase: 08-odd-customisation*
*Completed: 2026-03-15*
