---
phase: 02-basic-lookups-and-search
plan: 01
subsystem: api
tags: [python, dataclass, regex, difflib, search, reverse-index]

requires:
  - phase: 01-foundation
    provides: OddStore with dict-based entity storage, ElementDef/ClassDef/MacroDef/ModuleDef models
provides:
  - Case-insensitive lookup for all entity types
  - Class members reverse index (class -> member idents)
  - Module elements reverse index (module -> ElementDef list)
  - Regex search across ident/gloss/desc with type filtering
  - Fuzzy name suggestions via difflib
affects: [02-basic-lookups-and-search]

tech-stack:
  added: [difflib, re]
  patterns: [generic CI lookup with TypeVar, reverse index built at init time, priority-ordered field matching]

key-files:
  created: [tests/test_store_query.py]
  modified: [src/tei_mcp/store.py, tests/conftest.py]

key-decisions:
  - "Reverse indexes built eagerly in __init__ for O(1) access"
  - "Search checks ident > gloss > desc in priority order, stops at first match per entity"
  - "suggest_names uses difflib.get_close_matches with cutoff=0.4 on lowercased names"

patterns-established:
  - "Generic _get_ci helper with TypeVar for case-insensitive lookup across any dict collection"
  - "Search returns list[dict] on success, dict on error (invalid regex)"

requirements-completed: [LOOK-01, LOOK-02, LOOK-03, LOOK-04, SRCH-01, SRCH-02]

duration: 2min
completed: 2026-03-14
---

# Phase 2 Plan 1: Store Query Methods Summary

**Case-insensitive lookup, reverse indexes, regex search, and fuzzy suggestions added to OddStore with 23 TDD tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T22:28:48Z
- **Completed:** 2026-03-14T22:30:25Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Case-insensitive lookup for elements, classes, macros, and modules via generic `_get_ci` helper
- Reverse indexes built at init: class members (class -> element/subclass idents) and module elements (module -> ElementDef list)
- Regex search across ident, gloss, desc fields with entity_type filter and max_results cap
- Fuzzy name suggestions using difflib.get_close_matches with lowercase normalization
- 23 new tests all passing, 56 total tests green with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add parsed_store fixture and write store query tests** - `4dd6186` (test) - TDD RED phase
2. **Task 2: Implement OddStore query methods** - `07b6772` (feat) - TDD GREEN phase

## Files Created/Modified
- `src/tei_mcp/store.py` - Added query methods: _get_ci, get_element_ci, get_class_ci, get_macro_ci, get_module_ci, get_class_members, get_module_elements, search, suggest_names
- `tests/test_store_query.py` - 23 unit tests covering all new query methods
- `tests/conftest.py` - Added parsed_store fixture using parse_odd on test_odd.xml

## Decisions Made
- Reverse indexes built eagerly in `__init__` for O(1) access at query time
- Search checks ident > gloss > desc in priority order, stops at first match per entity (no duplicates)
- `suggest_names` uses `difflib.get_close_matches` with cutoff=0.4 on lowercased names, mapping back to original-cased idents

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All store query methods ready for Plan 02 MCP tool wrappers
- search() and suggest_names() return structured dicts ready for JSON serialization

---
*Phase: 02-basic-lookups-and-search*
*Completed: 2026-03-14*
