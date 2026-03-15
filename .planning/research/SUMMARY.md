# Project Research Summary

**Project:** TEI-P5 MCP Server v2.0 — Document Validation & Enhanced Querying
**Domain:** XML schema tooling / MCP server for LLM-assisted TEI markup
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

This v2.0 research covers adding document validation, deprecation awareness, and enhanced querying to an existing, production-ready TEI-P5 MCP server. The server has a mature four-layer architecture (p5subset.xml -> parser.py -> models.py -> store.py -> server.py) built on Python 3.13, FastMCP, and stdlib `xml.etree.ElementTree`. The critical discovery is that v2.0 requires exactly one new runtime dependency: `lxml >= 5.0`, used exclusively for parsing user-submitted TEI documents where `sourceline` line numbers are required for useful error messages. All other new features — including deprecation awareness, valid_children, batch nesting, and suggest_attribute — extend existing patterns without introducing new technology. The lxml/stdlib ET boundary must be clear and respected throughout: lxml for user documents, stdlib ET for the ODD spec.

The recommended build order is dependency-driven and risk-stratified. Model enrichment for deprecation comes first because it is cross-cutting, backward-compatible, and urgently needed (`re` element has already expired as of today). Quick-win tools ship second as pure, zero-risk additions that deliver immediate LLM value and establish the caching infrastructure that validate_document requires. Core validation (`validate_element` + `validate_document`) arrives third as the headline feature, integrating all prior work. ODD-aware validation rounds out v2.0 as the highest-complexity differentiator, treated as a phased MVP: module filtering + delete mode first, change mode second.

The primary risks are concrete and well-understood. TEI namespace stripping is mandatory for document validation — forgetting it produces 100% false positive rates. Store logic must not be duplicated; validate_document must build on cached store methods, not reimplement them. The tool must document its scope honestly: Schematron constraints, cardinality enforcement, and co-occurrence rules are explicitly out of scope, and every validate_document response must say so. ODD `change` mode merge semantics are a deep merge, not a shallow replace — implementing this incorrectly silently corrupts the project schema. All four risks have clear, testable prevention strategies.

## Key Findings

### Recommended Stack

The existing stack (Python 3.13, FastMCP 3.1+, stdlib `xml.etree.ElementTree`, frozen dataclasses, difflib, httpx) is validated and should not be migrated. The single new dependency is `lxml >= 5.0`, used at a strict boundary: lxml parses user-submitted TEI documents to obtain `sourceline` line numbers; stdlib ET continues to parse p5subset.xml and ODD customisation files. These two XML stacks communicate only through string element names and attribute dicts — no lxml/ET objects cross the boundary.

