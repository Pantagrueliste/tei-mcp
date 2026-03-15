# Requirements: tei-mcp

**Defined:** 2026-03-14
**Core Value:** An LLM can accurately look up any TEI element's attributes, content model, and valid nesting — so it produces correct TEI markup without hallucinating the spec.

## v1 Requirements (Complete)

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

- [x] **HIER-01**: User can see the full class membership chain for an element

### Cross-Cutting

- [x] **XCUT-01**: All tools return JSON responses
- [x] **XCUT-02**: All tools are read-only
- [x] **XCUT-03**: No output to stdout except MCP protocol messages (logging to stderr only)

## v2 Requirements

Requirements for document validation and enhanced querying milestone.

### Validation

- [ ] **VALD-01**: User can call validate_document with a TEI XML file path and receive a JSON array of issues with severity, line number, element, message, and rule
- [ ] **VALD-02**: validate_document checks content model compliance — flags children not allowed by the parent's expanded content model
- [ ] **VALD-03**: validate_document checks required children — flags elements violating minimum cardinality (e.g., choice needs ≥2 children)
- [ ] **VALD-04**: validate_document checks attribute validity — flags attributes not in the element's attribute list (including inherited)
- [ ] **VALD-05**: validate_document checks closed value lists — flags attribute values not in allowed sets
- [ ] **VALD-06**: validate_document checks empty elements — flags elements with required content models that have no children
- [ ] **VALD-07**: validate_document checks reference integrity — flags bare ref="#" placeholders and optionally validates ref targets against authority file xml:id values
- [ ] **VALD-08**: validate_document checks missing attributes — flags elements where key attributes are absent (e.g., locus without from/to, date without when, persName without ref in body)
- [ ] **VALD-09**: validate_document response clearly states scope limitations (not checked: Schematron, datatype patterns, element ordering)
- [ ] **VALD-10**: User can call validate_element with element context to check a single element for incremental editing workflows

### Deprecation

- [x] **DEPR-01**: list_attributes flags deprecated attributes with a "deprecated" field, validUntil date, and migration guidance
- [x] **DEPR-02**: lookup_element surfaces deprecation status for deprecated elements
- [ ] **DEPR-03**: validate_document emits warnings for deprecated attribute and element usage
- [x] **DEPR-04**: Parser extracts @validUntil and desc type="deprecationInfo" from ODD spec into model fields

### Enhanced Querying

- [x] **QURY-01**: User can call valid_children with a parent element name and receive a flat, deduplicated list of allowed child element names
- [x] **QURY-02**: valid_children groups results by provenance (directly named vs via class membership) and flags required vs optional
- [x] **QURY-03**: User can call check_nesting with multiple parent-child pairs in a single batch call and receive results for all pairs
- [ ] **QURY-04**: User can call suggest_attribute with an element name and intent keyword to find the most relevant attributes with descriptions

### ODD Customisation

- [ ] **ODDS-01**: User can load a project ODD customisation file to constrain validation to project-specific schema
- [ ] **ODDS-02**: ODD parser handles moduleRef with include/except for element filtering
- [ ] **ODDS-03**: ODD parser handles elementSpec mode="delete" to remove elements from the schema
- [ ] **ODDS-04**: ODD parser handles elementSpec mode="change" for attribute modifications
- [ ] **ODDS-05**: ODD-customised validation produces a separate OddStore instance (base store unchanged)

## Future Requirements

Deferred beyond v2. Tracked but not in current roadmap.

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
| Full schema validation (Schematron, datatypes, ordering) | Content model presence checks only — not a schema validator replacement |
| HTTP/SSE transport | stdio only per project constraints |
| Write operations / spec modification | Read-only reference tool |
| ODD change mode deep-merge of content models | MVP covers attribute changes only; content model merge deferred |

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
| VALD-01 | Phase 7 | Pending |
| VALD-02 | Phase 7 | Pending |
| VALD-03 | Phase 7 | Pending |
| VALD-04 | Phase 7 | Pending |
| VALD-05 | Phase 7 | Pending |
| VALD-06 | Phase 7 | Pending |
| VALD-07 | Phase 7 | Pending |
| VALD-08 | Phase 7 | Pending |
| VALD-09 | Phase 7 | Pending |
| VALD-10 | Phase 7 | Pending |
| DEPR-01 | Phase 5 | Complete |
| DEPR-02 | Phase 5 | Complete |
| DEPR-03 | Phase 7 | Pending |
| DEPR-04 | Phase 5 | Complete |
| QURY-01 | Phase 6 | Complete |
| QURY-02 | Phase 6 | Complete |
| QURY-03 | Phase 6 | Complete |
| QURY-04 | Phase 6 | Pending |
| ODDS-01 | Phase 8 | Pending |
| ODDS-02 | Phase 8 | Pending |
| ODDS-03 | Phase 8 | Pending |
| ODDS-04 | Phase 8 | Pending |
| ODDS-05 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 23 total (all complete)
- v2 requirements: 23 total
- Mapped to phases: 23 v1 (complete) + 23 v2 (pending) = 46 total
- Unmapped: 0

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-15 after v2.0 roadmap creation*
