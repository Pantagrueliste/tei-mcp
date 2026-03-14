---
phase: 04-content-models-and-nesting-validation
plan: 02
subsystem: api
tags: [nesting-validation, bfs, cycle-detection, mcp-tools, content-model]

requires:
  - phase: 04-content-models-and-nesting-validation
    provides: "expand_content_model, _collect_direct_children, _parse_content_tree, enriched test fixture"
  - phase: 01-foundation
    provides: "OddStore, ElementDef, parser, case-insensitive lookup, suggest_names"
provides:
  - "check_nesting() with direct and recursive modes"
  - "expand_content_model MCP tool"
  - "check_nesting MCP tool"
  - "BFS recursive reachability with cycle detection and path tracking"
affects: []

tech-stack:
  added: []
  patterns: [BFS reachability with path tracking, classRef provenance in nesting reason, thin MCP wrapper delegation]

key-files:
  created: []
  modified:
    - src/tei_mcp/store.py
    - src/tei_mcp/server.py
    - tests/test_store_query.py
    - tests/test_tools.py

key-decisions:
  - "BFS for recursive nesting uses visited set to handle self-referencing cycles (div contains model.divLike which includes div)"
  - "Direct nesting reason enriched with classRef provenance via _find_class_for_child tree walk"
  - "check_nesting combines direct and recursive in single method with recursive=False default"

patterns-established:
  - "Nesting validation returns structured dict with reason field for LLM self-correction"
  - "BFS path tracking via queue items of (element, path_list) tuples"

requirements-completed: [NEST-01, NEST-02, NEST-03]

duration: 2min
completed: 2026-03-14
---

# Phase 4 Plan 2: Nesting Validation and MCP Tool Wiring Summary

**Direct and recursive nesting validation with BFS cycle detection, plus expand_content_model and check_nesting MCP tools bringing total to 9 registered tools**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T23:55:03Z
- **Completed:** 2026-03-14T23:57:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Implemented check_nesting() with direct mode (parent-child validity) and recursive mode (BFS reachability with path tracking)
- Cycle detection handles self-referencing elements (div -> model.divLike -> div) without infinite loop
- Direct nesting reasons include classRef provenance (e.g., "p is allowed via classRef model.common")
- Wired expand_content_model and check_nesting as MCP tools, completing all Phase 4 tool registrations
- All 128 tests pass including 8 new unit tests and 6 new integration tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement check_nesting store method with tests (TDD)**
   - `2600827` (test) - RED: 8 failing nesting validation tests
   - `456a175` (feat) - GREEN: check_nesting implementation with all tests passing
2. **Task 2: Wire MCP tools and add integration tests** - `a410cb9` (feat)

## Files Created/Modified
- `src/tei_mcp/store.py` - Added check_nesting, _check_nesting_direct, _check_nesting_recursive, _find_class_for_child, _walk_tree_for_class
- `src/tei_mcp/server.py` - Added expand_content_model and check_nesting MCP tool registrations
- `tests/test_store_query.py` - 8 nesting validation unit tests
- `tests/test_tools.py` - 6 integration tests for the two new MCP tools

## Decisions Made
- BFS for recursive nesting uses visited set initialized with ancestor to handle self-referencing cycles
- Direct nesting enriches reason field by walking content tree to find which classRef the child came through
- check_nesting combines direct and recursive modes in a single method (recursive=False default) rather than separate tools

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 4 requirements (CMOD-01/02/03, NEST-01/02/03) complete
- 9 MCP tools registered covering element/class/macro lookup, module listing, search, attributes, class chains, content model expansion, and nesting validation
- Full test suite: 128 tests passing

---
*Phase: 04-content-models-and-nesting-validation*
*Completed: 2026-03-14*
