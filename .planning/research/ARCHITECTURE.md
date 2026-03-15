# Architecture Patterns

**Domain:** TEI-P5 MCP Server v2.0 -- Document Validation & Enhanced Querying
**Researched:** 2026-03-15

## Existing Architecture (v1.0)

Four-layer architecture already in place:

```
p5subset.xml -> parser.py -> models.py (frozen dataclasses) -> store.py (OddStore) -> server.py (FastMCP tools)
```

Key existing components:
- **models.py**: `ElementDef`, `ClassDef`, `MacroDef`, `ModuleDef`, `AttDef` (all frozen dataclasses)
- **parser.py**: `parse_odd()` returns `OddStore` directly; uses `xml.etree.ElementTree`
- **store.py**: `OddStore` with query methods (`get_element_ci`, `resolve_attributes`, `expand_content_model`, `check_nesting`, `_collect_direct_children`, `_collect_elements_from_tree`, `_parse_content_tree`, `search`, `suggest_names`, `get_class_chain`)
- **server.py**: 8 tools registered via `@mcp.tool()`, lifespan loads OddStore into context

Note: The v1.0 roadmap proposed a separate `query.py` but in practice all query logic lives in `store.py`. This is fine for the current scale and should be maintained for v2.0 -- splitting now would create churn without benefit.

## Feature Integration Analysis

### Feature 1: valid_children (flat child list)

**Type:** New method on OddStore + new MCP tool

**Integration:** Trivial. `_collect_direct_children()` already exists as a private method returning `set[str]`. This feature wraps it in a public method that returns a sorted list with optional metadata (gloss, module).

**New components:**
- `OddStore.valid_children(parent: str) -> dict` -- public wrapper around `_collect_direct_children` with element metadata enrichment
- `server.py`: new `valid_children` tool

**Modified components:** None. Pure addition.

**Data flow:**
```
valid_children("div") -> OddStore.valid_children("div")
  -> _collect_direct_children("div")  [existing]
  -> enrich each ident with gloss/module from self.elements
  -> return {"parent": "div", "children": [{ident, gloss, module}, ...]}
```

### Feature 2: Batch check_nesting

**Type:** New method on OddStore + new MCP tool (or extend existing tool)

**Integration:** Straightforward. Loops over pairs calling existing `check_nesting()`. The key design decision: add a `pairs` parameter to the existing `check_nesting` tool vs. create a separate `batch_check_nesting` tool.

**Recommendation:** Add a separate `batch_check_nesting` tool. Reason: the existing `check_nesting` has a clean single-pair interface with `recursive` flag. Overloading it with batch semantics muddies the API. A separate tool keeps both interfaces clean.

**New components:**
- `OddStore.batch_check_nesting(pairs: list[tuple[str, str]], recursive: bool) -> dict` -- iterates pairs, collects results
- `server.py`: new `batch_check_nesting` tool

**Modified components:** None.

**Data flow:**
```
batch_check_nesting([("p","div"), ("head","div")]) -> OddStore.batch_check_nesting(pairs)
  -> for each pair: self.check_nesting(child, parent)  [existing]
  -> return {"results": [...], "summary": {valid: N, invalid: M}}
```

### Feature 3: Deprecation Awareness

**Type:** Model enhancement + parser enhancement + modifications to existing methods/tools

**Integration:** This is the most cross-cutting feature. Deprecation data must be:
1. Parsed from ODD (elementSpec/@validUntil, attDef/@validUntil, classSpec/@validUntil)
2. Stored in models
3. Surfaced in existing tool responses

**New components:**
- None new -- this modifies existing components

**Modified components:**
- `models.py`: Add `deprecated: bool` and `valid_until: str` fields to `ElementDef`, `AttDef`, and `ClassDef`. Since these are frozen dataclasses, adding optional fields with defaults is backward-compatible.
- `parser.py`: Extract `@validUntil` and `@status="deprecated"` from spec elements during parsing. The `@validUntil` attribute appears on `elementSpec`, `attDef`, and `classSpec` elements in the ODD.
- `store.py`: Modify `resolve_attributes()` to include deprecation info in attribute entries. Add `deprecated` field to attribute dicts returned.
- `server.py`: Modify `lookup_element` to include deprecation warning in response. Modify `list_attributes` to flag deprecated attributes.

**Data flow change:**
```
Parser: elementSpec[@validUntil] -> ElementDef(deprecated=True, valid_until="2024-11-01")
Parser: attDef[@validUntil] -> AttDef(deprecated=True, valid_until="...")

lookup_element("seg") -> adds "deprecation_warnings": ["attribute 'part' deprecated since 2024-11-01"]
list_attributes("seg") -> each attr dict gains "deprecated": true/false, "valid_until": "..."
```

