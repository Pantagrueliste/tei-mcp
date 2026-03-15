# Domain Pitfalls

**Domain:** TEI-P5 ODD MCP Server -- v2.0 Document Validation & Enhanced Querying
**Researched:** 2026-03-15
**Scope:** Pitfalls specific to adding validate_document, deprecation awareness, valid_children, batch nesting, suggest_attribute, and ODD-aware validation to the existing v1.0 MCP server

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Existing Parser Uses stdlib xml.etree.ElementTree -- No Line Numbers for Document Validation

**What goes wrong:** The `validate_document` tool needs to report errors with line numbers so the LLM can locate and fix problems. The existing parser (`parser.py`, `store.py`) uses Python's `xml.etree.ElementTree`, which does NOT track line numbers. stdlib ET elements have no `sourceline` attribute. Switching to lxml for document parsing while keeping stdlib ET for spec parsing creates two different XML APIs in the same codebase, leading to subtle bugs where code written for one API is called with elements from the other.

**Why it happens:** v1.0 did not need line numbers -- it parsed p5subset.xml once at startup for structural data. Document validation is fundamentally different: it parses user-submitted XML and must report WHERE errors occur.

**Consequences:**
- Without line numbers, validation errors are useless ("element X is invalid" with no location)
- lxml is not even in `pyproject.toml` dependencies -- adding it is a dependency change
- Mixing stdlib ET and lxml.etree in the same codebase causes type confusion (`ET.Element` vs `lxml.etree._Element` are different types)
- lxml's `sourceline` caps at 65535 on libxml2 < 2.9 (affects files over 65K lines)

**Prevention:**
- Add `lxml` to `pyproject.toml` dependencies
- Use lxml ONLY for document validation (parsing user TEI files), keep stdlib ET for spec parsing -- clear boundary
- Or migrate both to lxml, but this is a larger change that risks breaking existing tests
- For the document parser, always use `lxml.etree.parse()` or `lxml.etree.fromstring()`, never stdlib ET
- Verify libxml2 version >= 2.9 for correct sourceline on large files (most modern systems have this)
- Document the boundary: "spec parsing = stdlib ET, document parsing = lxml"

**Detection:** If validation errors lack line numbers or report line 0, the wrong parser is being used.

**Phase:** Must be resolved at the very start of v2.0, before validate_document implementation.

---

### Pitfall 2: TEI Namespace Not Handled When Parsing Real Documents

**What goes wrong:** Real TEI documents declare the TEI namespace: `<TEI xmlns="http://www.tei-c.org/ns/1.0">`. This means every element is in the `{http://www.tei-c.org/ns/1.0}` namespace. But the existing store's element lookups use bare names (`"p"`, `"div"`, `"persName"`). If `validate_document` parses a real document with lxml, every element tag will be `{http://www.tei-c.org/ns/1.0}p`, not `p`. Naively calling `store.get_element(tag)` will always return None.

**Why it happens:** The spec parser strips namespaces during parsing (line 398 of store.py: `tag = el.tag.split("}")[1] if "}" in el.tag else el.tag`). This works because the store uses bare idents. But document elements arrive with full namespace URIs.

**Consequences:**
- Every element in a valid TEI document is reported as "unknown element" -- 100% false positive rate
- The tool becomes completely unusable, not just inaccurate

**Prevention:**
- In the document validator, strip the TEI namespace prefix from element tags before looking them up in the store: `local_name = etree.QName(element).localname` (lxml) or split on `}`
- Handle elements NOT in the TEI namespace differently: they may be valid (e.g., MathML, SVG via `<anyElement>`) or invalid (typo in namespace URI)
- Handle the case where a document does NOT declare a namespace (bare `<TEI>` without xmlns) -- this is technically non-conformant but common in practice
- Test with both namespaced (`<TEI xmlns="...">`) and bare (`<TEI>`) documents

**Detection:** If validate_document reports every element as unknown, namespace stripping is missing.

**Phase:** First thing to handle in validate_document implementation.

---

### Pitfall 3: Content Model Validation Is Fundamentally Limited -- Overpromising Correctness

