---
phase: 01-foundation
plan: 02
subsystem: api
tags: [xml-parser, elementtree, fastmcp, mcp-server, tei-odd, lifespan]

# Dependency graph
requires:
  - phase: 01-foundation-01
    provides: "Frozen dataclasses, download logic, test fixtures"
provides:
  - "parse_odd(path) function parsing TEI ODD XML into OddStore"
  - "OddStore with O(1) dict-based lookup for elements, classes, macros, modules"
  - "FastMCP server shell with lifespan-based data loading"
  - "main() entry point for tei-mcp console script"
affects: [phase-2, phase-3, phase-4]

# Tech tracking
tech-stack:
  added: []
  patterns: [xml-namespace-aware-parsing, lifespan-context-manager, stderr-only-logging]

key-files:
  created:
    - src/tei_mcp/parser.py
    - src/tei_mcp/store.py
    - src/tei_mcp/server.py
    - tests/test_parser.py
    - tests/test_server.py
  modified: []

key-decisions:
  - "Used xml:lang attribute filtering via full namespace URI ({http://www.w3.org/XML/1998/namespace}lang) since ElementTree XPath does not resolve the xml: prefix in predicates"
  - "Lifespan decorated with @lifespan from fastmcp.server.lifespan, yielding store dict to context"
  - "Logging configured to stderr as the very first action in server.py, before any other imports"

patterns-established:
  - "XML namespace handling: NS dict with tei/rng prefixes, _XML_LANG constant for xml:lang attribute"
  - "Lifespan pattern: ensure_odd_file -> parse_odd -> yield {store} in context"
  - "No-stdout guarantee: logging.basicConfig(stream=sys.stderr) before all imports"

requirements-completed: [BOOT-02, BOOT-03, XCUT-01, XCUT-03]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 1 Plan 02: ODD Parser, Store, and MCP Server Summary

**TEI ODD XML parser with English-filtered gloss/desc, O(1) OddStore, and FastMCP server shell with lifespan-based data loading -- 33 tests passing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T21:32:22Z
- **Completed:** 2026-03-14T21:35:38Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- ODD XML parser correctly extracts all four TEI entity types (elements, classes, macros, modules) with English language filtering
- OddStore provides O(1) dict-based lookup for all entity types with count properties
- FastMCP server shell starts with lifespan that chains download -> parse -> store -> context
- Full Phase 1 test suite: 33 tests all green (models, download, parser, server)

## Task Commits

Each task was committed atomically:

1. **Task 1: ODD XML parser and in-memory store** - `1fdf5ae` (feat)
2. **Task 2: FastMCP server shell with lifespan** - `c835a41` (feat)

_Note: TDD tasks -- tests written first (RED), then implementation (GREEN), committed together._

## Files Created/Modified
- `src/tei_mcp/parser.py` - parse_odd() with namespace-aware XML parsing, English gloss/desc filtering, content_raw capture
- `src/tei_mcp/store.py` - OddStore class with dict-based indexes and O(1) lookup methods
- `src/tei_mcp/server.py` - FastMCP "tei-mcp" server with lifespan hook and stderr-only logging
- `tests/test_parser.py` - 13 tests for parser entity extraction, language selection, store lookups
- `tests/test_server.py` - 5 tests for logging, server name, stdout safety, lifespan, main entry point

## Decisions Made
- Used full namespace URI `{http://www.w3.org/XML/1998/namespace}lang` for xml:lang attribute filtering because ElementTree XPath does not resolve the `xml:` prefix in attribute predicates
- Lifespan uses `@lifespan` decorator from `fastmcp.server.lifespan` (confirmed working with FastMCP 3.1.x)
- Logging configured to stderr as the very first action in server.py, before any FastMCP or project imports, to guarantee no stdout contamination

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed xml:lang XPath predicate handling**
- **Found during:** Task 1 (parser implementation)
- **Issue:** ElementTree raises SyntaxError on `[@xml:lang="en"]` because it cannot resolve the `xml:` prefix in XPath predicates without it being in the namespace map
- **Fix:** Replaced XPath predicate approach with explicit iteration over candidates checking `el.get(_XML_LANG) == "en"` using the full namespace URI constant
- **Files modified:** src/tei_mcp/parser.py
- **Verification:** All 13 parser tests pass including English vs German language selection
- **Committed in:** 1fdf5ae (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correct language filtering. No scope creep.

## Issues Encountered

None beyond the xml:lang deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Complete MCP server pipeline: download -> parse -> store -> server ready for tool registration
- Phase 2 can add tools that access store via `ctx.lifespan_context["store"]`
- All 33 Phase 1 tests green, providing regression safety for tool additions

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
