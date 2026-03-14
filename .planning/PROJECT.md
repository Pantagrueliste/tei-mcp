# tei-mcp

## What This Is

A Python MCP server that parses the TEI-P5 ODD specification (p5subset.xml) and exposes the full TEI Guidelines as queryable, read-only tools for LLMs. Designed as an encoding assistant — an LLM uses it as a live reference while building TEI XML markup, checking valid elements, attributes, content models, and nesting as it goes. Built with FastMCP (stdio transport), lxml for XML parsing, and uv for package management.

## Core Value

An LLM can accurately look up any TEI element's attributes, content model, and valid nesting — so it produces correct TEI markup without hallucinating the spec.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Parse p5subset.xml once at startup and build in-memory data structures for elements, classes, macros, and modules
- [ ] Download script to fetch p5subset.xml from the TEIC/TEI GitHub repo
- [ ] Tool: look up elements by name (returns structural data — attributes, content model, classes, module)
- [ ] Tool: look up classes by name (model classes and attribute classes)
- [ ] Tool: look up macros by name
- [ ] Tool: look up modules by name (list contained elements)
- [ ] Tool: search across element/class names, glosses, and descriptions using regex
- [ ] Tool: list element attributes including those inherited from the attribute class hierarchy
- [ ] Tool: show content models with class references expanded to concrete elements
- [ ] Tool: check direct parent-child nesting validity (can X be an immediate child of Y?)
- [ ] Tool: check recursive nesting reachability (can X appear anywhere inside Y?)
- [ ] All tools return JSON, all are read-only
- [ ] FastMCP server with stdio transport
- [ ] uv for package management

### Out of Scope

- Prose/remarks from the Guidelines — structure only (attributes, content models, classes)
- Module subsetting or filtering — full spec is always loaded
- Write operations or spec modification
- HTTP/SSE transport — stdio only
- Mobile or web UI

## Context

- TEI-P5 is the XML schema for encoding humanities texts. The spec is defined in ODD (One Document Does it all) format.
- p5subset.xml is the compiled ODD subset from https://github.com/TEIC/TEI — it contains element declarations, class definitions, macro definitions, and content models for the full Guidelines.
- Content models in TEI use class references (e.g., model.pLike) that must be expanded to find concrete elements. Attribute classes (e.g., att.global) contribute attributes to member elements.
- The class hierarchy can be several levels deep — proper attribute/content resolution requires walking the full tree.

## Constraints

- **Data source**: p5subset.xml from TEIC/TEI GitHub repo — single authoritative file
- **Transport**: stdio only (FastMCP)
- **Runtime**: Python with lxml for XML parsing
- **Package management**: uv
- **Responses**: JSON only, structural data only (no Guidelines prose)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Structure-only responses (no prose) | Keeps payloads small and focused for encoding assistance | — Pending |
| Both direct and recursive nesting checks | Direct for quick validation, recursive for complex nesting scenarios | — Pending |
| Regex search over substring | More flexible for pattern matching across spec entities | — Pending |
| Full spec loaded (no module filtering) | Simplifies implementation, encoding may touch any module | — Pending |

---
*Last updated: 2026-03-14 after initialization*
