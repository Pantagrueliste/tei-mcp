---
phase: 07-core-validation
plan: 01
subsystem: validation
tags: [lxml, tei, xml-parsing, validator, namespace]

# Dependency graph
requires:
  - phase: 04-content-model
    provides: OddStore with valid_children, resolve_attributes, get_element
provides:
  - TEIValidator class with validate_file method
  - _strip_ns and _strip_ns_attr namespace utilities
  - LIMITATIONS constant for response disclosure
  - _build_summary issue aggregation
affects: [07-02, 07-03, 08-odd-customisation]

# Tech tracking
tech-stack:
  added: [lxml>=5.0]
  patterns: [TEIValidator as OddStore consumer, namespace stripping before store lookups]

key-files:
  created: [src/tei_mcp/validator.py, tests/test_validator.py]
  modified: [pyproject.toml]

key-decisions:
  - "TEIValidator is a separate module consuming OddStore, not extending it"
  - "lxml for user document parsing (sourceline), stdlib ET unchanged for ODD spec"
  - "LIMITATIONS constant included in every response per VALD-09"

patterns-established:
  - "Namespace stripping: _strip_ns for element tags, _strip_ns_attr for xml: namespace attributes"
  - "Validator response shape: {issues: [], summary: {total, by_severity, by_rule}, limitations: {}}"

requirements-completed: [VALD-01, VALD-09]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 7 Plan 1: Validator Scaffold Summary

**TEIValidator class with lxml parsing, validate_file returning {issues, summary, limitations}, and namespace stripping utilities**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T14:57:40Z
- **Completed:** 2026-03-15T14:59:17Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- TEIValidator class scaffold with validate_file method parsing XML via lxml
- Namespace stripping utilities (_strip_ns, _strip_ns_attr) for TEI and xml: namespaces
- LIMITATIONS constant documenting 5 areas not checked (Schematron, datatypes, ordering, PIs, non-TEI)
- Summary builder aggregating issues by severity and rule type
- lxml>=5.0 added as project dependency

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: TEIValidator scaffold tests** - `ee34631` (test)
2. **Task 1 GREEN: TEIValidator implementation** - `dc0caac` (feat)

## Files Created/Modified
- `src/tei_mcp/validator.py` - TEIValidator class with validate_file, _strip_ns, _strip_ns_attr, LIMITATIONS, _build_summary
- `tests/test_validator.py` - 7 unit tests for validator scaffold
- `pyproject.toml` - Added lxml>=5.0 dependency

## Decisions Made
- TEIValidator as separate module consuming OddStore (not extending store.py) -- clean separation of concerns
- lxml used only for user document parsing; stdlib ET unchanged for ODD spec parsing
- Element walk loop present as skeleton with no check methods called yet (Plan 02 adds checks)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Validator scaffold ready for Plan 02 to add check methods (_check_content_model, _check_attributes, etc.)
- Element iteration loop in validate_file ready to call check methods
- Namespace stripping utilities ready for use in all check methods

## Self-Check: PASSED

- FOUND: src/tei_mcp/validator.py
- FOUND: tests/test_validator.py
- FOUND: ee34631 (RED commit)
- FOUND: dc0caac (GREEN commit)

---
*Phase: 07-core-validation*
*Completed: 2026-03-15*
