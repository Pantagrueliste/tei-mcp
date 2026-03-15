# Technology Stack: v2.0 Additions

**Project:** TEI-P5 MCP Server (v2.0 Document Validation & Enhanced Querying)
**Researched:** 2026-03-15
**Scope:** NEW stack requirements only. Existing stack (Python 3.13, FastMCP, uv, stdlib xml.etree.ElementTree, dataclasses, difflib, httpx) is validated and not re-assessed.

## Critical Context: Existing Stack Reality

The v1.0 codebase uses `xml.etree.ElementTree` (stdlib), NOT `lxml`. The previous research recommended lxml but it was never adopted. This is actually fine for v2.0:

| What Code Uses | What v1.0 Research Said | Reality |
|----------------|------------------------|---------|
| `xml.etree.ElementTree` | "Use lxml for XPath" | Stdlib ET works. BFS-based hierarchy walking replaces XPath axis queries. No performance issue at ~5MB XML. |
| `dataclasses(frozen=True)` | "Use Pydantic" | Frozen dataclasses + `asdict()` work cleanly. Pydantic would require migrating all models. Not worth it for v2.0. |
| `difflib` | Not mentioned | Already used for `suggest_names()`. Appropriate for `suggest_attribute` too. |

**Decision: Do NOT migrate to lxml or Pydantic for v2.0.** The existing patterns work. Adding lxml just for `sourceline` when the project is already built on stdlib ET would create two XML parsing stacks. Instead, use lxml ONLY for the document validation feature where `sourceline` is needed (user-submitted TEI documents), keeping stdlib ET for ODD spec parsing.

## Recommended Stack Additions

