# Feature Landscape

**Domain:** TEI-P5 MCP server -- document validation and enhanced querying (v2.0)
**Researched:** 2026-03-15

## Table Stakes

Features users expect from a validation-capable TEI MCP server. Missing = the milestone fails to deliver its core promise of bridging spec knowledge to document validation.

| Feature | Why Expected | Complexity | Depends On | Notes |
|---------|--------------|------------|------------|-------|
| **validate_document** | The milestone's raison d'etre. Users currently script this manually against the 59-letter corpus. Without it, the server is still just a spec reference, not a validation tool. | High | expand_content_model, check_nesting, resolve_attributes, _collect_direct_children | Largest single feature. Must parse TEI XML, walk the tree, and check every element against spec. See detailed breakdown below. |
| **valid_children** | Direct complement to check_nesting. An LLM needs "what CAN go here?" not just "can X go in Y?". Without it, the LLM must call check_nesting for every possible element -- hundreds of calls. | Low | _collect_direct_children (already exists) | Essentially exposes _collect_direct_children as a public tool with deduplication and sorting. Most of the logic already exists. |
| **Deprecation awareness** | Real-world corpus already hit this (part attr on seg). If tools silently return deprecated attrs/elements without warning, the LLM produces deprecated markup. p5subset.xml has validUntil on 3 elements and 1 attribute currently. | Medium | Parser changes to extract validUntil and deprecationInfo from elementSpec, attDef, classSpec, dataSpec | Requires model changes (add deprecation fields), parser changes (extract validUntil + deprecationInfo desc), and surfacing in lookup_element, list_attributes, and validate_document output. |
| **Batch check_nesting** | Without this, validating a document's structure requires N separate MCP round-trips. In a 59-document corpus with hundreds of nesting pairs, this is prohibitively slow. | Low | check_nesting (already exists) | Wrapper that takes a list of (child, parent) pairs and returns results for all. Trivial implementation, high ergonomic value. |

## Differentiators

Features that set this server apart from existing TEI validation tools (Oxygen, TEI by Example Validator, Jing+RELAX NG). Not expected, but valuable for the MCP/LLM use case.

| Feature | Value Proposition | Complexity | Depends On | Notes |
|---------|-------------------|------------|------------|-------|
| **validate_element** | Incremental validation during editing. Unlike validate_document (batch check), this checks a single element in its context -- perfect for an LLM building markup element-by-element. No traditional validator offers this interactive, contextual mode. | Medium | validate_document infrastructure (reuses same checks but scoped to one element) | Returns: valid nesting in parent, valid children present, required attributes present, no deprecated attrs used, no unknown attrs. |
| **suggest_attribute** | Novel for TEI tooling. Traditional validators say "wrong attribute" but never say "use this instead." An LLM asking "which attribute marks the target of a reference?" gets back `target` from att.pointing. Bridges intent to spec. | Medium | resolve_attributes, search | Keyword search across attribute descriptions within the scope of a given element's available attributes (local + inherited). Could also search globally if no element specified. |
| **ODD-aware validation** | Project customizations are how real TEI projects work. Without ODD awareness, validation is against the full TEI spec, which is too permissive (allows elements the project has deleted) or wrong (misses project-added constraints like required @type values). This is the hardest feature but the most differentiating. | High | Full parser infrastructure + new ODD overlay engine | Must parse ODD customization files (schemaSpec, moduleRef, elementSpec with mode=change/delete/add, classSpec modifications, attDef overrides). Needs to build a modified OddStore that reflects the project's actual schema. |

## Anti-Features

Features to explicitly NOT build. These are out of scope per PROJECT.md or would undermine the server's design.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Schema generation (RELAX NG / XSD / DTD)** | Roma/OxGarage already does this well. Duplicating it adds massive complexity for little value. Our tool validates against the parsed ODD directly, not via generated schemas. | Point users to Roma/OxGarage for schema files. Validate directly from parsed spec. |
| **Schematron constraint checking** | Schematron rules in TEI are complex (XPath-based, cross-document). They require an XSLT/XPath engine that goes well beyond lxml basics. Explicitly deferred to future milestone. | Document as future milestone. validate_document covers structural/content model checks, not Schematron co-occurrence constraints. |
| **Full RELAX NG validation** | Would require generating and then applying RELAX NG schemas. Our approach is simpler: check content models directly from the parsed ODD tree. | Use the content model tree + nesting checks directly. More useful error messages than RELAX NG anyway. |
| **Write operations / spec modification** | Server is read-only by design. Mutation would require persisting changes and handling conflicts. | All tools remain read-only query/validation tools. |
| **Prose/remarks from Guidelines** | Keeps payloads focused. LLMs don't need the full Guidelines text for encoding assistance. | Return structural data only. desc fields are already included for context. |
| **Namespace validation** | TEI namespace handling (tei:, xml:) is standard and handled by XML parsers. Validating namespace declarations adds complexity for minimal value in the LLM use case. | Trust lxml's namespace handling. |
| **Full sequence/cardinality enforcement** | Content models with strict ordering (sequence with min/maxOccurs) require a full finite-state automaton or regex-based matcher. Disproportionate complexity vs. value for v2.0. | Check presence (correct elements appear) rather than order/cardinality. Flag as future enhancement. |