**What goes wrong:** The existing content model expansion produces a tree of sequences, alternations, and element refs with cardinality. But validating a document against these content models is NOT equivalent to schema validation. TEI has constraints that content models alone cannot express: co-occurrence constraints (Schematron rules), datatype validation, attribute value interdependencies, and prose-described requirements. If `validate_document` claims to do "full validation" but only checks content model nesting, users will trust false negatives (passing documents that are actually invalid).

**Why it happens:** The gap between "what elements can appear here" and "is this document valid" is much larger than it appears:
- Content models say `<choice>` can contain `sic|corr`, but Schematron rules enforce they come in pairs
- Content models say `<date>` has optional `@when`, but the spec requires at least one dating attribute
- Sequence ordering is specified in content models but the current `_collect_direct_children` flattens to a set, losing order

**Consequences:**
- Users assume validated documents are correct, submit them to archives, and get rejected
- False sense of security is worse than no validation at all

**Prevention:**
- Name the tool clearly: `validate_document` should be documented as "content model and attribute validation" not "full TEI validation"
- Report validation scope in every response: "Checked: element nesting, attribute validity, deprecations. NOT checked: Schematron constraints, datatype patterns, co-occurrence rules"
- Include a `limitations` field in the response JSON
- Explicitly list out-of-scope checks in tool documentation
- Consider adding a `validate_schema` tool later that uses lxml's RelaxNG validation for full schema checking

**Detection:** Compare validate_document results against `xmllint --relaxng tei_all.rng` on the same file. Differences reveal the gap.

**Phase:** Tool design and documentation, before implementation begins.

---

### Pitfall 4: Duplicating Store Logic Instead of Reusing It

**What goes wrong:** `validate_document` needs to check nesting, attributes, and content models for every element in a document. The store already has `check_nesting`, `resolve_attributes`, and `expand_content_model`. The temptation is to write separate, "optimized" validation logic that reimplements these checks inline. This creates two sources of truth: the MCP tools and the validator check different things, diverge over time, and produce contradictory results.

**Why it happens:** The existing store methods are designed for single-element queries (look up one element, check one nesting pair). Document validation needs to check hundreds of elements efficiently. The naive approach -- calling `check_nesting()` for every parent-child pair in a document -- parses content models repeatedly. The reflex is to "optimize" by inlining and deduplicating.

**Consequences:**
- `check_nesting("p", "div")` says valid, but `validate_document` on a file with `<div><p>` says invalid (or vice versa)
- Bug fixes in one path don't propagate to the other
- Test coverage must be duplicated

