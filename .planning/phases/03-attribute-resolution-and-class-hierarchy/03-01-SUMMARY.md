---
phase: 03-attribute-resolution-and-class-hierarchy
plan: 01
subsystem: api
tags: [dataclass, xml-parsing, bfs, attribute-resolution, class-hierarchy]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Frozen dataclass models (ElementDef, ClassDef), ODD parser, OddStore"
  - phase: 02-basic-lookups-and-search
    provides: "Case-insensitive lookup, suggest_names, search methods"
provides:
  - "AttDef frozen dataclass with datatype, values, closed fields"
  - "_parse_att_def() parser function extracting rich attribute data"
  - "resolve_attributes() method for local + inherited attribute resolution"
  - "get_class_chain() method for class membership chain traversal"
  - "Enriched test fixture with att.* sub-hierarchy and override scenario"
affects: [03-02-mcp-tools, phase-04-content-models]

# Tech tracking
tech-stack:
  added: [collections.deque]
  patterns: [BFS-hierarchy-walking, override-detection, local-first-ordering]

key-files:
  created: []
  modified:
    - src/tei_mcp/models.py
    - src/tei_mcp/parser.py
    - src/tei_mcp/store.py
    - tests/fixtures/test_odd.xml
    - tests/test_models.py
    - tests/test_parser.py
    - tests/test_store_query.py
    - tests/test_server.py

key-decisions:
  - "AttDef frozen dataclass placed before ElementDef in models.py for reference ordering"
  - "BFS (not DFS) for attribute inheritance ensures nearest-class-first ordering"
  - "Override detection scans visited att.* classes for matching ident after BFS completes"
  - "Semi-open valList (type='semi') sets closed=False -- only type='closed' is truly closed"

patterns-established:
  - "BFS hierarchy walking: deque-based with visited set for cycle detection"
  - "resolve_attributes returns flat list with source annotation and optional overrides field"
  - "get_class_chain returns separate chains per direct membership with per-chain visited set"

requirements-completed: [ATTR-01, ATTR-02, ATTR-03, HIER-01]

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 3 Plan 1: Attribute Resolution and Class Hierarchy Summary

**AttDef model with datatype/values/closed, BFS attribute resolution with local-first ordering and override detection, and class chain traversal with cycle protection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-14T23:11:55Z
- **Completed:** 2026-03-14T23:16:56Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- AttDef frozen dataclass with ident, desc, datatype, values, closed fields
- Parser enriched with _parse_att_def() extracting datatype (key= and name= paths) and valList data
- resolve_attributes() returns flat list: local attrs first (with override detection), then inherited in BFS order
- get_class_chain() returns separate chains per direct class membership with cycle detection
- Test fixture enriched with att.naming -> att.canonical sub-hierarchy and local override scenario (persName ref vs att.canonical ref)
- Full test suite: 96 tests passing (26 new tests added)

## Task Commits

Each task was committed atomically:

1. **Task 1: AttDef model, parser enrichment, fixture enrichment** - `ad6f852` (test: RED), `717e954` (feat: GREEN)
2. **Task 2: resolve_attributes and get_class_chain** - `0a2fe67` (test: RED), `a9dc95e` (feat: GREEN)

_TDD tasks have separate RED/GREEN commits._

## Files Created/Modified
- `src/tei_mcp/models.py` - Added AttDef dataclass; changed ElementDef.attributes and ClassDef.attributes to tuple[AttDef, ...]
- `src/tei_mcp/parser.py` - Added _parse_att_def() function; updated _parse_element_spec and _parse_class_spec to produce AttDef objects
- `src/tei_mcp/store.py` - Added resolve_attributes() and get_class_chain() methods with BFS and cycle detection
- `tests/fixtures/test_odd.xml` - Enriched with datatypes, att.naming/att.canonical sub-hierarchy, local override scenario
- `tests/test_models.py` - Added TestAttDef class; updated ElementDef/ClassDef tests for AttDef tuples
- `tests/test_parser.py` - Added 8 new tests for parser enrichment; updated existing tests for AttDef type
- `tests/test_store_query.py` - Added 14 new tests for resolve_attributes and get_class_chain
- `tests/test_server.py` - Updated class_count assertion for enriched fixture (2 -> 4)

## Decisions Made
- BFS (not DFS) for attribute inheritance ensures nearest-class-first ordering as specified
- Semi-open valList (type="semi") returns closed=False -- only type="closed" is truly closed
- Override detection: after BFS completes, scan visited att.* classes for matching local attr idents
- get_class_chain walks linearly through first superclass per level; multiple superclasses each start own chain

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_server.py class_count assertion**
- **Found during:** Task 1 (test fixture enrichment)
- **Issue:** test_server.py::test_lifespan_loads_store asserted class_count == 2, but enriched fixture now has 4 classes
- **Fix:** Updated assertion to class_count == 4
- **Files modified:** tests/test_server.py
- **Verification:** Full test suite passes
- **Committed in:** 717e954 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary update for existing test to match enriched fixture. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- resolve_attributes() and get_class_chain() are ready for MCP tool wrappers in Plan 02
- Store methods follow established patterns (case-insensitive lookup, error + suggestions)
- All 96 tests green, no regressions

---
*Phase: 03-attribute-resolution-and-class-hierarchy*
*Completed: 2026-03-14*