## Feature Dependencies

```
Deprecation awareness (parser + models)
    |
    v
valid_children (expose _collect_direct_children)  --> validate_element
    |                                                      |
    v                                                      v
Batch check_nesting                              validate_document
    |                                                      |
    +------------------------------------------------------+
                           |
                           v
                  ODD-aware validation
                  (overlay modified store)
                           |
                           v
                  suggest_attribute
                  (can work standalone but richer with ODD context)
```

**Critical path:** Deprecation awareness must come first because validate_document needs to report deprecated elements/attributes. valid_children is a prerequisite for validate_element (which needs to list what is allowed, not just check one child). validate_document is the integration point that exercises all prior features. ODD-aware validation layers on top of everything.

## Detailed Feature Specifications

### validate_document

**Input:** TEI XML string (or file path)
**Output:** List of validation issues, each with: element path (XPath), issue type, severity, message

**Checks to perform (ordered by importance):**

1. **Content model violations** -- child element not allowed in parent's content model. Uses check_nesting logic. This is the check that caught "encodingDesc inside encodingDesc" in the corpus.
2. **Unknown elements** -- element name not in TEI spec (caught "n" used instead of "name").
3. **Invalid attributes** -- attribute not defined for element (local or inherited). Caught "target" on "add" (should be "corresp").
4. **Missing required attributes** -- element missing attributes with usage="req". Caught "locus" without "from"/"to".
5. **Deprecated element/attribute usage** -- element or attribute has validUntil in the past or near future. Caught "part" on "seg".
6. **Empty required-content elements** -- element has non-empty content model but contains no children/text.

**NOT in scope for v2.0:**
7. Sequence/cardinality violations -- content model specifies sequence or min/maxOccurs constraints that are not met. Defer to future milestone.

**Severity levels:** ERROR (structural invalidity), WARNING (deprecated usage, likely mistakes), INFO (suggestions)

**Performance concern:** Walking every element in a document and checking its content model is O(elements * content_model_size). For large documents, this could be slow. Must cache _collect_direct_children results and the resolved attribute sets per element name, since many elements share the same name across a document.

### validate_element

**Input:** element name, parent element name, list of child element names, list of attribute names and values
**Output:** List of validation issues for just this element

**Checks:** Same as validate_document but scoped to a single element context. Designed for incremental validation during editing. Returns both issues found and what IS valid (e.g., "these children are allowed, these are not").

### Deprecation Awareness

**Model changes needed:**
- `ElementDef`: add `valid_until: str | None` and `deprecation_info: str`
- `AttDef`: add `valid_until: str | None` and `deprecation_info: str`
- `ClassDef`: add `valid_until: str | None` and `deprecation_info: str`
- `MacroDef`: add `valid_until: str | None` and `deprecation_info: str`

**Parser changes:** Extract `validUntil` attribute and `desc[@type='deprecationInfo']` text from each spec element and attDef.

**Tool integration:**
- `lookup_element`: include `deprecated: true/false`, `valid_until`, `deprecation_info` in response
- `list_attributes`: include deprecation status per attribute
- `validate_document`: flag deprecated elements/attributes as WARNING

**Current p5subset.xml deprecation data (verified from file):**
- `superEntry` element: validUntil 2027-03-07 (use nested entry instead)
- `re` element: validUntil 2026-03-10 (already past as of today -- use entry instead)
- `teidata.point` dataSpec: validUntil 2050-02-25
- `attRef/@name` attribute: validUntil 2026-11-13 (use @key instead)
- 6 `desc type="deprecationInfo"` elements total in the file

### valid_children

**Input:** parent element name
**Output:** sorted, deduplicated list of element idents that can be direct children

