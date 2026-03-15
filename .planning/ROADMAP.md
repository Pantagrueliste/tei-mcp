# Roadmap: tei-mcp

## Milestones

- [x] **v1.0 Spec Lookup Foundation** - Phases 1-4 (shipped 2026-03-15)
- [ ] **v2.0 Document Validation & Enhanced Querying** - Phases 5-8 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 Spec Lookup Foundation (Phases 1-4) - SHIPPED 2026-03-15</summary>

- [x] **Phase 1: Foundation** - Project scaffold, ODD parser, in-memory data model, and MCP server shell (completed 2026-03-14)
- [x] **Phase 2: Basic Lookups and Search** - Element, class, macro, and module lookup tools plus regex search (completed 2026-03-14)
- [x] **Phase 3: Attribute Resolution and Class Hierarchy** - Full inherited attribute listing and class membership chain traversal (completed 2026-03-14)
- [x] **Phase 4: Content Models and Nesting Validation** - Content model expansion and parent-child nesting checks (completed 2026-03-15)

</details>

### v2.0 Document Validation & Enhanced Querying (Phases 5-8)

**Milestone Goal:** Bridge the gap between spec knowledge and actual document validation -- move from "what does the spec say?" to "is this document correct?"

- [ ] **Phase 5: Deprecation Awareness** - Model enrichment and parser changes to surface deprecation status across existing tools
- [ ] **Phase 6: Enhanced Querying** - valid_children, batch check_nesting, and suggest_attribute tools for richer LLM interaction
- [ ] **Phase 7: Core Validation** - validate_document and validate_element tools for checking TEI XML against the spec
- [ ] **Phase 8: ODD Customisation** - Project-specific schema validation using ODD customisation files

## Phase Details

### Phase 5: Deprecation Awareness
**Goal**: Existing tools surface deprecation status so an LLM knows which elements and attributes are deprecated, when they expire, and what to use instead
**Depends on**: Phase 4 (v1.0 complete -- parser, models, and store infrastructure exist)
**Requirements**: DEPR-01, DEPR-02, DEPR-04
**Success Criteria** (what must be TRUE):
  1. User calls list_attributes for an element with a deprecated attribute (e.g., seg/@part) and the response includes a "deprecated" flag, validUntil date, and migration guidance for that attribute
  2. User calls lookup_element for a deprecated element (e.g., "re") and the response includes deprecation status with validUntil date and deprecation info text
  3. Parser extracts @validUntil and desc[@type='deprecationInfo'] from the ODD spec into model fields -- verifiable by checking that known deprecated entities (re, superEntry, attRef/@name) carry deprecation data after startup
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md -- Model fields and parser deprecation extraction (TDD)
- [ ] 05-02-PLAN.md -- Deprecation in store and server tool responses (TDD)

### Phase 6: Enhanced Querying
**Goal**: An LLM can discover allowed children for an element, validate multiple nesting pairs in one call, and find the right attribute by describing its intent
**Depends on**: Phase 5 (deprecation data available so new tools can include it)
**Requirements**: QURY-01, QURY-02, QURY-03, QURY-04
**Success Criteria** (what must be TRUE):
  1. User calls valid_children("div") and receives a flat, deduplicated list of allowed child element names grouped by provenance (directly named vs via class) with required/optional flags
  2. User calls check_nesting with multiple parent-child pairs (e.g., [("p","div"), ("head","div"), ("note","body")]) in a single batch call and receives results for all pairs without multiple round-trips
  3. User calls suggest_attribute("persName", "link to authority") and receives relevant attributes (e.g., ref, key) with descriptions ranked by relevance to the intent keywords
**Plans**: 3 plans

Plans:
- [ ] 06-01-PLAN.md -- valid_children tool with required flags and content model indicators (TDD)
- [ ] 06-02-PLAN.md -- check_nesting_batch tool for multiple pair validation (TDD)
- [ ] 06-03-PLAN.md -- suggest_attribute tool for intent-based attribute search (TDD)

### Phase 7: Core Validation
**Goal**: An LLM can validate a complete TEI XML document or a single element in context, receiving structured issues with severity, location, and actionable messages
**Depends on**: Phase 6 (caching infrastructure from valid_children; deprecation data from Phase 5)
**Requirements**: VALD-01, VALD-02, VALD-03, VALD-04, VALD-05, VALD-06, VALD-07, VALD-09, VALD-10, DEPR-03
**Note**: VALD-08 dropped (editorial convention, not spec rule) -- project-specific attribute expectations belong in ODD customisation (Phase 8)
**Success Criteria** (what must be TRUE):
  1. User calls validate_document with a TEI XML file path and receives a JSON array of issues, each with severity (error/warning/info), line number, element name, message, and rule code
  2. validate_document catches content model violations (child not allowed), attribute violations (unknown attribute, invalid closed-list value), empty required-content elements, and reference integrity issues (bare ref="#" placeholders)
  3. validate_document emits warnings for deprecated element and attribute usage (e.g., seg/@part triggers a deprecation warning with migration guidance)
  4. validate_document response includes a limitations field stating what was NOT checked (Schematron, datatype patterns, element ordering)
  5. User calls validate_element with an element name and its context (parent, attributes, children) and receives validation issues for that single element -- enabling incremental editing workflows
**Plans**: 3 plans

Plans:
- [x] 07-01-PLAN.md -- TEIValidator scaffold, lxml dependency, validate_file response shape (TDD)
- [ ] 07-02-PLAN.md -- All validation check methods: content model, attributes, empty, refs, deprecation (TDD)
- [ ] 07-03-PLAN.md -- validate_element dual-format input and MCP tool registration (TDD)

### Phase 8: ODD Customisation
**Goal**: An LLM can validate documents against a project-specific ODD customisation rather than the full permissive TEI schema
**Depends on**: Phase 7 (working base validation to layer customisation on top of)
**Requirements**: ODDS-01, ODDS-02, ODDS-03, ODDS-04, ODDS-05
**Success Criteria** (what must be TRUE):
  1. User loads a project ODD file (e.g., TEI Lite) and validation tools constrain results to the customised schema -- elements excluded by the ODD are flagged as invalid
  2. ODD parser handles moduleRef with include/except attributes to filter elements at module level
  3. ODD parser handles elementSpec mode="delete" (element removed from schema) and mode="change" (attribute modifications applied) -- the customised schema reflects these changes
  4. ODD customisation produces a separate store instance -- the base TEI store is never mutated, allowing multiple project schemas per server session
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 5 -> 6 -> 7 -> 8

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-03-14 |
| 2. Basic Lookups and Search | v1.0 | 2/2 | Complete | 2026-03-14 |
| 3. Attribute Resolution and Class Hierarchy | v1.0 | 2/2 | Complete | 2026-03-14 |
| 4. Content Models and Nesting Validation | v1.0 | 2/2 | Complete | 2026-03-15 |
| 5. Deprecation Awareness | v2.0 | 2/2 | Complete | 2026-03-15 |
| 6. Enhanced Querying | v2.0 | 3/3 | Complete | 2026-03-15 |
| 7. Core Validation | 2/3 | In Progress|  | - |
| 8. ODD Customisation | v2.0 | 0/? | Not started | - |