**Critical detail:** The `@validUntil` attribute on `attDef` is the primary source. Some attributes like `part` on multiple elements have `validUntil="2024-11-01"`. The parser must capture this from `attDef` elements in the ODD, not just from `elementSpec`.

### Feature 4: suggest_attribute

**Type:** New method on OddStore + new MCP tool

**Integration:** Builds on `resolve_attributes()` to get the full attribute set, then searches attribute descriptions and idents against intent keywords.

**New components:**
- `OddStore.suggest_attribute(element: str, intent: str) -> dict` -- resolves all attributes for an element, then searches ident+desc against intent keywords using regex or fuzzy matching
- `server.py`: new `suggest_attribute` tool

**Modified components:** None.

**Data flow:**
```
suggest_attribute("p", "language") -> OddStore.suggest_attribute("p", "language")
  -> self.resolve_attributes("p")  [existing]
  -> search attrs by regex on ident + desc for "language"
  -> return {"element": "p", "matches": [{name: "xml:lang", source: "att.global", desc: "...", relevance: "ident_match"}, ...]}
```

**Design note:** Use the existing `resolve_attributes` result format. Search across both `ident` and `desc` fields. Rank ident matches higher than desc matches. Include the source class for context.

### Feature 5: validate_element (single element in context)

**Type:** New module + new MCP tool

**Integration:** This is the bridge from "spec lookup" to "document checking." It takes a snippet of XML (one element with its attributes and immediate children) and validates it against the spec.

**New components:**
- `src/tei_mcp/validator.py`: New module containing validation logic. This is the right time to separate validation from querying because validation has different concerns (XML parsing of user input, error collection, attribute checking) from spec querying.
- `server.py`: new `validate_element` tool

**Modified components:** None directly, but validator.py imports from store.py extensively.

**Validation checks performed:**
1. Element exists in spec
2. All attributes are valid for this element (via `resolve_attributes`)
3. Attribute values match constraints (closed valList)
4. Immediate children are valid (via `_collect_direct_children`)
5. Deprecation warnings (requires Feature 3)

**Data flow:**
```
validate_element("<seg part='I'>text</seg>", parent="p")
  -> parse XML snippet with ET
  -> store.get_element_ci("seg") -- exists?
  -> store.resolve_attributes("seg") -- check each attr
  -> for each child element: store.check_nesting(child, "seg") -- valid children?
  -> collect errors/warnings
  -> return {"element": "seg", "valid": false, "errors": [...], "warnings": [...]}
```

**Input format decision:** Accept raw XML string, not parsed structure. Reason: the LLM is building XML markup, so it naturally has XML strings. Parsing internally with ET keeps the API simple.

### Feature 6: validate_document (full TEI XML file)

**Type:** Extension of validator.py + new MCP tool

**Integration:** Walks entire document tree, applying validate_element logic at each node. This is the most complex new feature.

**New components:**
- `validator.py`: `validate_document(xml_content: str, store: OddStore) -> dict` function
- `server.py`: new `validate_document` tool

**Modified components:** None.

**Design:**
```python
def validate_document(xml_content: str, store: OddStore, max_errors: int = 100) -> dict:
    """Walk document tree, validate each element in context."""
    root = ET.fromstring(xml_content)
    errors = []
    warnings = []

    def walk(el, parent_name=None):
        tag = strip_ns(el.tag)
        # 1. Element exists?
        # 2. Attributes valid?
        # 3. Nesting valid? (tag inside parent_name)
        # 4. Deprecation?
        for child in el:
            walk(child, parent_name=tag)

    walk(root)
    return {"errors": errors, "warnings": warnings, "summary": {...}}
```

**Key concerns:**
- **Namespace stripping:** TEI documents use `http://www.tei-c.org/ns/1.0` namespace. Must strip it to match OddStore idents.
- **Error limits:** Large documents could produce hundreds of errors. Cap at `max_errors` (default 100).
- **Error location:** Include XPath or line-based location for each error so the LLM can navigate to the problem.
- **Performance:** Walking a 1000-element document with nesting checks at each node involves many `_collect_direct_children` calls. Each call parses content_raw XML. Consider caching `_collect_direct_children` results since the same parent element types recur.

### Feature 7: ODD-aware validation (project customisation)

**Type:** Parser enhancement + OddStore enhancement + validator enhancement

**Integration:** This is the most architecturally significant feature. TEI projects use ODD customisation files that modify the base spec: deleting elements, constraining attributes, adding new elements. The validator must respect these customisations.