**Prevention:**
- Extract the core logic into cacheable primitives. `_collect_direct_children(parent)` already returns a set -- cache it (it's pure, same input = same output)
- Build `validate_document` ON TOP OF store methods, not alongside them
- Add a `_direct_children_cache: dict[str, set[str]]` to OddStore, populated lazily
- For attribute validation, call `resolve_attributes` once per element name (not per element occurrence), cache the result
- Performance target: validate a 1000-element document in < 2 seconds using cached lookups

**Detection:** Write a test that validates a document, then calls the individual tools on the same elements, and asserts results match.

**Phase:** Architecture decision before validate_document coding begins.

---

## Moderate Pitfalls

### Pitfall 5: Deprecation Data Is Sparse and Inconsistent in p5subset.xml

**What goes wrong:** The milestone assumes deprecation info can be surfaced across all tools. But p5subset.xml uses `@validUntil` on spec elements (elementSpec, attDef, etc.) to mark deprecation, NOT a simple boolean flag. The current data has only a handful of deprecated items:
- `<superEntry>` element: `validUntil="2027-03-07"`
- `<re>` element: `validUntil="2026-03-10"` (already expired!)
- `@name` on one attDef: `validUntil="2026-11-13"`
- `teidata.point` dataSpec: `validUntil="2050-02-25"`

There is NO `deprecated="true"` attribute. Deprecation info lives in `<desc type="deprecationInfo">` child elements, which contain prose, not structured data. The existing `ElementDef` and `AttDef` models have no field for deprecation status.

**Why it happens:** TEI uses a date-based deprecation model via the `att.deprecated` class, not a boolean flag. A construct is deprecated if it has a `@validUntil` date. It is expired if that date is in the past.

**Prevention:**
- Add `valid_until: str | None` field to `ElementDef`, `ClassDef`, `MacroDef`, `AttDef`
- Add `deprecation_info: str` field for the prose explanation from `<desc type="deprecationInfo">`
- Parse `@validUntil` from elementSpec, classSpec, macroSpec, attDef elements
- Parse `<desc type="deprecationInfo">` as the deprecation explanation
- Compare `validUntil` against current date to determine status: "active", "deprecated" (future date), "expired" (past date)
- Do NOT assume most elements have deprecation info -- only a few do currently
- Surface deprecation in ALL tools: lookup_element, list_attributes, check_nesting should all flag deprecated items

**Detection:** If `lookup_element("re")` doesn't mention deprecation, the parser isn't extracting `@validUntil`.

**Phase:** Parser enrichment, early in v2.0 (before validate_document, since validation should flag deprecated usage).

---

### Pitfall 6: ODD Customisation Semantics Are Deceptively Complex

**What goes wrong:** ODD-aware validation requires parsing a project's customisation file and applying its modifications to the base TEI spec. ODD files use `@mode` attributes on spec elements with four values: `add`, `delete`, `change`, `replace`. Each has different merge semantics:
- `delete`: Remove the element entirely from the schema
- `change`: Merge child elements (replace matching children, keep others)
- `replace`: Completely replace the spec with the customisation's version
- `add`: Add a new element not in the base TEI

Getting ANY of these wrong produces a silently incorrect customised schema.

**Why it happens:** The `change` mode is particularly treacherous. It does not replace the entire spec -- it replaces only the children that are present in the customisation. An ODD that adds one attribute via `change` must preserve all other attributes from the base spec. This requires a deep merge, not a shallow replace. Most first implementations get this wrong.

**Consequences:**
- `delete` mode: If not handled, deleted elements are treated as valid, and the validator passes documents that a project's actual schema would reject
- `change` mode: If implemented as full replace, customisations that modify one attribute accidentally delete all other attributes
- Module inclusion/exclusion: ODDs specify which modules to include via `<moduleRef>`. Elements from excluded modules should not be valid. This is easy to miss because the base spec loads everything

**Prevention:**
- Start with module-level filtering only: parse `<moduleRef>` elements to determine which modules are active, filter the store's element index accordingly
- Then add `delete` mode: straightforward removal from the filtered index
- Then add `change` mode with proper deep merge: for each child element type (classes, attList, content), merge if present in customisation, keep base if not
- Defer `add` mode (custom elements not in TEI) and `replace` mode to a later phase if time-constrained
- Test against a real-world ODD (e.g., TEI Lite, TEI Bare) and compare results against Roma-generated schemas

**Detection:** Validate a document against TEI Lite ODD. If elements excluded from TEI Lite (e.g., `<msDesc>`) are reported as valid, module filtering is broken.

**Phase:** Last feature in v2.0. The most complex and most likely to need its own research spike.

---

### Pitfall 7: validate_document Input Size and Timeout Risk

**What goes wrong:** Real TEI documents can be enormous. A critical edition of a novel might be 50,000+ lines of XML. The `validate_document` tool must parse the entire document, walk every element, check nesting for every parent-child pair, and validate attributes. Without performance guardrails, this can take minutes and either timeout the MCP call or produce a response with thousands of errors that exceeds the 25K token limit.

**Why it happens:** MCP tools are synchronous from the client's perspective. There is no streaming progress. The client waits for a complete response.

**Consequences:**
- MCP client timeout (typically 30-60 seconds) kills the validation mid-run
- Response with 500+ errors is truncated at the token limit, losing the most important errors
- Memory usage spikes if the full document tree is held alongside validation results

**Prevention:**
- Accept XML as a file path, not as inline content in the tool call (avoids MCP message size limits)
- Set a configurable `max_errors` parameter (default: 50) that stops validation after N errors
- Report errors in priority order: structural errors first, then attribute errors, then deprecation warnings
- For very large files, validate in a streaming fashion: iterparse with lxml, check each element as it's encountered, don't build a full tree if possible
- Include a `truncated: true` flag and `total_error_estimate` in the response when hitting limits
- Measure and log validation time to stderr

**Detection:** Test with a 10,000+ line TEI file. If it takes > 10 seconds or the response is truncated, guardrails are needed.

**Phase:** validate_document design phase, before implementation.

---

### Pitfall 8: valid_children Flattening Loses Critical Context

**What goes wrong:** The `valid_children` tool returns a flat list of allowed child elements for a parent. But the existing `_collect_direct_children` method already does this (returns a `set[str]`). The pitfall is returning ONLY the flat set without indicating whether children are required vs optional, exclusive (alternation) vs cumulative (sequence), or repeatable. A flat list of `["p", "list", "table", "head"]` for `<div>` doesn't tell the LLM that `<head>` is optional and comes first, while at least one of `p|list|table` is required.

**Why it happens:** Extracting a flat list is easy -- it's already implemented. Adding structural annotations requires walking the content model tree and preserving semantics, which is the hard part.

**Prevention:**
- Return the flat list (for simple queries) BUT include an `ordered` or `structured` field that preserves key constraints
- At minimum, annotate each child with `required: true/false` based on `minOccurs` of its containing group
- Consider a `model_summary` string field: `"(head?, (model.divLike | model.divPart)+)"` for human-readable structure
- Reuse `expand_content_model` internally -- don't reimplement content model walking

**Detection:** If valid_children for `<div>` returns a flat list identical to `_collect_direct_children`, it's not adding enough value over the existing check_nesting tool.

**Phase:** valid_children tool design.

---

### Pitfall 9: suggest_attribute Keyword Matching Is Fragile

**What goes wrong:** The `suggest_attribute` tool finds the right attribute for an element given intent keywords (e.g., "language" -> `@xml:lang`). Naive string matching on attribute idents will miss most matches because TEI attribute names are terse abbreviations: `@rend` for rendering, `@resp` for responsibility, `@cert` for certainty. The attribute name alone does not convey its purpose.

**Why it happens:** Attribute idents are short codes, not descriptive names. The descriptive text is in `<desc>` elements. But the current `AttDef` model stores `desc` -- the challenge is building a good search index over it.

**Prevention:**
- Search across attribute `desc` text, not just `ident`
- Also search the attribute class desc (e.g., `att.datable.w3c` desc mentions "dating" even if individual attributes like `@when` don't)
- Consider fuzzy matching (the store already has `difflib.get_close_matches` for element names)
- Return attributes ranked by relevance: exact ident match > desc keyword match > class desc match
- Include the source class in results so the LLM understands provenance

**Detection:** Test `suggest_attribute("persName", "language")` -- it should find `@xml:lang` from att.global. If it returns nothing, keyword search is too narrow.

**Phase:** suggest_attribute implementation.

---

### Pitfall 10: Batch check_nesting N+1 Query Pattern

**What goes wrong:** Batch check_nesting accepts multiple (child, parent) pairs. The naive implementation loops over pairs and calls `check_nesting` for each one. Each call to `check_nesting` calls `_collect_direct_children`, which calls `_parse_content_tree`, which calls `ET.fromstring` on the content XML. If 20 pairs share the same parent, the content model is parsed 20 times.

**Why it happens:** The existing `check_nesting` was designed for single-pair queries. Batching it without caching just multiplies the cost.

**Consequences:** A batch of 50 pairs with 10 unique parents should require 10 content model parses, but actually does 50. This is a 5x performance penalty that will be noticeable for validate_document (which effectively does batch nesting for every element in the document).

**Prevention:**
- Add `@functools.lru_cache` to `_collect_direct_children` (requires making it take only hashable args -- it already does, just `name: str`)
- Or add an explicit `_direct_children_cache: dict[str, set[str]]` on OddStore, populated lazily
- For batch check_nesting, group pairs by parent, compute direct children once per unique parent, then check all children against that set
- This same cache benefits validate_document enormously

**Detection:** Profile batch check_nesting with 100 pairs. If it's more than 2x slower than checking unique parents, caching is missing.

**Phase:** Batch check_nesting implementation, but the caching infrastructure benefits validate_document too.

---

## Minor Pitfalls

### Pitfall 11: lxml.etree.fromstring vs lxml.etree.parse for Documents

**What goes wrong:** If validate_document accepts XML as a string (from the MCP tool call), using `lxml.etree.fromstring()` loses the ability to report file-relative line numbers. If it accepts a file path, using `lxml.etree.parse()` preserves sourceline information correctly. Mixing the two approaches or switching between them produces inconsistent line number reporting.

**Prevention:** Accept file paths for validate_document. Use `lxml.etree.parse(path)` consistently. If string input is needed, write to a temp file first or document that line numbers start from the string, not from the original file.

**Phase:** validate_document API design.

---

### Pitfall 12: Frozen Dataclasses Block Adding Deprecation Fields

**What goes wrong:** The existing models (`ElementDef`, `AttDef`, `ClassDef`, `MacroDef`) are `@dataclass(frozen=True)`. Adding new fields like `valid_until` and `deprecation_info` requires updating every constructor call in the parser and every test fixture. Frozen dataclasses cannot be mutated after creation, so you cannot "patch in" deprecation data after initial parsing.

**Why it happens:** Frozen dataclasses are a good design choice for immutability. But they make schema evolution more work.

**Prevention:**
- Add new fields with defaults (`valid_until: str | None = None`, `deprecation_info: str = ""`) so existing constructor calls don't break
- Update the parser to extract and pass the new fields
- Update test fixtures that construct these models directly
- Consider if any tests use `==` comparison on models (frozen dataclasses get `__eq__` for free) -- new fields will affect equality

**Detection:** If adding a field without a default, every `ElementDef(...)` call in tests and parser will fail with TypeError.

**Phase:** First implementation step -- model enrichment before any feature work.

---

### Pitfall 13: validate_element Context Requires Parent Chain

**What goes wrong:** The `validate_element` tool checks a single element "in context" for incremental editing. But "in context" means knowing the element's parent, grandparent, etc. If the tool only receives the element's XML, it cannot check nesting validity. If it receives the element plus its parent name, it can check direct nesting but not deeper context (e.g., `<p>` is valid in `<div>` but not in `<p>` -- the grandparent matters for some checks).

**Prevention:**
- Define the API clearly: accept `element_xml` plus `parent_name` (and optionally `ancestors: list[str]`)
- For most cases, parent name alone is sufficient for nesting checks
- Document that validate_element checks the same things as validate_document but for a single element
- Reuse the same validation logic as validate_document, just scoped to one element

**Phase:** validate_element design.

---

### Pitfall 14: Attribute Validation Must Handle xml: Prefix Specially

**What goes wrong:** TEI elements commonly have attributes in the XML namespace: `xml:id`, `xml:lang`, `xml:space`, `xml:base`. In a parsed document (lxml), these appear as `{http://www.w3.org/XML/1998/namespace}id`. But in the store, they're stored as `xml:id` (the ident from the spec). Comparing `{http://www.w3.org/XML/1998/namespace}id` against `xml:id` fails unless explicitly mapped.

**Prevention:**
- Map `{http://www.w3.org/XML/1998/namespace}` prefix to `xml:` when normalizing document attribute names
- Similarly handle `{http://www.w3.org/XML/1998/namespace}lang` -> `xml:lang`
- Test attribute validation with a real element that has `xml:id` and `xml:lang`

**Detection:** If validate_document reports `xml:id` as an invalid attribute on every element, namespace mapping for attributes is broken.

**Phase:** Attribute validation in validate_document.

---

### Pitfall 15: ODD moduleRef @include and @except Filtering

**What goes wrong:** ODD files don't just include or exclude whole modules. A `<moduleRef>` can have `@include` (only include these elements from the module) or `@except` (include all elements from the module except these). Implementing only module-level filtering misses this granularity, causing the validator to accept elements that the project's schema excludes.

**Prevention:**
- Parse `@include` and `@except` on `<moduleRef>` elements
- `@include="a b c"` means only elements a, b, c from that module are valid
- `@except="x y"` means all elements from that module EXCEPT x and y
- These are space-separated lists of element idents
- Test with TEI Lite, which uses `@include` on several moduleRefs

**Phase:** ODD-aware validation implementation.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Model enrichment (deprecation fields) | Frozen dataclass schema evolution | Add fields with defaults, update parser and tests |
| Deprecation awareness | Sparse data, date-based not boolean | Parse `@validUntil` + `<desc type="deprecationInfo">`, compare against current date |
| validate_document | No line numbers with stdlib ET | Use lxml for document parsing, keep stdlib ET for spec |
| validate_document | TEI namespace not stripped | Strip `{http://www.tei-c.org/ns/1.0}` from element tags |
| validate_document | Overpromising validation scope | Document limitations in every response |
| validate_document | Input size / timeout | max_errors cap, streaming parse, file path input |
| validate_document | Duplicating store logic | Build on top of cached store methods |
| valid_children | Flat list loses structure | Include ordering/optionality annotations |
| batch check_nesting | N+1 content model parsing | Cache `_collect_direct_children` results |
| suggest_attribute | Terse ident names miss keyword matches | Search desc text + class desc, not just idents |
| validate_element | Context requires parent chain | Accept parent_name + optional ancestors |
| Attribute validation | xml: namespace prefix mismatch | Map XML namespace URI to `xml:` prefix |
| ODD-aware validation | Complex merge semantics (change/delete/replace) | Start with module filtering + delete, defer change/replace |
| ODD-aware validation | moduleRef @include/@except granularity | Parse element-level filtering attributes |

## Sources

- [lxml sourceline 65535 cap bug](https://bugs.launchpad.net/lxml/+bug/1341590) -- confirmed fixed in lxml 3.3.4+ with libxml2 2.9+
- [lxml sourceline incorrect for long files](https://bugs.launchpad.net/lxml/+bug/674775) -- original bug report
- [lxml sourceline with remove_blank_text](https://bugs.launchpad.net/lxml/+bug/1742121) -- off-by-one with parser options
- [Validating TEI-XML with Python](https://adrien.barbaresi.eu/blog/validating-tei-xml-python.html) -- lxml-based TEI validation approaches
- [lxml validation documentation](https://lxml.de/validation.html) -- RelaxNG and Schematron support
- [lxml namespace handling](https://webscraping.ai/faq/lxml/how-do-i-handle-namespaces-in-xml-parsing-with-lxml) -- namespace map patterns
- [xml.etree.ElementTree vs lxml](https://bjoernricks.github.io/posts/python/stdlib-etree-vs-lxml-etree/) -- API differences and namespace handling
- [TEI Using the TEI (Chapter 24)](https://tei-c.org/release/doc/tei-p5-doc/en/html/USE.html) -- ODD customisation semantics, mode attributes
- [Getting Started with P5 ODDs](https://tei-c.org/guidelines/customization/getting-started-with-p5-odds/) -- module inclusion, element deletion
- [TEI elementSpec specification](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-elementSpec.html) -- mode attribute values
- [TEI attDef specification](https://www.tei-c.org/release/doc/tei-p5-doc/en/html/ref-attDef.html) -- validUntil on attributes
- [TEI Documentation Elements (Chapter 23)](https://www.tei-c.org/release/doc/tei-p5-doc/en/html/TD.html) -- constraintSpec, Schematron limitations
- [TEI att.deprecated class](https://www.tei-c.org/release/doc/tei-p5-doc/en/html/ref-att.deprecated.html) -- validUntil attribute semantics
- [TEI conformance and validation](https://classics-at.chs.harvard.edu/what-is-tei-conformance-and-why-should-you-care/) -- limits of schema vs content model validation
- Direct analysis of `/Users/cag30/tei-p5/src/tei_mcp/data/p5subset.xml` -- deprecation instances verified (superEntry, re, @name, teidata.point)
- Direct analysis of existing codebase (`store.py`, `parser.py`, `models.py`, `server.py`, `pyproject.toml`)
