---
phase: 05-deprecation-awareness
plan: 01
subsystem: parser
tags: [xml, deprecation, dataclass, stdlib-et]

requires:
  - phase: 01-foundation
    provides: AttDef/ElementDef models and ODD parser
provides:
  - AttDef.valid_until and AttDef.deprecation_info fields
  - ElementDef.valid_until and ElementDef.deprecation_info fields
  - _extract_deprecation() and _inner_xml() parser helpers
affects: [05-02-deprecation-surfacing]

tech-stack:
  added: []
  patterns: [_extract_deprecation shared helper, _inner_xml for inline markup preservation]

key-files:
  created: []
  modified:
    - src/tei_mcp/models.py
    - src/tei_mcp/parser.py
    - tests/fixtures/test_odd.xml
    - tests/test_parser.py

key-decisions:
  - "Used re.sub to strip namespace prefixes from _inner_xml output rather than manual string manipulation"
  - "Generic fallback message pattern: 'Deprecated as of {date}. No migration guidance available.'"

patterns-established:
  - "_extract_deprecation() returns (str, str) tuple, shared across parse functions"
  - "Deprecation fields use empty-string defaults for backward compatibility"

requirements-completed: [DEPR-04]

duration: 3min
completed: 2026-03-15
---

# Phase 5 Plan 1: Deprecation Data Extraction Summary

**Parser extracts @validUntil and desc[@type='deprecationInfo'] into AttDef/ElementDef fields with inline XML preservation and generic fallback**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T12:28:56Z
- **Completed:** 2026-03-15T12:31:38Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added valid_until and deprecation_info fields to AttDef and ElementDef with empty-string defaults (backward compatible)
- Implemented _extract_deprecation() helper that reads @validUntil and desc[@type='deprecationInfo'] with English preference
- Implemented _inner_xml() helper that preserves inline XML markup (e.g. `<gi>entry</gi>`) without namespace pollution
- Generic fallback message when no deprecationInfo desc exists

## Task Commits

Each task was committed atomically:

1. **Task 1: Add deprecated fixtures and write failing parser tests (RED)** - `c012e8e` (test)
2. **Task 2: Implement model fields and parser extraction (GREEN)** - `c696331` (feat)

_TDD plan: RED then GREEN commits._

## Files Created/Modified
- `src/tei_mcp/models.py` - Added valid_until and deprecation_info fields to AttDef and ElementDef
- `src/tei_mcp/parser.py` - Added _inner_xml(), _extract_deprecation() helpers; wired into _parse_att_def() and _parse_element_spec()
- `tests/fixtures/test_odd.xml` - Added deprecated elements (re, superEntry), classSpec (att.ref) with deprecated attDef, and attRef element
- `tests/test_parser.py` - Added 5 deprecation tests; updated entity counts
- `tests/test_models.py` - Updated asdict assertion for new default fields
- `tests/test_server.py` - Updated entity counts for expanded fixture
- `tests/test_store_query.py` - Updated att.global member count for new attRef element

## Decisions Made
- Used re.sub to strip namespace prefixes from _inner_xml output (ns0: and xmlns:ns0 patterns)
- Generic fallback message follows pattern "Deprecated as of {date}. No migration guidance available." for elements without deprecationInfo desc

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated hardcoded entity counts in test_models.py**
- **Found during:** Task 2 (GREEN)
- **Issue:** test_serializes_via_asdict expected dict without new default fields
- **Fix:** Added valid_until and deprecation_info to expected dict
- **Files modified:** tests/test_models.py

**2. [Rule 1 - Bug] Updated hardcoded entity counts in test_server.py**
- **Found during:** Task 2 (GREEN)
- **Issue:** test_lifespan_loads_store had old element/class counts (12/13 vs 15/14)
- **Fix:** Updated counts to match expanded fixture
- **Files modified:** tests/test_server.py

**3. [Rule 1 - Bug] Updated hardcoded member count in test_store_query.py**
- **Found during:** Task 2 (GREEN)
- **Issue:** test_get_class_members expected 12 att.global members, now 13 with attRef
- **Fix:** Updated count to 13
- **Files modified:** tests/test_store_query.py

---

**Total deviations:** 3 auto-fixed (3 Rule 1 bugs)
**Impact on plan:** All auto-fixes necessary due to expanded fixture. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Deprecation fields are extracted and available on models
- Plan 02 can surface deprecation warnings in MCP tool responses
- All 133 tests pass with no regressions

---
*Phase: 05-deprecation-awareness*
*Completed: 2026-03-15*
