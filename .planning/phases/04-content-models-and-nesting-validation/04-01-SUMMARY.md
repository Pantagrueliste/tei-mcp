---
phase: 04-content-models-and-nesting-validation
plan: 01
subsystem: api
tags: [xml, content-model, tree-parsing, bfs, odd]

requires:
  - phase: 01-foundation
    provides: "OddStore, ElementDef, MacroDef with content_raw, parser"
  - phase: 02-element-and-module-lookups
    provides: "Case-insensitive lookup, reverse indexes, suggest_names"
provides:
  - "expand_content_model() for elements and macros"
  - "_parse_content_tree() XML-to-dict tree parser"
  - "_resolve_class_to_elements() BFS class resolution with via annotations"
  - "_collect_direct_children() for nesting validation"
  - "Enriched test fixture with 12 elements and 13 classes"
affects: [04-02-nesting-validation]

tech-stack:
  added: [xml.etree.ElementTree for content model parsing]
  patterns: [tag-dispatch content parser, BFS class resolution, macro inline resolution with cycle detection]

key-files:
  created: []
  modified:
    - src/tei_mcp/store.py
    - tests/fixtures/test_odd.xml
    - tests/test_store_query.py
    - tests/test_parser.py
    - tests/test_server.py

key-decisions:
  - "MacroRef nodes resolved inline (replaced by macro content tree) rather than kept as references"
  - "ClassRef via field tracks the class where the member was found for useful provenance"
  - "Sentinel _ANY='*' used for anyElement in _collect_direct_children"

patterns-established:
  - "Content model tree format: {type, min, max, children} for containers; {type, class, elements} for classRef"
  - "Macro resolution with visited_macros set for cycle detection"

requirements-completed: [CMOD-01, CMOD-02, CMOD-03]

duration: 3min
completed: 2026-03-14
---

# Phase 4 Plan 1: Content Model Expansion Summary

**ODD XML content model expansion engine with classRef BFS resolution, inline macro resolution, and structured JSON tree output**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T23:49:25Z
- **Completed:** 2026-03-14T23:52:52Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Enriched test fixture from 3 to 12 elements and 4 to 13 classes with full content model data
- Implemented expand_content_model() returning nested JSON trees with sequence, alternation, classRef, element, text, empty, dataRef node types
- ClassRef nodes resolve to concrete elements via BFS with via annotations showing source class
- MacroRef nodes resolved inline with cycle detection (no macroRef in output)
- All 114 tests pass including 9 new content model expansion tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Enrich test fixture and write content model expansion tests** - `04e0686` (test)
2. **Task 2: Implement content model expansion engine in OddStore** - `01c07b3` (feat)

## Files Created/Modified
- `tests/fixtures/test_odd.xml` - Enriched with body, head, hi, note, gap, gi, surname, forename, roleName elements and 9 model classes
- `src/tei_mcp/store.py` - Added expand_content_model, _parse_content_tree, _parse_node, _resolve_class_to_elements, _collect_direct_children, _collect_elements_from_tree
- `tests/test_store_query.py` - 9 new content model tests, updated counts for enriched fixture
- `tests/test_parser.py` - Updated entity counts for enriched fixture
- `tests/test_server.py` - Updated entity counts for enriched fixture

## Decisions Made
- MacroRef nodes resolved inline (output tree never contains macroRef type, replaced by macro's content tree)
- ClassRef via field tracks the class where the member was found, not the original class queried
- Sentinel `_ANY = "*"` used in _collect_direct_children for anyElement detection

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing test assertions for enriched fixture**
- **Found during:** Task 1
- **Issue:** Adding new elements/classes to test_odd.xml changed entity counts and class membership lists relied on by existing tests in test_parser.py, test_server.py, and test_store_query.py
- **Fix:** Updated hardcoded counts (element_count 3->12, class_count 4->13, module_count 2->4) and att.global membership assertions
- **Files modified:** tests/test_parser.py, tests/test_server.py, tests/test_store_query.py
- **Verification:** All 114 tests pass
- **Committed in:** 04e0686 (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added model.common classSpec to fixture**
- **Found during:** Task 1
- **Issue:** model.common was referenced by model.pLike's memberOf and div's content model but had no classSpec definition, preventing proper class resolution in content model expansion
- **Fix:** Added classSpec for model.common as a model class in the fixture
- **Files modified:** tests/fixtures/test_odd.xml
- **Verification:** classRef resolution for model.common now returns concrete elements
- **Committed in:** 04e0686 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Content model expansion engine ready for nesting validation (Plan 02)
- _collect_direct_children() method ready for use by nesting checker
- Enriched fixture provides sufficient element/class diversity for nesting tests

---
*Phase: 04-content-models-and-nesting-validation*
*Completed: 2026-03-14*