**New components:**
- `OddStore.apply_customisation(odd_path: str) -> OddStore` -- returns a new OddStore with customisations applied. Must NOT mutate the base store (other tools still need the full spec).
- OR: `parser.py`: `parse_customisation(path, base_store) -> OddStore` -- parse a customisation ODD and merge with base

**Modified components:**
- `validator.py`: Accept optional `customisation_store` parameter
- `server.py`: Tools that validate accept optional `odd_file` parameter

**ODD customisation operations to support:**
1. `elementSpec[@mode='delete']` -- element removed from valid set
2. `elementSpec[@mode='change']` -- element modified (attributes changed, content model altered)
3. `elementSpec[@mode='add']` -- new element added
4. `classSpec[@mode='delete'|'change']` -- class modifications
5. `moduleRef` with `@include`/`@except` -- module-level inclusion/exclusion

**Architecture decision:** Create a NEW OddStore instance for customised specs rather than mutating the base store. Reason: the server loads one base p5subset.xml at startup. Multiple projects may use different customisations. Each customisation should produce an independent OddStore.

**Data flow:**
```
validate_document(xml, odd_file="myproject.odd")
  -> parse base p5subset.xml store (already loaded at startup)
  -> parse_customisation("myproject.odd", base_store) -> custom_store
  -> validate_document(xml, custom_store)
```

**Caching consideration:** Parsing customisation files on every call is expensive. Cache parsed customisation stores keyed by file path + mtime.

## Component Dependency Graph

```
                    Feature Dependencies
                    ====================

valid_children -----> (none, uses existing _collect_direct_children)
batch_nesting ------> (none, uses existing check_nesting)
suggest_attribute --> (none, uses existing resolve_attributes)
deprecation --------> (model + parser changes, cross-cutting)

validate_element ---> deprecation (for warnings)
                  --> valid_children logic (for child checking)
                  --> resolve_attributes (for attr checking)

validate_document --> validate_element (applies per-node)

ODD-aware ---------> validate_document (customised validation)
                  --> parser changes (parse customisation files)
```

## New Module: validator.py

This is the primary new file for v2.0. It should contain:

```python
"""Document and element validation against TEI ODD specification."""

from __future__ import annotations
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from tei_mcp.store import OddStore

TEI_NS = "http://www.tei-c.org/ns/1.0"

@dataclass
class ValidationIssue:
    """A single validation error or warning."""
    severity: str          # "error" or "warning"
    element: str           # element ident where issue found
    xpath: str             # location in document
    code: str              # machine-readable issue code
    message: str           # human-readable description

def validate_element(
    xml_str: str,
    store: OddStore,
    parent: str | None = None,
) -> dict:
    """Validate a single element snippet."""
    ...

def validate_document(
    xml_str: str,
    store: OddStore,
    max_errors: int = 100,
) -> dict:
    """Validate a full TEI XML document."""
    ...

def _strip_ns(tag: str) -> str:
    """Strip namespace from element tag."""
    if "}" in tag:
        return tag.split("}")[1]
    return tag
```

**Issue codes** provide machine-readable error classification:

| Code | Meaning |
|------|---------|
| `UNKNOWN_ELEMENT` | Element not in spec |
| `INVALID_NESTING` | Child not allowed in parent |
| `UNKNOWN_ATTRIBUTE` | Attribute not valid for element |
| `INVALID_ATTR_VALUE` | Attribute value not in closed valList |
| `DEPRECATED_ELEMENT` | Element is deprecated |
| `DEPRECATED_ATTRIBUTE` | Attribute is deprecated |
| `EMPTY_CONTENT` | Element requires content but is empty |

## Suggested Build Order

Based on the dependency graph above:

```
Phase 5: Quick Wins (no dependencies)
  5.1: valid_children tool
  5.2: batch_check_nesting tool
  5.3: suggest_attribute tool

Phase 6: Deprecation (cross-cutting, needed before validation)
  6.1: Model + parser changes for deprecation data
  6.2: Surface deprecation in existing tools

Phase 7: Validation Core
  7.1: validator.py with validate_element
  7.2: validate_document (extends validator.py)

Phase 8: ODD Customisation
  8.1: ODD customisation parser
  8.2: Customised validation integration
```

**Rationale for this order:**

1. **Phase 5 first** because these features are pure additions with zero risk to existing functionality. They provide immediate value to LLM users and build confidence in the architecture before making cross-cutting changes.

2. **Phase 6 before Phase 7** because validate_element and validate_document need deprecation data to produce complete warnings. Building deprecation first means validation gets it for free.

