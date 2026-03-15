---
phase: 05-deprecation-awareness
plan: 02
subsystem: api
tags: [deprecation, mcp-tools, store, server]

requires:
  - phase: 05-deprecation-awareness
    provides: AttDef.valid_until/deprecation_info and ElementDef.valid_until/deprecation_info fields
provides:
  - _build_deprecation_obj() shared helper for deprecation dict construction
  - Deprecation-enriched resolve_attributes() output (list_attributes tool)
  - Deprecation-enriched lookup_element() with deprecated_attribute_count
  - Deprecation-enriched lookup_class() attribute-level deprecation
affects: []

tech-stack:
  added: []
  patterns: [_build_deprecation_obj shared helper, deprecation object absent-not-null pattern, raw field cleanup in asdict output]

key-files:
  created: []
  modified:
    - src/tei_mcp/store.py
    - src/tei_mcp/server.py
    - tests/test_store_query.py
    - tests/test_server.py

key-decisions:
  - "Imported _build_deprecation_obj from store into server rather than duplicating"
  - "Raw valid_until/deprecation_info popped from asdict output in server responses (internal-only fields)"
  - "FakeContext class pattern for testing server tool functions directly"

patterns-established:
  - "_build_deprecation_obj returns dict|None; caller adds key only if not None (absent-not-null)"
  - "Server pops raw internal fields from asdict and replaces with enriched objects"

requirements-completed: [DEPR-01, DEPR-02]

duration: 2min
completed: 2026-03-15
---

# Phase 5 Plan 2: Deprecation Surfacing Summary

**Deprecation objects surfaced in list_attributes, lookup_element, and lookup_class with expired/severity classification and deprecated_attribute_count**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T12:34:34Z
- **Completed:** 2026-03-15T12:36:32Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added _build_deprecation_obj() helper that constructs {expired, valid_until, severity, info} dicts
- resolve_attributes() now includes deprecation objects on deprecated attributes (both local and inherited)
- lookup_element() returns element-level deprecation object and deprecated_attribute_count
- lookup_class() returns attribute-level deprecation objects in its attributes list
- Raw valid_until/deprecation_info fields cleaned from server asdict output

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing integration tests (RED)** - `267bee8` (test)
2. **Task 2: Implement deprecation in store and server responses (GREEN)** - `8dc2fe5` (feat)

_TDD plan: RED then GREEN commits._

## Files Created/Modified
- `src/tei_mcp/store.py` - Added _build_deprecation_obj() helper; enriched resolve_attributes() with per-attribute deprecation
- `src/tei_mcp/server.py` - Imported _build_deprecation_obj; enriched lookup_element with deprecation + deprecated_attribute_count; enriched lookup_class with attribute deprecation; cleaned raw fields
- `tests/test_store_query.py` - Added test_resolve_attributes_deprecated and test_resolve_attributes_no_deprecation
- `tests/test_server.py` - Added FakeContext, test_lookup_element_deprecated, test_lookup_element_not_deprecated, test_lookup_element_deprecated_attr_count, test_lookup_class_deprecated_attr

## Decisions Made
- Imported _build_deprecation_obj from store.py into server.py (single source of truth vs duplication)
- Raw valid_until/deprecation_info fields popped from asdict output in server (internal-only, replaced by enriched deprecation object)
- Created FakeContext class in test_server.py for direct tool function testing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DEPR-01 (list_attributes flags deprecated attributes) complete
- DEPR-02 (lookup_element surfaces deprecation status) complete
- Phase 05 deprecation awareness fully implemented
- All 139 tests pass with no regressions

---
*Phase: 05-deprecation-awareness*
*Completed: 2026-03-15*
