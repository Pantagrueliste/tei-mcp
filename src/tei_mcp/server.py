"""FastMCP server for querying the TEI P5 ODD specification."""

# Configure logging to stderr BEFORE any other imports that might set up logging.
import logging
import sys

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tei-mcp")

from dataclasses import asdict  # noqa: E402

from fastmcp import Context, FastMCP  # noqa: E402
from fastmcp.server.lifespan import lifespan  # noqa: E402

from tei_mcp.download import ensure_odd_file  # noqa: E402
from tei_mcp.parser import parse_odd  # noqa: E402
from tei_mcp.store import OddStore, _build_deprecation_obj  # noqa: E402


@lifespan
async def app_lifespan(server):
    """Download (if needed) and parse p5subset.xml at server startup."""
    odd_path = await ensure_odd_file()
    logger.info("Parsing ODD file: %s", odd_path)
    store = parse_odd(odd_path)
    logger.info(
        "Loaded %d elements, %d classes, %d macros, %d modules",
        store.element_count,
        store.class_count,
        store.macro_count,
        store.module_count,
    )
    try:
        yield {"store": store}
    finally:
        logger.info("Server shutting down")


mcp = FastMCP("tei-mcp", lifespan=app_lifespan)

@mcp.tool()
async def lookup_element(name: str, ctx: Context) -> dict:
    """Look up a TEI element by name (case-insensitive).

    Returns the element's ident, module, gloss, desc, classes, attributes,
    and content_raw. If not found, returns an error with suggestions.

    Example: lookup_element("persName")
    """
    store: OddStore = ctx.lifespan_context["store"]
    elem = store.get_element_ci(name)
    if elem is None:
        return {
            "error": f"Element '{name}' not found",
            "suggestions": store.suggest_names(name, "element"),
        }
    result = asdict(elem)
    # Add element-level deprecation object
    depr = _build_deprecation_obj(
        result.pop("valid_until", ""), result.pop("deprecation_info", "")
    )
    if depr:
        result["deprecation"] = depr
    # Clean up and enrich attribute-level deprecation
    for attr_dict in result.get("attributes", []):
        vu = attr_dict.pop("valid_until", "")
        di = attr_dict.pop("deprecation_info", "")
        attr_depr = _build_deprecation_obj(vu, di)
        if attr_depr:
            attr_dict["deprecation"] = attr_depr
    # Count deprecated attributes (including inherited)
    all_attrs = store.resolve_attributes(elem.ident)
    if "attributes" in all_attrs:
        depr_count = sum(1 for a in all_attrs["attributes"] if "deprecation" in a)
        if depr_count > 0:
            result["deprecated_attribute_count"] = depr_count
    return result


@mcp.tool()
async def lookup_class(name: str, ctx: Context) -> dict:
    """Look up a TEI class by name (case-insensitive).

    Returns the class's ident, module, class_type, gloss, desc, classes,
    attributes, and a computed members list of element/subclass idents.
    If not found, returns an error with suggestions.

    Example: lookup_class("att.global")
    """
    store: OddStore = ctx.lifespan_context["store"]
    cls_def = store.get_class_ci(name)
    if cls_def is None:
        return {
            "error": f"Class '{name}' not found",
            "suggestions": store.suggest_names(name, "class"),
        }
    result = asdict(cls_def)
    result["members"] = store.get_class_members(cls_def.ident)
    # Enrich attribute-level deprecation in asdict output
    for attr_dict in result.get("attributes", []):
        vu = attr_dict.pop("valid_until", "")
        di = attr_dict.pop("deprecation_info", "")
        attr_depr = _build_deprecation_obj(vu, di)
        if attr_depr:
            attr_dict["deprecation"] = attr_depr
    return result


@mcp.tool()
async def lookup_macro(name: str, ctx: Context) -> dict:
    """Look up a TEI macro by name (case-insensitive).

    Returns the macro's ident, module, gloss, desc, and content_raw.
    If not found, returns an error with suggestions.

    Example: lookup_macro("macro.paraContent")
    """
    store: OddStore = ctx.lifespan_context["store"]
    macro_def = store.get_macro_ci(name)
    if macro_def is None:
        return {
            "error": f"Macro '{name}' not found",
            "suggestions": store.suggest_names(name, "macro"),
        }
    return asdict(macro_def)