3. **Phase 7 before Phase 8** because validate_document against the base spec must work correctly before adding customisation complexity. ODD customisation is the hardest feature and benefits from a stable validation foundation.

4. **Within Phase 5**, valid_children is simplest (wraps existing private method), batch_nesting is next (loops existing method), suggest_attribute is most involved (new search logic).

## Performance Considerations

### Caching _collect_direct_children

`validate_document` will call `_collect_direct_children` repeatedly for the same parent element types as it walks the tree. A document with 500 `<p>` elements inside `<div>` elements will call `_collect_direct_children("div")` 500 times, each time re-parsing the content_raw XML string.

**Recommendation:** Add a `_direct_children_cache: dict[str, set[str]]` to OddStore, populated lazily. This is safe because the store is immutable after construction.

```python
def _collect_direct_children(self, name: str) -> set[str]:
    if name in self._direct_children_cache:
        return self._direct_children_cache[name]
    # ... existing logic ...
    self._direct_children_cache[name] = result
    return result
```

### Document Size Limits

For `validate_document`, consider:
- Documents over 1MB: warn but proceed
- Documents over 10MB: refuse (LLM context is the bottleneck, not processing)
- Error cap at 100 by default (configurable)

### ODD Customisation Caching

Cache parsed customisation OddStores by `(file_path, mtime)` tuple. Most projects use a single customisation file that changes rarely.

## Patterns to Follow

### Pattern 5: Validation Issue Objects
**What:** Use structured `ValidationIssue` objects with severity, code, element, xpath, and message.
**When:** All validation output.
**Why:** Machine-readable codes let the LLM categorize and prioritize fixes. XPath locations let it navigate. Severity distinguishes errors (must fix) from warnings (should fix).

### Pattern 6: Namespace-Aware Input Handling
**What:** Strip TEI namespace from document elements before matching against OddStore idents.
**When:** All document/element validation.
**Why:** OddStore keys are bare idents ("p", "div"). Documents use namespaced tags ("{http://www.tei-c.org/ns/1.0}p"). Forgetting this mapping is a guaranteed bug.

### Pattern 7: Immutable Customisation
**What:** ODD customisation produces a NEW OddStore, never mutates the base store.
**When:** ODD-aware validation.
**Why:** The base store serves all non-customised queries. Mutation would corrupt the shared state. Creating a new store per customisation is cheap (dict copy + modifications) and safe.

## Anti-Patterns to Avoid

### Anti-Pattern 5: Validation in OddStore
**What:** Adding validate_element/validate_document methods directly to OddStore.
**Why bad:** OddStore is a data index + query engine for the spec. Validation is a consumer of that data, not part of the index itself. It deals with user-supplied XML, error collection, namespace handling -- concerns foreign to the store.
**Instead:** New `validator.py` module that imports and queries OddStore.

### Anti-Pattern 6: Parsing User XML with lxml
**What:** Using lxml for parsing user-supplied XML in validation.
**Why bad:** The existing codebase uses `xml.etree.ElementTree` (stdlib). Introducing lxml for validation creates an inconsistency. ET is sufficient for document walking and attribute checking.
**Instead:** Use `xml.etree.ElementTree` consistently. The parser already uses it successfully.

### Anti-Pattern 7: Monolithic Validation
**What:** One giant function that does all validation checks.
**Why bad:** Untestable. Individual checks (nesting, attributes, deprecation) can't be tested independently.
**Instead:** Compose validation from focused check functions: `_check_element_exists`, `_check_attributes`, `_check_nesting`, `_check_deprecation`. Each takes an element + store and returns issues.

## Modified File Summary

| File | Change Type | Features Affected |
|------|------------|-------------------|
| `models.py` | Modify (add fields) | Deprecation |
| `parser.py` | Modify (extract deprecation) | Deprecation, ODD customisation |
| `store.py` | Modify (new methods, cache) | valid_children, batch_nesting, suggest_attribute, deprecation surfacing |
| `server.py` | Modify (new tools, modify existing) | All 7 features |
| `validator.py` | **NEW** | validate_element, validate_document, ODD-aware validation |

## Sources

- Existing codebase analysis: `src/tei_mcp/store.py`, `models.py`, `parser.py`, `server.py`
- [TEI ODD customisation](https://tei-c.org/guidelines/customization/) - How ODD customisation files work (elementSpec modes, moduleRef include/except)
- [TEI elementSpec @validUntil](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-elementSpec.html) - Deprecation mechanism in ODD
- Project corpus analysis: 59 diplomatic letters exposing validation gaps (documented in PROJECT.md)
