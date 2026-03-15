---
phase: 07-core-validation
plan: 02
subsystem: validation
tags: [lxml, tei, xml-validation, content-model, ref-integrity, deprecation]

# Dependency graph
requires:
  - phase: 07-core-validation/01
    provides: TEIValidator scaffold with validate_file, _strip_ns, _strip_ns_attr
  - phase: 04-content-model
    provides: OddStore with valid_children, resolve_attributes, get_element
provides:
  - 7 validation check methods in TEIValidator (_check_content_model, _check_required_children, _check_attributes, _check_empty, _check_refs, _check_deprecation, _collect_ids)
  - Authority file cross-referencing for ref-integrity
affects: [07-03, 08-odd-customisation]

# Tech tracking
tech-stack:
  added: []
  patterns: [per-element check dispatch in validate_file loop, id collection before element walk for ref checking]

key-files:
  created: []
  modified: [src/tei_mcp/validator.py, tests/test_validator.py]

key-decisions:
  - "Warning severity for required-children (not error) because ordering/alternation makes detection fuzzy"
  - "Only ref and target attributes checked for ref-integrity (most common; expandable later)"
  - "Bare '#' is warning not error per CONTEXT.md specification"

patterns-established:
  - "Each validation check is a private method appending to issues list -- testable in isolation"
  - "id_set collected before element walk and passed to _check_refs for O(1) lookups"

requirements-completed: [VALD-02, VALD-03, VALD-04, VALD-05, VALD-06, VALD-07, DEPR-03]

# Metrics
duration: 4min
completed: 2026-03-15
---

# Phase 7 Plan 2: Validation Checks Summary

**7 validation check methods (content-model, required-children, unknown-attribute, closed-value-list, empty-element, ref-integrity, deprecation) wired into TEIValidator.validate_file**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T15:01:57Z
- **Completed:** 2026-03-15T15:06:03Z
- **Tasks:** 2 (both TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- All 7 validation check types implemented as private methods on TEIValidator
- Reference integrity with xml:id collection, bare-hash warnings, and authority file support
- Deprecation warnings for both elements and attributes using _build_deprecation_obj
- Content model, attribute validity, closed value list, and empty element checks using OddStore query methods
- 20 new tests (27 total validator tests), 190 full suite green

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Content model/attribute/empty tests** - `bda771a` (test)
2. **Task 1 GREEN: Content model/attribute/empty implementation** - `b5086c5` (feat)
3. **Task 2 RED: Ref integrity/deprecation tests** - `31347c7` (test)
4. **Task 2 GREEN: Ref integrity/deprecation implementation** - `d13ed16` (feat)

_TDD tasks: RED then GREEN commits for each task_

## Files Created/Modified
- `src/tei_mcp/validator.py` - Added 7 check methods, _collect_ids, authority file handling, wired all checks into validate_file loop
- `tests/test_validator.py` - 20 new test functions covering all 7 check types

## Decisions Made
- Warning severity for required-children (not error) -- ordering/alternation in content models makes exact cardinality checking fuzzy
- Only check ref and target attributes for reference integrity -- covers vast majority of real-world cases per RESEARCH.md recommendation
- Import _build_deprecation_obj from store module (single source of truth for deprecation logic)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 7 validation check types functional in validate_file
- Ready for Plan 03 to add MCP tool wrappers (validate_document, validate_element)
- Authority file support ready for cross-file reference checking

## Self-Check: PASSED

- FOUND: src/tei_mcp/validator.py (341 lines)
- FOUND: tests/test_validator.py (478 lines)
- FOUND: bda771a (Task 1 RED commit)
- FOUND: b5086c5 (Task 1 GREEN commit)
- FOUND: 31347c7 (Task 2 RED commit)
- FOUND: d13ed16 (Task 2 GREEN commit)

---
*Phase: 07-core-validation*
*Completed: 2026-03-15*
