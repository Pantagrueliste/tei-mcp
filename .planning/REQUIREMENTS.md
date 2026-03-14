# Requirements: tei-mcp

**Defined:** 2026-03-14
**Core Value:** An LLM can accurately look up any TEI element's attributes, content model, and valid nesting — so it produces correct TEI markup without hallucinating the spec.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Bootstrap

- [x] **BOOT-01**: Download script fetches p5subset.xml from TEIC/TEI GitHub repo
- [x] **BOOT-02**: Server parses p5subset.xml once at startup into in-memory data structures for elements, classes, macros, and modules
- [x] **BOOT-03**: FastMCP server starts via stdio transport with all tools registered
- [x] **BOOT-04**: uv manages all project dependencies via pyproject.toml

### Lookup

- [x] **LOOK-01**: User can look up an element by name and get its ident, module, gloss, class memberships, local attributes, and raw content model
- [x] **LOOK-02**: User can look up a class by name and get its ident, type (model/atts), description, members, and superclasses
- [x] **LOOK-03**: User can look up a macro by name and get its ident, description, and content
- [x] **LOOK-04**: User can list all elements belonging to a given module

### Search

- [x] **SRCH-01**: User can search across element/class/macro names, glosses, and descriptions using regex patterns
- [x] **SRCH-02**: Search results return structured JSON with matched entity type, ident, and gloss

### Attributes

- [x] **ATTR-01**: User can list all attributes for an element including those inherited from the att.* class hierarchy
- [x] **ATTR-02**: Each attribute includes its allowed values, datatypes, and constraints (closed value lists, teidata.* types)
- [x] **ATTR-03**: User can see which attribute class each inherited attribute comes from

### Content Models

- [x] **CMOD-01**: User can expand an element's content model with class references resolved to concrete elements
- [x] **CMOD-02**: Expansion preserves structural semantics (sequence, alternation, repetition) not just flat element lists
- [x] **CMOD-03**: Macro references in content models are recursively resolved

### Nesting Validation

- [x] **NEST-01**: User can check if element X can be a direct child of element Y (parent-child validity)
- [x] **NEST-02**: User can check if element X can appear anywhere inside element Y (recursive reachability)
- [x] **NEST-03**: Nesting checks handle cycles in the content model graph (e.g., div contains div)

### Class Hierarchy

- [x] **HIER-01**: User can see the full class membership chain for an element (e.g., persName → model.nameLike.agent → model.nameLike → model.phraseSeq)

### Cross-Cutting

- [x] **XCUT-01**: All tools return JSON responses
- [x] **XCUT-02**: All tools are read-only
- [x] **XCUT-03**: No output to stdout except MCP protocol messages (logging to stderr only)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extended Reference

- **DTYP-01**: Expand teidata.* types to underlying XSD/RELAX NG primitives
- **SCHM-01**: Display Schematron constraintSpec rules as informational text

### Enhanced Search

- **SRCH-03**: Search with filtering by entity type (elements only, classes only, etc.)
- **SRCH-04**: Search with filtering by module

## Out of Scope

| Feature | Reason |
|---------|--------|
| Guidelines prose/remarks | Structure only — keeps payloads small for encoding assistance |
| Schema generation (RELAX NG / XSD) | Different tool (Roma/OxGarage), different complexity |
| Document validation | Requires full schema + validation engine — use oXygen/jing |
| Module subsetting / filtering | Full spec always loaded — simplifies implementation |
| HTTP/SSE transport | stdio only per project constraints |
| Write operations / spec modification | Read-only reference tool |
| Caching/persistence | Parse fresh each startup — p5subset.xml is small enough |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BOOT-01 | Phase 1 | Complete |
| BOOT-02 | Phase 1 | Complete |
| BOOT-03 | Phase 1 | Complete |
| BOOT-04 | Phase 1 | Complete |
| LOOK-01 | Phase 2 | Complete |
| LOOK-02 | Phase 2 | Complete |
| LOOK-03 | Phase 2 | Complete |
| LOOK-04 | Phase 2 | Complete |
| SRCH-01 | Phase 2 | Complete |
| SRCH-02 | Phase 2 | Complete |
| ATTR-01 | Phase 3 | Complete |
| ATTR-02 | Phase 3 | Complete |
| ATTR-03 | Phase 3 | Complete |
| CMOD-01 | Phase 4 | Complete |
| CMOD-02 | Phase 4 | Complete |
| CMOD-03 | Phase 4 | Complete |
| NEST-01 | Phase 4 | Complete |
| NEST-02 | Phase 4 | Complete |
| NEST-03 | Phase 4 | Complete |
| HIER-01 | Phase 3 | Complete |
| XCUT-01 | Phase 1 | Complete |
| XCUT-02 | Phase 1 | Complete |
| XCUT-03 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after roadmap creation*
