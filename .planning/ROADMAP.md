# Roadmap: tei-mcp

## Overview

This roadmap delivers a read-only MCP server that exposes the TEI P5 ODD specification as queryable tools for LLMs. The build follows the strict dependency chain inherent in the architecture: parse the spec first, then expose basic lookups, then add attribute inheritance resolution, then content model expansion and nesting validation. Each phase delivers a coherent, testable capability that the next phase builds on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Project scaffold, ODD parser, in-memory data model, and MCP server shell (completed 2026-03-14)
- [x] **Phase 2: Basic Lookups and Search** - Element, class, macro, and module lookup tools plus regex search (completed 2026-03-14)
- [x] **Phase 3: Attribute Resolution and Class Hierarchy** - Full inherited attribute listing and class membership chain traversal (completed 2026-03-14)
- [ ] **Phase 4: Content Models and Nesting Validation** - Content model expansion and parent-child nesting checks

## Phase Details

### Phase 1: Foundation
**Goal**: A running MCP server that parses p5subset.xml at startup into correct, queryable in-memory data structures
**Depends on**: Nothing (first phase)
**Requirements**: BOOT-01, BOOT-02, BOOT-03, BOOT-04, XCUT-01, XCUT-02, XCUT-03
**Success Criteria** (what must be TRUE):
  1. Running `uv run` starts the MCP server without errors and it responds to the MCP initialize handshake over stdio
  2. A download script fetches p5subset.xml from the TEIC/TEI GitHub repo and places it in the expected location
  3. The parser loads p5subset.xml and builds indexes containing 500+ elements, 200+ classes, and 5+ macros (verifiable by count; TEI P5 has ~588 elements, ~212 classes, ~8 macros)
  4. All server output goes through stderr logging only -- no stdout contamination outside MCP protocol messages
  5. All tool responses are JSON and all tools are read-only (no mutation of parsed data)
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Project scaffold, frozen data models, download logic, and test infrastructure
- [ ] 01-02-PLAN.md — ODD XML parser, in-memory store, and FastMCP server shell with lifespan

### Phase 2: Basic Lookups and Search
**Goal**: An LLM can look up any element, class, macro, or module by name and search across the spec by regex
**Depends on**: Phase 1
**Requirements**: LOOK-01, LOOK-02, LOOK-03, LOOK-04, SRCH-01, SRCH-02
**Success Criteria** (what must be TRUE):
  1. User can call lookup_element with a name like "persName" and receive its ident, module, gloss, class memberships, local attributes, and raw content model as structured JSON
  2. User can call lookup_class with a name like "att.global" and receive its type, description, member list, and superclasses
  3. User can call lookup_macro with a name like "macro.paraContent" and receive its ident, description, and content definition
  4. User can call list_module_elements with a module name like "namesdates" and receive all elements belonging to that module
  5. User can call search with a regex pattern and receive matching entities (elements, classes, macros) with their type, ident, and gloss
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — OddStore query methods: case-insensitive lookup, reverse indexes, regex search, name suggestions
- [ ] 02-02-PLAN.md — Five MCP tool registrations wrapping store query methods

### Phase 3: Attribute Resolution and Class Hierarchy
**Goal**: An LLM can retrieve the complete attribute set for any element including inherited attributes, and trace class membership chains
**Depends on**: Phase 2
**Requirements**: ATTR-01, ATTR-02, ATTR-03, HIER-01
**Success Criteria** (what must be TRUE):
  1. User can call list_attributes for an element like "persName" and receive both local and inherited attributes (including those from att.global, att.naming, etc.)
  2. Each attribute in the response includes its allowed values, datatype, and whether the value list is closed or open
  3. Each inherited attribute shows which att.* class it comes from (e.g., "xml:id from att.global")
  4. User can call class_membership_chain for an element and see the full hierarchy (e.g., persName -> model.nameLike.agent -> model.nameLike -> model.phrase)
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — AttDef data model, parser enrichment, resolve_attributes and get_class_chain store methods
- [ ] 03-02-PLAN.md — list_attributes and class_membership_chain MCP tool registrations

### Phase 4: Content Models and Nesting Validation
**Goal**: An LLM can expand content models to concrete elements and check whether one element can nest inside another
**Depends on**: Phase 3
**Requirements**: CMOD-01, CMOD-02, CMOD-03, NEST-01, NEST-02, NEST-03
**Success Criteria** (what must be TRUE):
  1. User can call expand_content_model for an element like "div" and receive its content model with class references resolved to concrete element names
  2. Expanded content models preserve structural semantics (sequence vs alternation vs repetition), not just flat element lists
  3. Macro references within content models are recursively resolved to their underlying content
  4. User can call check_nesting("p", "div") and get a YES/NO answer for direct parent-child validity
  5. User can call check_nesting_recursive("persName", "body") and get a YES/NO answer for whether persName can appear anywhere inside body, with cycle detection preventing infinite loops
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — Content model expansion engine: fixture enrichment, tree builder, classRef/macroRef resolution
- [ ] 04-02-PLAN.md — Nesting validation (direct + recursive) and MCP tool wiring for expand_content_model and check_nesting

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Complete    | 2026-03-14 |
| 2. Basic Lookups and Search | 0/2 | Complete    | 2026-03-14 |
| 3. Attribute Resolution and Class Hierarchy | 0/2 | Complete    | 2026-03-14 |
| 4. Content Models and Nesting Validation | 0/2 | Not started | - |