@mcp.tool()
async def list_module_elements(module: str, ctx: Context) -> dict:
    """List all elements in a TEI module.

    Returns the module's ident, gloss, and a list of {ident, gloss} pairs
    for each element. If module not found, returns an error with suggestions.

    Example: list_module_elements("namesdates")
    """
    store: OddStore = ctx.lifespan_context["store"]
    mod_def = store.get_module_ci(module)
    if mod_def is None:
        return {
            "error": f"Module '{module}' not found",
            "suggestions": store.suggest_names(module, "module"),
        }
    elements = store.get_module_elements(mod_def.ident)
    element_list = [{"ident": e.ident, "gloss": e.gloss} for e in elements]
    return {"module": mod_def.ident, "gloss": mod_def.gloss, "elements": element_list}


@mcp.tool()
async def search(
    pattern: str,
    entity_type: str | None = None,
    max_results: int = 50,
    ctx: Context = None,
) -> list[dict] | dict:
    """Search TEI entities by regex pattern across ident, gloss, and desc.

    Each result includes type, ident, gloss, and match_field (which field
    matched). Optionally filter by entity_type and limit results.

    Example: search("pers.*Name")
    """
    store: OddStore = ctx.lifespan_context["store"]
    return store.search(pattern, entity_type, max_results)


@mcp.tool()
async def list_attributes(name: str, ctx: Context) -> dict:
    """List all attributes for a TEI element or class, including inherited attributes.

    Returns a flat list of attributes with local attributes first, then inherited
    in hierarchy order (nearest class first). Each attribute includes its name,
    source class (or "local"), datatype, allowed values, and whether the value
    list is closed. Local overrides of inherited attributes include an "overrides"
    field indicating which class was overridden.

    Accepts both element names (e.g., "persName") and att.* class names
    (e.g., "att.global"). Case-insensitive lookup with suggestions on not-found.

    Example: list_attributes("persName")
    """
    store: OddStore = ctx.lifespan_context["store"]
    return store.resolve_attributes(name)


@mcp.tool()
async def class_membership_chain(name: str, ctx: Context) -> dict:
    """Show the full class membership hierarchy for a TEI element or class.

    Returns separate chains for each direct class membership. Each chain walks
    upward through the class hierarchy to the root. Each step includes the
    class ident, type (model or atts), and gloss.

    Accepts both element names (e.g., "persName") and class names
    (e.g., "model.nameLike.agent"). Case-insensitive lookup with suggestions
    on not-found.

    Example: class_membership_chain("persName")
    """
    store: OddStore = ctx.lifespan_context["store"]
    return store.get_class_chain(name)


@mcp.tool()
async def expand_content_model(name: str, ctx: Context) -> dict:
    """Expand the content model for a TEI element or macro into a structured tree.

    Returns a nested JSON tree preserving structural semantics (sequence,
    alternation, repetition). Class references are resolved to concrete
    element names with 'via' annotations. Macro references are recursively
    resolved inline.

    Accepts both element names (e.g., "div", "p") and macro names
    (e.g., "macro.paraContent"). Case-insensitive lookup with suggestions
    on not-found.

    Example: expand_content_model("div")
    """
    store: OddStore = ctx.lifespan_context["store"]
    return store.expand_content_model(name)


@mcp.tool()
async def check_nesting(
    child: str,
    parent: str,
    recursive: bool = False,
    ctx: Context = None,
) -> dict:
    """Check whether a TEI element can appear inside another element.

    By default checks direct parent-child validity. Set recursive=True
    to check if the child can appear anywhere nested inside the ancestor
    (with path tracking and cycle detection).

    Direct mode returns: {valid, child, parent, reason}
    Recursive mode returns: {reachable, child, ancestor, path, reason}

    The reason field explains why nesting is valid or invalid -- useful
    for understanding TEI structure and self-correcting markup.

    Example: check_nesting("p", "div")
    Example: check_nesting("persName", "body", recursive=True)
    """
    store: OddStore = ctx.lifespan_context["store"]
    return store.check_nesting(child, parent, recursive=recursive)


def main():
    """Entry point for the tei-mcp console script."""
    mcp.run()
