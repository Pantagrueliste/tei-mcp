---
phase: 07-core-validation
plan: 03
subsystem: validation
tags: [lxml, tei, xml-validation, mcp-tools, element-validation]

# Dependency graph
requires:
  - phase: 07-core-validation/02
    provides: TEIValidator with 7 check methods and validate_file
  - phase: 04-content-model
    provides: OddStore with valid_children, resolve_attributes, get_element
provides:
  - validate_element method with dual input (XML snippet and structured dict)
  - validate_document MCP tool delegating to validate_file
  - validate_element MCP tool with JSON parsing for structured input
affects: [08-odd-customisation]

# Tech tracking
tech-stack:
  added: []
  patterns: [dual input detection (XML vs dict) by leading '<', JSON string parsing in MCP tool layer]

key-files:
  created: []
  modified: [src/tei_mcp/validator.py, src/tei_mcp/server.py, tests/test_validator.py, tests/test_tools.py]

key-decisions:
  - "XML vs structured input auto-detected by leading '<' character"
  - "MCP tool layer handles JSON string to dict conversion (MCP params are always strings)"
  - "validate_element skips ref-integrity (no document-level xml:id pool)"
  - "Validator created in lifespan alongside store, passed via lifespan_context"

patterns-established:
  - "Dual input format: XML snippet string or dict with name/attributes/children keys"
  - "All validate_element issues have line=None (no document context)"

requirements-completed: [VALD-10]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 7 Plan 3: Element Validation and MCP Tool Wiring Summary

**validate_element with dual XML/structured input and validate_document/validate_element MCP tools completing Phase 7**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T15:08:36Z
- **Completed:** 2026-03-15T15:11:54Z
- **Tasks:** 2 (Task 1 TDD, Task 2 auto)
- **Files modified:** 4

## Accomplishments
- validate_element method supporting XML snippet and structured dict input with nesting, attribute, empty, and deprecation checks
- Both validate_document and validate_element registered as MCP tools in server.py
- JSON string parsing in MCP tool layer for structured element input
- 11 new tests (201 total suite green)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: validate_element failing tests** - `c0c50cb` (test)
2. **Task 1 GREEN: validate_element implementation** - `64e7a56` (feat)
3. **Task 2: MCP tool registration** - `dca3039` (feat)

_TDD Task 1: RED then GREEN commits_

## Files Created/Modified
- `src/tei_mcp/validator.py` - Added validate_element method with dual input format (510 lines total)
- `src/tei_mcp/server.py` - Added validate_document and validate_element MCP tools, TEIValidator in lifespan
- `tests/test_validator.py` - 8 new validate_element tests (35 total)
- `tests/test_tools.py` - 3 new MCP tool integration tests

## Decisions Made
- XML vs structured input auto-detected by checking if string starts with '<'
- MCP tool layer converts JSON strings to dicts (MCP parameters are always strings)
- validate_element skips ref-integrity checks since there is no document-level xml:id pool
- TEIValidator instantiated in server lifespan and passed via lifespan_context dict

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test using fileDesc (not in test ODD fixture)**
- **Found during:** Task 1 GREEN
- **Issue:** Test used `<fileDesc/>` for invalid nesting but fileDesc is not in the test ODD fixture, so it was silently skipped
- **Fix:** Changed test to use `<div>` which IS in the test fixture but not a valid child of `<p>`
- **Files modified:** tests/test_validator.py
- **Committed in:** 64e7a56 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test correction necessary for valid RED/GREEN cycle. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 7 complete: all validation checks functional as MCP tools
- validate_document and validate_element accessible via MCP protocol
- Ready for Phase 8 (ODD customisation) which can build on TEIValidator

## Self-Check: PASSED

- FOUND: src/tei_mcp/validator.py (510 lines)
- FOUND: src/tei_mcp/server.py
- FOUND: tests/test_validator.py
- FOUND: tests/test_tools.py
- FOUND: c0c50cb (Task 1 RED commit)
- FOUND: 64e7a56 (Task 1 GREEN commit)
- FOUND: dca3039 (Task 2 commit)

---
*Phase: 07-core-validation*
*Completed: 2026-03-15*
