---
phase: 06-enhanced-querying
plan: 03
subsystem: api
tags: [mcp, attribute-suggestion, keyword-search, tdd]

requires:
  - phase: 06-enhanced-querying
    provides: resolve_attributes store method, AttDef.desc on elements and classes
provides:
  - suggest_attribute() store method with keyword-based attribute search
  - _get_attr_description() helper for looking up AttDef.desc from source
  - suggest_attribute MCP tool registration
affects: [06-enhanced-querying]

tech-stack:
  added: []
  patterns: [keyword overlap scoring with tie-breaking by locality then alphabetical]

key-files:
  created: []
  modified:
    - src/tei_mcp/store.py
    - src/tei_mcp/server.py
    - tests/test_store_query.py
    - tests/test_server.py

key-decisions:
  - "_get_attr_description helper looks up desc from AttDef on element (local) or class (inherited)"
  - "Keyword overlap scoring: intersection of intent words with description words"
  - "Tie-breaking: score desc, then local-before-inherited, then alphabetical"

patterns-established:
  - "Attribute suggestion pattern: resolve all attrs, score by keyword overlap with descriptions, return ranked results"

requirements-completed: [QURY-04]

duration: 1min
completed: 2026-03-15
---

# Phase 6 Plan 3: Suggest Attribute Summary

**suggest_attribute tool finding relevant attributes by keyword-matching intent descriptions against AttDef.desc fields**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-15T13:53:55Z
- **Completed:** 2026-03-15T13:55:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Implemented _get_attr_description() helper to look up AttDef.desc from source element or class
- Implemented suggest_attribute() store method with keyword overlap scoring against attribute descriptions
- Registered suggest_attribute MCP tool delegating to store method
- 7 unit tests + 1 MCP tool integration test covering basic search, description fields, result limits, no-match, not-found, and ranking

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing suggest_attribute tests (RED)** - `bcefd36` (test)
2. **Task 2: Implement suggest_attribute store method and MCP tool (GREEN)** - `4d23f2c` (feat)

## Files Created/Modified
- `src/tei_mcp/store.py` - Added _get_attr_description() helper and suggest_attribute() method
- `src/tei_mcp/server.py` - Added suggest_attribute MCP tool registration
- `tests/test_store_query.py` - Added 7 suggest_attribute unit tests
- `tests/test_server.py` - Added suggest_attribute MCP tool integration test

## Decisions Made
- _get_attr_description looks up AttDef.desc from element (local) or class (inherited source)
- Keyword overlap scoring: intersection of re.findall words from intent and description
- Tie-breaking: score descending, local-before-inherited, then alphabetical by name

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- suggest_attribute completes the enhanced querying phase (3/3 plans)
- All 163 tests pass with no regressions
- Phase 6 tools ready: valid_children, check_nesting_batch, suggest_attribute

---
*Phase: 06-enhanced-querying*
*Completed: 2026-03-15*