**Core technologies:**
- `lxml >= 5.0`: user document parsing — the only library providing `sourceline` on parsed elements (stdlib ET issue #14078 will never be resolved)
- `xml.etree.ElementTree` (stdlib): ODD spec parsing — existing patterns, no line numbers needed for spec errors
- `difflib.SequenceMatcher` (stdlib): suggest_attribute intent matching — already used in `suggest_names()`, sufficient for the small search space (~50-100 attributes per element)
- `datetime.date` (stdlib): deprecation status calculation — `validUntil` is `yyyy-mm-dd`, `date.fromisoformat()` handles parsing, compare with `date.today()` for status
- `dataclasses(frozen=True)`: model fields with defaults for new deprecation data — backward-compatible schema evolution via optional fields

**What NOT to add:** lxml for ODD parsing (creates two XML stacks for spec), Pydantic (frozen dataclasses + `asdict()` work), rapidfuzz/thefuzz (difflib is sufficient), jsonschema (FastMCP handles), RELAX NG validation (out of scope per PROJECT.md).

### Expected Features

**Must have (table stakes):**
- `validate_document` — the milestone's core promise; checks content model nesting, unknown elements, invalid attributes, missing required attributes, deprecated usage, and empty required-content elements
- `valid_children` — direct complement to check_nesting; exposes `_collect_direct_children` publicly so LLMs get "what CAN go here" without hundreds of separate calls
- Deprecation awareness — p5subset.xml has `re` element with `validUntil="2026-03-10"` (already expired as of today); tools must surface this or produce misleading output
- Batch check_nesting — without it, document structure validation requires N MCP round-trips; trivial wrapper over existing `check_nesting`

**Should have (competitive differentiators):**
- `validate_element` — incremental validation during editing; no traditional TEI validator offers this interactive, contextual mode
- `suggest_attribute` — maps intent keywords to attribute names; bridges intent-to-spec gap that error-only validators do not address
- ODD-aware validation — project customisations are how real TEI projects work; validates against project-specific schema not full permissive TEI

**Defer (beyond v2.0):**
- Full sequence/cardinality enforcement (requires finite-state automaton; presence-only checks are sufficient for v2.0)
- Schematron constraint checking (requires XSLT/XPath engine, explicitly out of scope per PROJECT.md)
- Schema generation (RELAX NG / XSD / DTD) — Roma/OxGarage already does this
- ODD `mode="add"` and `mode="replace"` (rare in practice; defer from ODD-aware MVP)
- Write operations (server is read-only by design)

### Architecture Approach

The architecture extends the existing four-layer pattern with one new module (`validator.py`) and focused enhancements to existing components. Validation is deliberately separated from querying: `validator.py` is a consumer of `OddStore`, not an extension of it. ODD customisation produces a NEW OddStore instance rather than mutating the shared base store, allowing multiple project schemas per server instance. A lazy `_direct_children_cache` on OddStore eliminates the N+1 content model parsing problem that would otherwise make document validation prohibitively slow on large corpora.

**Major components:**
1. `models.py` — add `valid_until: str | None = None` and `deprecation_info: str = ""` defaults to `ElementDef`, `AttDef`, `ClassDef`, `MacroDef`; backward-compatible due to default values
2. `parser.py` — extract `@validUntil` and `desc[@type='deprecationInfo']` during ODD parsing; later parse ODD customisation files with the same stdlib ET patterns
3. `store.py` — add `valid_children()`, `batch_check_nesting()`, `suggest_attribute()` public methods; add `_direct_children_cache: dict[str, set[str]]`; surface deprecation in `resolve_attributes()` and existing tool responses
4. `validator.py` (NEW) — `validate_element()` and `validate_document()` functions using lxml for document parsing; `ValidationIssue` dataclass with severity, code, element, xpath, message; issue codes: `UNKNOWN_ELEMENT`, `INVALID_NESTING`, `UNKNOWN_ATTRIBUTE`, `INVALID_ATTR_VALUE`, `DEPRECATED_ELEMENT`, `DEPRECATED_ATTRIBUTE`, `EMPTY_CONTENT`
5. `server.py` — register 5 new MCP tools; modify `lookup_element` and `list_attributes` to include deprecation data; add optional `odd_file` parameter to validation tools

### Critical Pitfalls

1. **TEI namespace produces 100% false positives in document validation** — Real documents use `{http://www.tei-c.org/ns/1.0}p`; OddStore keys are bare `p`. Strip namespace from every element tag before lookup. Also map `{http://www.w3.org/XML/1998/namespace}id` to `xml:id` for attribute validation. Detection: if every element is reported as unknown, stripping is missing.

2. **Duplicating store logic creates divergent validation behaviour** — Writing standalone validation checks instead of building on `check_nesting`, `resolve_attributes`, and `_collect_direct_children` creates two sources of truth that diverge over time. Use the `_direct_children_cache` to make store methods fast enough; do not reimplement them.

3. **Overpromising validation correctness** — Content model + attribute validation is not full TEI validation. Schematron constraints, co-occurrence rules, and datatype patterns are explicitly out of scope. Every `validate_document` response must include a `limitations` field stating what was NOT checked.

4. **ODD `change` mode is a deep merge, not a replace** — A customisation that modifies one attribute must preserve all other attributes from the base spec. Shallow replacement silently corrupts the schema. Build ODD-aware validation incrementally: module filtering + delete mode first; change mode only after base validation is stable.

5. **Batch N+1 content model parsing** — Looping `check_nesting` over pairs without caching parses the same content model XML repeatedly. Add `_direct_children_cache` to OddStore (populated lazily) before implementing batch_check_nesting; validate_document inherits this benefit automatically.

## Implications for Roadmap

Based on the dependency graph from the architecture research, the natural build order is: model enrichment -> quick-win tools (parallel with or after models) -> core validation -> ODD-aware validation. This maps to four phases:

### Phase 1: Model & Parser Enrichment (Deprecation Foundation)

**Rationale:** Deprecation data must exist in models before any validation tool can report it. Adding optional fields with defaults to frozen dataclasses is backward-compatible — no existing tool or test breaks. The `re` element expired today (validUntil 2026-03-10); this work is urgent.
**Delivers:** `ElementDef`, `AttDef`, `ClassDef`, `MacroDef` with `valid_until` and `deprecation_info` fields; parser extracts `@validUntil` and `desc[@type='deprecationInfo']`; `lookup_element` and `list_attributes` surface deprecation data.
**Addresses:** Deprecation awareness (table stakes).
**Avoids:** Frozen dataclass schema evolution pitfall (use default values), building validate_document without deprecation support (would require costly retrofit).

### Phase 2: Quick-Win Tools

**Rationale:** `valid_children`, `batch_check_nesting`, and `suggest_attribute` are pure additions with zero dependencies on Phase 1 (though they benefit from it) and zero risk to existing functionality. Delivering them here provides immediate LLM value, exercises OddStore extension patterns, and installs the `_direct_children_cache` that validate_document will require.
**Delivers:** `valid_children` tool (wraps `_collect_direct_children` with element metadata); `batch_check_nesting` tool (loops existing `check_nesting` with summary); `suggest_attribute` tool (three-tier matching: ident exact, desc keyword, difflib fuzzy); `_direct_children_cache` on OddStore.
**Addresses:** valid_children (table stakes), batch_check_nesting (table stakes), suggest_attribute (differentiator).
**Avoids:** N+1 content model parsing pitfall (cache installed here, not in validate_document phase), suggest_attribute terse-ident pitfall (search desc text and class desc, not just idents).

### Phase 3: Core Validation

**Rationale:** The headline milestone feature. Creates `validator.py` as a new module distinct from `store.py`. Requires Phase 1 (deprecation data in models) for complete warning output and benefits from Phase 2 (caching infrastructure). Introduces the lxml dependency scoped to this module only.
**Delivers:** `validator.py` module with `ValidationIssue` dataclass and issue codes; `validate_element` tool (single element in context with parent, optional ancestors); `validate_document` tool (full TEI XML file walk with line numbers); response includes `limitations` field, scope statement, and `truncated` flag.
**Addresses:** validate_document (table stakes), validate_element (differentiator).
**Uses:** `lxml >= 5.0` (add to pyproject.toml dependencies + `types-lxml` to dev deps).
**Avoids:** Namespace stripping pitfall, xml: attribute prefix mapping pitfall, logic duplication pitfall, size/timeout pitfall (max_errors cap default 100, file path input preferred over inline strings).

### Phase 4: ODD-Aware Validation

**Rationale:** Most complex and most differentiating feature. Must follow Phase 3 because it layers customisation on top of a working base validator. Phase A MVP (moduleRef filtering + elementSpec `mode="delete"`) covers 80% of real-world customisations. Phase B (attDef `mode="change"`) follows if time permits within the milestone.
**Delivers:** `parse_customisation()` in parser.py; `OddStore.apply_customisation()` returning a NEW OddStore (never mutates base store); customisation stores cached by `(file_path, mtime)`; `validate_document` and `validate_element` accept optional `odd_file` parameter.
**Addresses:** ODD-aware validation (differentiator).
**Avoids:** Deep merge error (implement delete-only first, change mode only after testing), moduleRef `@include`/`@except` granularity pitfall (parse element-level filtering from the start), base store mutation pitfall (always create new OddStore instances).

### Phase Ordering Rationale

- Deprecation first because it is cross-cutting and has default-value backward compatibility. No existing tool breaks; all future tools are enriched.
- Quick-win tools second because they are pure additions, deliver immediate value, and install the caching infrastructure that validate_document needs without the complexity of validation logic.
- Core validation third because it depends on deprecation data and the cache but is independent of ODD customisation. Getting plain document validation correct before adding customisation complexity is essential.
- ODD-aware validation last because it layers on a working validator. A bug in customisation parsing should not block the core value proposition.

### Research Flags

Phases with well-documented patterns (skip research-phase):
- **Phase 1 (Model enrichment):** Frozen dataclass field addition with defaults is standard Python. Deprecation data location in p5subset.xml verified directly in the file — no ambiguity.
- **Phase 2 (Quick-win tools):** All three tools extend existing OddStore methods using documented patterns. No novel integration required.

Phases likely needing deeper research or design spikes during planning:
- **Phase 3 (Validation core):** The lxml/stdlib ET integration boundary needs a concrete design document before coding. The `fromstring` vs `parse` choice for line number accuracy (see PITFALLS.md #11) must be decided before the API is locked. Benchmark validate_document on real corpus documents before declaring performance acceptable.
- **Phase 4 (ODD-aware validation):** ODD `change` mode merge semantics are deceptively complex. Strongly recommend a research spike: parse TEI Lite ODD with the new parser, compare the resulting customised OddStore against a Roma-generated schema for the same customisation. Run this before writing any `change` mode logic.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | lxml `sourceline` verified against API docs and Python issue tracker; difflib sufficiency verified from existing codebase usage; stdlib ET limitation confirmed as unresolvable |
| Features | HIGH | Deprecation instances verified directly in p5subset.xml (superEntry, re, attRef/@name, teidata.point); feature dependencies confirmed by direct codebase analysis; 59-document corpus validation gaps documented in PROJECT.md |
| Architecture | HIGH | Based on direct analysis of existing codebase (store.py 635 lines, parser.py 201 lines, server.py 229 lines, models.py 61 lines); patterns are well-established Python; new module boundary (validator.py) is clearly motivated |
| Pitfalls | HIGH | Most pitfalls verified against lxml bug tracker, Python issue tracker, and direct codebase analysis; ODD merge semantics verified against TEI specification docs; namespace pitfall confirmed by reading actual document corpus |

**Overall confidence:** HIGH

### Gaps to Address

- **ODD `change` mode merge depth:** Research documents the semantics but does not confirm which specific attDef child elements require deep merge vs shallow replacement. Requires a concrete test case during Phase 4 planning — compare against Roma output.
- **validate_document performance profile:** The `_direct_children_cache` fix is specified, but actual performance on the 59-document corpus has not been measured. Establish a baseline benchmark before Phase 3 implementation to confirm the cache is sufficient and identify any remaining hotspots.
- **suggest_attribute relevance ranking cutoffs:** The three-tier matching is specified but not validated against real LLM queries. The 0.3 difflib cutoff is a starting estimate. A brief round of exploratory testing after Phase 2 would confirm whether it produces useful results or needs tuning.
- **lxml `fromstring` vs `parse` for string vs file-path input:** PITFALLS.md recommends file path input for validate_document to preserve accurate line numbers. Confirm whether the MCP tool interface will always have access to a file path or if inline XML string input must also be supported. This decision affects the tool API design.

## Sources

### Primary (HIGH confidence)
- [lxml API reference: sourceline property](https://lxml.de/apidoc/lxml.etree.html) — sourceline availability and return type
- [Python issue #14078](https://bugs.python.org/issue14078) — confirms stdlib ET will never get sourceline
- [TEI att.deprecated class](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-att.deprecated.html) — `@validUntil` attribute definition and semantics
- [TEI elementSpec reference](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-elementSpec.html) — mode attribute values (add/delete/change/replace)
- [TEI moduleRef reference](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-moduleRef.html) — include/except attributes
- `/Users/cag30/tei-p5/src/tei_mcp/data/p5subset.xml` — deprecation instances verified directly (superEntry 2027-03-07, re 2026-03-10, attRef/@name 2026-11-13, teidata.point 2050-02-25)
- Existing codebase: `store.py` (635 lines), `parser.py` (201 lines), `models.py` (61 lines), `server.py` (229 lines)

### Secondary (MEDIUM confidence)
- [TEI Getting Started with P5 ODDs](https://tei-c.org/guidelines/customization/getting-started-with-p5-odds/) — ODD customisation structure, moduleRef semantics
- [lxml parsing guide](https://lxml.de/parsing.html) — fromstring vs parse behaviour and line number preservation
- [Python difflib docs](https://docs.python.org/3/library/difflib.html) — SequenceMatcher for intent matching
- [TEI Using the TEI chapter](https://tei-c.org/release/doc/tei-p5-doc/en/html/USE.html) — ODD customisation semantics, mode attribute merge behaviour
- [Validating TEI-XML with Python](https://adrien.barbaresi.eu/blog/validating-tei-xml-python.html) — lxml-based TEI validation approaches

### Tertiary (LOW confidence — validate during implementation)
- [lxml sourceline 65535 cap bug](https://bugs.launchpad.net/lxml/+bug/1341590) — confirmed fixed in lxml 3.3.4+ with libxml2 2.9+; verify libxml2 version on deployment environment
- [lxml sourceline with remove_blank_text](https://bugs.launchpad.net/lxml/+bug/1742121) — off-by-one with specific parser options; test empirically with corpus documents

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
