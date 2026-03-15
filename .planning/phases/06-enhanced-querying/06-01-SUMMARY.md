---
phase: 06-enhanced-querying
plan: 01
subsystem: api
tags: [mcp, content-model, querying, tdd]

requires:
  - phase: 04-content-models
    provides: _parse_content_tree, _collect_direct_children, content model tree structure
provides:
  - valid_children() store method returning flat deduplicated child list with required flags
  - valid_children MCP tool registration
  - _collect_children_with_metadata() helper for content tree walking with context tracking
affects: [06-enhanced-querying]

tech-stack:
  added: []
  patterns: [context_min propagation for required flag semantics through alternation/sequence]

key-files:
  created: []
  modified:
    - src/tei_mcp/store.py
    - src/tei_mcp/server.py
    - tests/test_store_query.py
    - tests/test_server.py
    - tests/fixtures/test_odd.xml
    - tests/test_parser.py

key-decisions:
  - "context_min=0 inside alternation nodes makes all children optional (no single branch is required)"
  - "anyElement returns allows_any_element=True with empty children list instead of listing all elements"
  - "Children sorted alphabetically for stable, predictable output"

patterns-established:
  - "context_min propagation: multiply node min by context_min to determine effective required status through nested sequence/alternation"

requirements-completed: [QURY-01, QURY-02]

duration: 2min
completed: 2026-03-15
---

# Phase 6 Plan 1: Valid Children Summary

**valid_children tool returning flat deduplicated child list with required/optional flags, text/anyElement/empty indicators**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T13:45:36Z
- **Completed:** 2026-03-15T13:47:46Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Implemented valid_children() store method with _collect_children_with_metadata() helper that walks content model trees tracking required flags through alternation/sequence context
- Registered valid_children MCP tool for instant "what can go inside <X>?" queries
- Added egXML fixture element with anyElement content model for comprehensive test coverage
- 10 unit tests covering basic, deduplication, required flag, alternation, text, empty, anyElement, not-found, sorted output, and MCP tool delegation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add anyElement fixture element and write failing valid_children tests (RED)** - `73f9b33` (test)
2. **Task 2: Implement valid_children store method and MCP tool (GREEN)** - `cf844b7` (feat)

## Files Created/Modified
- `src/tei_mcp/store.py` - Added valid_children() method and _collect_children_with_metadata() helper
- `src/tei_mcp/server.py` - Added valid_children MCP tool registration
- `tests/test_store_query.py` - Added 9 valid_children unit tests
- `tests/test_server.py` - Added valid_children MCP tool integration test
- `tests/fixtures/test_odd.xml` - Added egXML elementSpec with anyElement content model
- `tests/test_parser.py` - Updated element count for new fixture element

## Decisions Made
- context_min=0 inside alternation nodes ensures all children are optional (correct semantics: no single alternation branch is required)
- anyElement returns allows_any_element=True with empty children list rather than enumerating all possible elements
- Children sorted alphabetically by name for stable, predictable output

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated parser test element count**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** test_parser.py hardcoded element_count=15, but adding egXML fixture made it 16
- **Fix:** Updated assertion from 15 to 16
- **Files modified:** tests/test_parser.py
- **Verification:** Full test suite passes (149 tests)
- **Committed in:** cf844b7 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial count update required by adding new fixture element. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- valid_children provides foundation for check_nesting_batch (plan 06-02) and suggest_attribute (plan 06-03)
- _collect_children_with_metadata pattern can be reused for enriching other query tools
- All 149 tests pass with no regressions

---
*Phase: 06-enhanced-querying*
*Completed: 2026-03-15*