**Implementation:** Calls `_collect_direct_children(parent)`, removes the `*` sentinel, sorts alphabetically. Add metadata: for each child, include which classRef or elementRef it comes through (reuse `_find_class_for_child` logic or build a parallel method that returns all class attributions at once).

### Batch check_nesting

**Input:** list of `{child, parent, recursive?}` pairs
**Output:** list of check_nesting results, one per pair, plus summary counts

**Implementation:** Loop over pairs, call existing `check_nesting` for each. Return `{total, valid_count, invalid_count, results: [...]}`. No new store logic needed.

### suggest_attribute

**Input:** element name (optional), intent keywords (e.g., "target reference link")
**Output:** ranked list of matching attributes with descriptions

**Implementation:**
1. If element specified: get all attributes (local + inherited) via resolve_attributes
2. Search attribute idents and descriptions against keywords (regex or token matching)
3. Rank by relevance (ident match > desc match)
4. If no element specified: search across all att.* classes globally (broader, slower)

### ODD-aware Validation

**Input:** path to ODD customization file
**Output:** modified OddStore reflecting the project's actual schema

**ODD processing steps:**
1. Parse the ODD file as TEI XML
2. Find `<schemaSpec>` -- this defines the customization
3. Process `<moduleRef>` elements to determine which modules are included. moduleRef supports `@include` (whitelist specific elements from a module) and `@except` (exclude specific elements)
4. Process `<elementSpec mode="delete">` to remove elements
5. Process `<elementSpec mode="change">` to modify elements (attribute changes, content model changes)
6. Process `<elementSpec mode="add">` to add project-specific elements
7. Process `<classSpec mode="change/delete">` for class modifications
8. Build a new OddStore (or overlay on top of the base store) reflecting these changes

**Recommended phased approach for v2.0:**
- Phase A (MVP): moduleRef filtering + elementSpec mode="delete" only. This covers 80% of real-world customizations.
- Phase B (if time allows): elementSpec mode="change" for attDef modifications (mode="delete" on attDefs, valList changes to closed).
- Defer: elementSpec mode="add" (rare), complex content model changes.

## MVP Recommendation

Prioritize in this order:

1. **Deprecation awareness** -- Foundation for all validation. Low-medium complexity, high value. Parser and model changes unlock deprecation info everywhere.
2. **valid_children** -- Low complexity, high value. Mostly wraps existing code. Immediate utility for LLM markup building.
3. **Batch check_nesting** -- Trivial complexity, needed for validate_document performance and ergonomics.
4. **validate_document** -- The headline feature. Depends on 1-3 being done. High complexity but core value proposition.
5. **validate_element** -- Reuses validate_document infrastructure. Medium complexity, high ergonomic value for incremental editing.
6. **suggest_attribute** -- Independent of validation pipeline. Can be built in parallel with 4-5. Medium complexity.
7. **ODD-aware validation** -- Highest complexity, highest differentiator. Build last because it layers on top of everything. Ship Phase A (moduleRef + delete) and iterate.

**Defer from v2.0 MVP:** Full sequence/cardinality validation in validate_document (presence-only checks are sufficient). Full ODD mode="change" with nested attDef modifications (handle delete and simple changes only). Schematron constraint checking (explicitly out of scope).

## Sources

- [TEI att.deprecated class](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-att.deprecated.html) -- validUntil mechanism, which spec elements use it
- [Getting Started with P5 ODDs](https://tei-c.org/guidelines/customization/getting-started-with-p5-odds/) -- ODD customization structure, mode attributes, moduleRef
- [TEI Roma](https://romabeta.tei-c.org/) -- ODD-to-schema generation tool
- [TEI Using the TEI chapter](https://tei-c.org/release/doc/tei-p5-doc/en/html/USE.html) -- official Guidelines chapter on customization
- [TEI by Example Validator](https://teibyexample.org/exist/tools/TBEvalidator.htm) -- existing web-based TEI validation tool
- [Brill TEI Validation docs](https://brillpublishers.gitlab.io/documentation-tei-xml/Validation.html) -- validation workflow documentation
- [TEI elementSpec reference](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-elementSpec.html) -- elementSpec mode attribute
- Direct analysis of p5subset.xml: 22 lines with validUntil, 6 deprecationInfo descs, 3 deprecated elements/datatypes, 1 deprecated attribute
- Direct analysis of existing codebase: store.py (635 lines), server.py (229 lines), parser.py (201 lines), models.py (61 lines)