### New Runtime Dependency

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| lxml | >=5.0 | TEI document parsing with line numbers | `sourceline` property on elements returns the original line number from the parser. This is essential for `validate_document` -- error messages like "line 42: `<seg>` has deprecated attribute `part`" are useless without line numbers. stdlib `xml.etree.ElementTree` has NO line number support (Python issue #14078, never resolved). lxml is the only option. | HIGH |

**Confidence rationale:** Verified via [lxml API docs](https://lxml.de/apidoc/lxml.etree.html) that `sourceline` returns `int | None` on all `ElementBase` objects. Verified via [Python tracker](https://bugs.python.org/issue14078) that stdlib ET will not get sourceline.

### lxml Usage Boundary

Use lxml for ONE purpose only: parsing user-submitted TEI XML documents in `validate_document` and `validate_element`.

```python
# Document validation: lxml for line numbers
from lxml import etree as lxml_etree

def parse_tei_document(xml_content: str) -> lxml_etree._Element:
    """Parse a TEI XML document with line number tracking."""
    parser = lxml_etree.XMLParser(remove_blank_text=False)
    root = lxml_etree.fromstring(xml_content.encode("utf-8"), parser)
    return root  # Every element has .sourceline -> int | None
```

Do NOT use lxml for:
- Parsing p5subset.xml (keep stdlib ET in `parser.py`)
- Content model expansion (keep stdlib ET in `store.py`)
- ODD customisation file parsing (use stdlib ET -- customisations are spec-like, not user documents)

### No New Dependencies Required

All other v2.0 features use existing stdlib or patterns:

| Feature | Technology | Why No New Dependency |
|---------|-----------|----------------------|
| Deprecation awareness | stdlib `datetime.date` | `validUntil` is `yyyy-mm-dd` format. `datetime.date.fromisoformat()` handles parsing. Compare with `datetime.date.today()` for status. |
| ODD customisation parsing | `xml.etree.ElementTree` | Customisation files have the same TEI namespace structure as p5subset.xml. Existing parser patterns apply. No line numbers needed -- errors are spec configuration issues, not document validation. |
| `suggest_attribute` | `difflib.SequenceMatcher` | Already used in `suggest_names()`. Attribute intent matching = fuzzy match intent keywords against attribute `desc` fields. `get_close_matches()` with lowered cutoff (0.3) handles intent phrases like "language" matching `xml:lang`. |
| `valid_children` | Existing `_collect_direct_children()` | Already implemented in `store.py`. The new tool is a thin wrapper returning a sorted list. |
| Batch `check_nesting` | Existing `check_nesting()` | Loop over pairs, collect results. No new tech needed. |

## Deprecation Detection: How It Works in p5subset.xml

**Confidence: HIGH** (verified directly in the actual p5subset.xml file at `src/tei_mcp/data/p5subset.xml`)

Deprecation is marked via two mechanisms in the ODD:

### 1. `@validUntil` attribute on spec elements

Appears on `elementSpec`, `attDef`, `dataSpec`, and potentially `classSpec` or `macroSpec`.

```xml
<!-- Deprecated element (superEntry, removed after 2027-03-07) -->
<elementSpec module="dictionaries" ident="superEntry" validUntil="2027-03-07">

<!-- Deprecated attribute (name on attRef, removed after 2026-11-13) -->
<attDef ident="name" validUntil="2026-11-13">

<!-- Deprecated datatype -->
<dataSpec module="tei" ident="teidata.point" validUntil="2050-02-25">
```

**Found in current p5subset.xml:**
- `superEntry` element: `validUntil="2027-03-07"`
- `re` element: `validUntil="2026-03-10"` (ALREADY PAST as of today)
- `name` attribute on `attRef`: `validUntil="2026-11-13"`

### 2. `<desc type="deprecationInfo">` child element

Provides human-readable explanation of the deprecation:

```xml
<desc xml:lang="en" type="deprecationInfo" versionDate="2024-03-07">
  Because an entry can now occur inside an entry, the superEntry
  element is no longer needed.
</desc>
```

### Parser Changes Required

The existing `_parse_element_spec()` and `_parse_att_def()` functions need to extract:
1. `validUntil` attribute value (string, `yyyy-mm-dd` format)
2. `desc[@type='deprecationInfo']` text content

This means adding fields to the frozen dataclasses:

```python
@dataclass(frozen=True)
class AttDef:
    ident: str
    desc: str
    datatype: str
    values: tuple[str, ...]
    closed: bool
    valid_until: str  # NEW: "" if not deprecated, "yyyy-mm-dd" if deprecated

@dataclass(frozen=True)
class ElementDef:
    # ... existing fields ...
    valid_until: str  # NEW
    deprecation_info: str  # NEW: text from desc[@type='deprecationInfo']
```

**Integration note:** Adding fields to frozen dataclasses with default values (`valid_until: str = ""`) is backward-compatible -- existing `ElementDef(...)` construction calls don't break.

## ODD Customisation File Structure

**Confidence: MEDIUM** (verified via [TEI customisation docs](https://tei-c.org/guidelines/customization/getting-started-with-p5-odds/) and [att.deprecated docs](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-att.deprecated.html))

An ODD customisation file is a TEI XML document containing a `<schemaSpec>` with:

```xml
<schemaSpec ident="myProject" start="TEI" source="tei:current">
  <!-- Include modules -->
  <moduleRef key="core"/>
  <moduleRef key="header"/>
  <moduleRef key="textstructure"/>
  <moduleRef key="namesdates"/>

  <!-- Exclude specific elements from included modules -->
  <elementSpec ident="superEntry" mode="delete"/>

  <!-- Modify element: restrict attributes -->
  <elementSpec ident="div" mode="change">
    <attList>
      <attDef ident="type" mode="change" usage="req">
        <valList type="closed">
          <valItem ident="chapter"/>
          <valItem ident="section"/>
        </valList>
      </attDef>
    </attList>
  </elementSpec>

  <!-- Add constraint to element -->
  <elementSpec ident="persName" mode="change">
    <attList>
      <attDef ident="ref" mode="change" usage="req"/>
    </attList>
  </elementSpec>
</schemaSpec>
```

### Key ODD Customisation Operations

| Operation | ODD Markup | Effect on Validation |
|-----------|-----------|---------------------|
| Include module | `<moduleRef key="core"/>` | Only elements from listed modules are valid |
| Include subset | `<moduleRef key="core" include="p hi emph"/>` | Only named elements from module are valid |
| Exclude elements | `<moduleRef key="core" except="q said"/>` | Named elements removed from module |
| Delete element | `<elementSpec ident="X" mode="delete"/>` | Element X is invalid |
| Change attribute | `<attDef ident="Y" mode="change"/>` | Attribute Y constraints modified |
| Delete attribute | `<attDef ident="Y" mode="delete"/>` | Attribute Y is invalid on parent element |
| Require attribute | `<attDef ident="Y" usage="req"/>` | Attribute Y must be present |
| Close value list | `<valList type="closed">` | Only listed values are valid |

### Parsing Strategy

Use existing stdlib ET patterns. The customisation parser:
1. Extracts `<moduleRef>` elements to determine which modules are active
2. Collects `<elementSpec mode="delete">` to build exclusion set
3. Collects `<elementSpec mode="change">` to build override map (attribute restrictions, value list closures)
4. Applies overrides to the base OddStore to produce a project-specific view

**No new parser library needed.** The customisation file uses the same TEI namespace (`http://www.tei-c.org/ns/1.0`) as p5subset.xml.

## suggest_attribute: Intent Matching Strategy

**Confidence: HIGH** (difflib is stdlib and already proven in this codebase)

The `suggest_attribute` tool maps intent keywords to attribute names. Three-tier matching:

### Tier 1: Exact attribute name match
If the user says "xml:lang", return the `xml:lang` attribute directly.

### Tier 2: Keyword-in-description match
Search attribute `desc` fields for the intent keyword. Example: intent "language" matches `xml:lang` because its desc contains "language".

```python
def suggest_attribute(element: str, intent: str) -> list[dict]:
    attrs = store.resolve_attributes(element)["attributes"]
    # Score each attribute by keyword overlap with desc
    scored = []
    for attr in attrs:
        score = _intent_score(intent, attr["name"], attr.get("desc", ""))
        if score > 0:
            scored.append((score, attr))
    return sorted(scored, key=lambda x: -x[0])[:5]
```

### Tier 3: Fuzzy match via difflib
Use `SequenceMatcher.ratio()` when no exact keyword match. Cutoff at 0.3 for broad matching.

**No external NLP library needed.** The attribute descriptions in TEI are short, technical, and keyword-rich. Simple substring + difflib matching handles the use case. Adding something like `rapidfuzz` or `thefuzz` would be over-engineering.

## What NOT to Add for v2.0

| Technology | Why Not |
|------------|---------|
| `lxml` for ODD parsing | Would create two XML stacks. Stdlib ET handles p5subset.xml fine. Only use lxml for user document validation. |
| Pydantic | Would require migrating all models. Frozen dataclasses + `asdict()` work. Migration can happen in a future major version if warranted. |
| `rapidfuzz` / `thefuzz` | For suggest_attribute fuzzy matching. difflib is already in use and sufficient. These add C dependencies for marginal improvement on a small search space (~50-100 attributes per element). |
| `jsonschema` | For validating tool inputs. FastMCP handles input validation via type hints and auto-generated JSON schema. |
| `click` / `typer` | For CLI args. The server has no CLI beyond `tei-mcp` entry point. FastMCP handles this. |
| RELAX NG validation (`lxml.etree.RelaxNG`) | Tempting for full schema validation, but out of scope. The project validates against expanded content models, not compiled schemas. Schema generation is explicitly out of scope per PROJECT.md. |
| `aiofiles` | For async file reading. Document validation reads files synchronously (small TEI files, <1MB typically). Async adds complexity for no gain. |

## Installation Changes

```bash
# Add lxml as runtime dependency
uv add "lxml>=5.0"

# Add lxml type stubs for development
uv add --group dev "types-lxml>=2025.1"
```

### Updated pyproject.toml dependencies section

```toml
[project]
dependencies = [
    "fastmcp>=3.1.0",
    "httpx>=0.27",
    "lxml>=5.0",        # NEW: document validation with line numbers
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "types-lxml>=2025.1",  # NEW: lxml type stubs
]
```

## Integration Points

### lxml <-> stdlib ET boundary

```
User TEI Document (XML string)
    |
    v
lxml.etree.fromstring()  <-- lxml only here
    |
    v
Walk elements with .tag, .attrib, .sourceline
    |
    v
Check each element against OddStore (stdlib ET-based)
    |
    v
Return validation errors with line numbers
```

The two XML stacks never mix. lxml parses user documents. Stdlib ET parses the ODD spec. They communicate through string element names and attribute dicts -- no lxml/ET object crossing.

### Deprecation <-> existing tools

Deprecation info flows through existing tool responses:

```
Parser extracts validUntil + deprecationInfo
    |
    v
Stored on ElementDef / AttDef dataclass fields
    |
    v
lookup_element adds "deprecated": true, "valid_until": "2027-03-07"
list_attributes adds "deprecated": true per attribute
validate_document flags deprecated elements/attributes as warnings
```

## Sources

- [lxml API reference: sourceline property](https://lxml.de/apidoc/lxml.etree.html) -- HIGH confidence
- [lxml parsing guide](https://lxml.de/parsing.html) -- HIGH confidence
- [Python issue #14078: sourceline for stdlib ET](https://bugs.python.org/issue14078) -- confirms stdlib ET will NOT get sourceline
- [TEI att.deprecated class](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-att.deprecated.html) -- HIGH confidence, `@validUntil` attribute definition
- [TEI Getting Started with P5 ODDs](https://tei-c.org/guidelines/customization/getting-started-with-p5-odds/) -- MEDIUM confidence, customisation structure
- [TEI elementSpec reference](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-elementSpec.html) -- mode attribute values
- [TEI moduleRef reference](https://tei-c.org/release/doc/tei-p5-doc/en/html/ref-moduleRef.html) -- include/except attributes
- [Python difflib docs](https://docs.python.org/3/library/difflib.html) -- SequenceMatcher for intent matching
- p5subset.xml (local, `src/tei_mcp/data/p5subset.xml`) -- verified deprecation markup patterns directly
