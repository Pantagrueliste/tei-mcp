# tei-mcp

An [MCP](https://modelcontextprotocol.io) server that gives LLMs access to the [TEI P5](https://tei-c.org/guidelines/) specification. It parses the TEI ODD and exposes tools for element lookup, attribute resolution, content model expansion, nesting validation, document validation, and ODD customisation.

## Features

- **Element, class, macro, and module lookup** with case-insensitive matching and typo suggestions
- **Attribute resolution** across the full TEI class hierarchy (local + inherited)
- **Content model expansion** into structured trees with class and macro resolution
- **Nesting validation** (direct parent-child and recursive reachability with path tracking)
- **Document validation** against TEI P5: content models, attributes, closed value lists, reference integrity, deprecation warnings
- **Single-element validation** for incremental editing workflows
- **ODD customisation** support: load a project ODD to constrain the schema (moduleRef filtering, elementSpec delete/change, attDef modifications)
- **Regex search** across all entity types (elements, classes, macros, modules)
- **Deprecation awareness** with validUntil dates and replacement suggestions
- **Attribute suggestion** by intent description (keyword matching against attribute descriptions)

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
# Clone and install
git clone https://github.com/Pantagrueliste/tei-mcp.git
cd tei-mcp
uv sync
```

On first run, the server downloads `p5subset.xml` from the TEI website (~5 MB) and caches it locally.

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tei": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/tei-mcp", "tei-mcp"]
    }
  }
}
```

### With Claude Code

Add to your project settings (`.mcp.json`):

```json
{
  "mcpServers": {
    "tei": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/tei-mcp", "tei-mcp"]
    }
  }
}
```

### Standalone

```bash
uv run tei-mcp
```

The server communicates over stdio using the MCP protocol.

## Tools

| Tool | Description |
|------|-------------|
| `lookup_element` | Look up an element by name (e.g., `persName`) |
| `lookup_class` | Look up a class by name (e.g., `att.global`) |
| `lookup_macro` | Look up a macro by name (e.g., `macro.paraContent`) |
| `list_module_elements` | List all elements in a module (e.g., `namesdates`) |
| `search` | Regex search across all TEI entities |
| `list_attributes` | Resolve all attributes for an element (local + inherited) |
| `class_membership_chain` | Show the full class hierarchy chain |
| `expand_content_model` | Expand content model into a structured tree |
| `valid_children` | List all valid direct children of an element |
| `check_nesting` | Check if an element can appear inside another |
| `check_nesting_batch` | Check multiple nesting pairs in one call |
| `suggest_attribute` | Find relevant attributes by intent description |
| `validate_document` | Validate a TEI XML file against the spec |
| `validate_element` | Validate a single element in context |
| `load_customisation` | Load an ODD customisation file |
| `unload_customisation` | Clear the loaded customisation |

Most tools accept `use_odd=True` to query the customised schema instead of the full TEI P5.

## ODD Customisation

Load a project-specific ODD file to constrain the schema:

```
1. Call load_customisation("/path/to/my-project.odd")
2. Use use_odd=True on subsequent tool calls
3. Call unload_customisation() to revert to the full spec
```

Supported ODD features:
- `moduleRef` with `include` / `except` filtering
- `elementSpec mode="delete"` to remove elements
- `elementSpec mode="change"` with `attDef` modifications (delete, change, add)
- Closed/semi value list restrictions

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEI_ODD_PATH` | — | Path to a local `p5subset.xml` (skips download) |
| `TEI_ODD_URL` | TEI-C GitHub URL | Custom URL for the ODD file |

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage info
uv run pytest -v
```

## License

MIT
