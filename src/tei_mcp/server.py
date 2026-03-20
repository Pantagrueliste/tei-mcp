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

import xml.etree.ElementTree as ET  # noqa: E402

from tei_mcp import __version__  # noqa: E402
from tei_mcp.customisation import apply_customisation  # noqa: E402
from tei_mcp.download import ensure_odd_file  # noqa: E402
from tei_mcp.parser import parse_odd  # noqa: E402
from tei_mcp.store import OddStore, _build_deprecation_obj  # noqa: E402
from tei_mcp.validator import TEIValidator  # noqa: E402

BANNER = r"""
  ╔╦╗╔═╗╦  ╔╦╗╔═╗╔═╗
   ║ ║╣ ║  ║║║║  ╠═╝
   ╩ ╚═╝╩  ╩ ╩╚═╝╩
"""


def _print_banner(store: OddStore) -> None:
    """Print startup banner with version and spec stats to stderr."""
    lines = BANNER.rstrip().split("\n")
    lines.append("  TEI P5 for AI agents")
    lines.append(f"  v{__version__} · {store.element_count} elements · "
                 f"{store.class_count} classes · {store.module_count} modules")
    lines.append("")
    sys.stderr.write("\n".join(lines) + "\n")


@lifespan
async def app_lifespan(server):
    """Download (if needed) and parse p5subset.xml at server startup."""
    odd_path = await ensure_odd_file()
    logger.info("Parsing ODD file: %s", odd_path)
    store = parse_odd(odd_path)
    _print_banner(store)
    validator = TEIValidator(store)
    try:
        yield {
            "store": store,
            "validator": validator,
            "custom_store": None,
            "custom_validator": None,
        }
    finally:
        logger.info("Server shutting down")


mcp = FastMCP("tei-mcp", lifespan=app_lifespan)


def _get_store(ctx: Context, use_odd: bool) -> OddStore:
    """Return the customised or base OddStore depending on use_odd flag."""
    if use_odd:
        custom = ctx.lifespan_context.get("custom_store")
        if custom is None:
            raise ValueError("No ODD customisation loaded. Call load_customisation first.")
        return custom
    return ctx.lifespan_context["store"]


def _get_validator(ctx: Context, use_odd: bool) -> TEIValidator:
    """Return the customised or base TEIValidator depending on use_odd flag."""
    if use_odd:
        custom = ctx.lifespan_context.get("custom_validator")
        if custom is None:
            raise ValueError("No ODD customisation loaded. Call load_customisation first.")
        return custom
    return ctx.lifespan_context["validator"]


@mcp.tool()
async def load_customisation(
    ctx: Context,
    odd_path: str | None = None,
    odd_content: str | None = None,
) -> dict:
    """Load a project ODD customisation to constrain validation.

    Provide either odd_path (a local file path) or odd_content (the raw XML
    string of the ODD file). When using a remote server, pass odd_content
    directly since the server cannot access your local filesystem.

    Parses the ODD and creates a constrained OddStore. Returns element count
    comparison (customised vs base).
    Set use_odd=True on other tools to query the customised schema.
    """
    base_store = ctx.lifespan_context["store"]
    try:
        custom_store = apply_customisation(base_store, odd_path=odd_path, odd_content=odd_content)
    except (ValueError, FileNotFoundError, ET.ParseError) as e:
        return {"error": str(e)}
    custom_validator = TEIValidator(custom_store)
    ctx.lifespan_context["custom_store"] = custom_store
    ctx.lifespan_context["custom_validator"] = custom_validator
    return {
        "status": "loaded",
        "elements": custom_store.element_count,
        "base_elements": base_store.element_count,
    }


@mcp.tool()
async def unload_customisation(ctx: Context) -> dict:
    """Clear the loaded ODD customisation.

    After unloading, all tools return to using the full TEI P5 spec.
    Calling a tool with use_odd=True after unloading will return an error.
    """
    ctx.lifespan_context["custom_store"] = None
    ctx.lifespan_context["custom_validator"] = None
    return {"status": "unloaded"}


@mcp.tool()
async def lookup_element(name: str, ctx: Context, use_odd: bool = False) -> dict:
    """Look up a TEI element by name (case-insensitive).

    Returns the element's ident, module, gloss, desc, classes, attributes,
    and content_raw. If not found, returns an error with suggestions.
    Set use_odd=True to query the customised schema.

    Example: lookup_element("persName")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
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
async def lookup_class(name: str, ctx: Context, use_odd: bool = False) -> dict:
    """Look up a TEI class by name (case-insensitive).

    Returns the class's ident, module, class_type, gloss, desc, classes,
    attributes, and a computed members list of element/subclass idents.
    If not found, returns an error with suggestions.
    Set use_odd=True to query the customised schema.

    Example: lookup_class("att.global")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
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
async def lookup_macro(name: str, ctx: Context, use_odd: bool = False) -> dict:
    """Look up a TEI macro by name (case-insensitive).

    Returns the macro's ident, module, gloss, desc, and content_raw.
    If not found, returns an error with suggestions.
    Set use_odd=True to query the customised schema.

    Example: lookup_macro("macro.paraContent")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    macro_def = store.get_macro_ci(name)
    if macro_def is None:
        return {
            "error": f"Macro '{name}' not found",
            "suggestions": store.suggest_names(name, "macro"),
        }
    return asdict(macro_def)


@mcp.tool()
async def list_module_elements(module: str, ctx: Context, use_odd: bool = False) -> dict:
    """List all elements in a TEI module.

    Returns the module's ident, gloss, and a list of {ident, gloss} pairs
    for each element. If module not found, returns an error with suggestions.
    Set use_odd=True to query the customised schema.

    Example: list_module_elements("namesdates")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
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
    use_odd: bool = False,
    ctx: Context = None,
) -> list[dict] | dict:
    """Search TEI entities by regex pattern across ident, gloss, and desc.

    Each result includes type, ident, gloss, and match_field (which field
    matched). Optionally filter by entity_type and limit results.
    Set use_odd=True to query the customised schema.

    Example: search("pers.*Name")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    return store.search(pattern, entity_type, max_results)


@mcp.tool()
async def list_attributes(name: str, ctx: Context, use_odd: bool = False) -> dict:
    """List all attributes for a TEI element or class, including inherited attributes.

    Returns a flat list of attributes with local attributes first, then inherited
    in hierarchy order (nearest class first). Each attribute includes its name,
    source class (or "local"), datatype, allowed values, and whether the value
    list is closed. Local overrides of inherited attributes include an "overrides"
    field indicating which class was overridden.

    Accepts both element names (e.g., "persName") and att.* class names
    (e.g., "att.global"). Case-insensitive lookup with suggestions on not-found.
    Set use_odd=True to query the customised schema.

    Example: list_attributes("persName")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    return store.resolve_attributes(name)


@mcp.tool()
async def class_membership_chain(name: str, ctx: Context, use_odd: bool = False) -> dict:
    """Show the full class membership hierarchy for a TEI element or class.

    Returns separate chains for each direct class membership. Each chain walks
    upward through the class hierarchy to the root. Each step includes the
    class ident, type (model or atts), and gloss.

    Accepts both element names (e.g., "persName") and class names
    (e.g., "model.nameLike.agent"). Case-insensitive lookup with suggestions
    on not-found.
    Set use_odd=True to query the customised schema.

    Example: class_membership_chain("persName")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    return store.get_class_chain(name)


@mcp.tool()
async def expand_content_model(name: str, ctx: Context, use_odd: bool = False) -> dict:
    """Expand the content model for a TEI element or macro into a structured tree.

    Returns a nested JSON tree preserving structural semantics (sequence,
    alternation, repetition). Class references are resolved to concrete
    element names with 'via' annotations. Macro references are recursively
    resolved inline.

    Accepts both element names (e.g., "div", "p") and macro names
    (e.g., "macro.paraContent"). Case-insensitive lookup with suggestions
    on not-found.
    Set use_odd=True to query the customised schema.

    Example: expand_content_model("div")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    return store.expand_content_model(name)


@mcp.tool()
async def valid_children(name: str, ctx: Context, use_odd: bool = False) -> dict:
    """List all elements that can appear as direct children of the given element.

    Returns a flat, deduplicated list of child element names with required/optional
    flags. Also indicates whether the element allows text content, any element,
    or has an empty content model.
    Set use_odd=True to query the customised schema.

    Example: valid_children("div")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    return store.valid_children(name)


@mcp.tool()
async def suggest_attribute(name: str, intent: str, ctx: Context, use_odd: bool = False) -> dict:
    """Find the most relevant attributes for an element by describing what you want.

    Searches attribute descriptions for keyword matches against your intent.
    Returns the top 5 matching attributes with name, description, source class,
    and relevance score.
    Set use_odd=True to query the customised schema.

    Example: suggest_attribute("persName", "link to authority")
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    return store.suggest_attribute(name, intent)


@mcp.tool()
async def check_nesting_batch(
    pairs: list[dict],
    recursive: bool = False,
    use_odd: bool = False,
    ctx: Context = None,
) -> dict:
    """Check multiple parent-child nesting relationships in a single call.

    Each pair is a dict with 'child' and 'parent' keys. The recursive flag
    applies to all pairs (True = check reachability anywhere inside ancestor,
    False = check direct parent-child only).

    Returns results for all pairs. If a pair has a typo, that pair gets an
    error with suggestions while other pairs still return valid results.
    Set use_odd=True to query the customised schema.

    Example: check_nesting_batch([{"child": "p", "parent": "div"}, {"child": "head", "parent": "div"}])
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    return store.check_nesting_batch(pairs, recursive=recursive)


@mcp.tool()
async def check_nesting(
    child: str,
    parent: str,
    recursive: bool = False,
    use_odd: bool = False,
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
    Set use_odd=True to query the customised schema.

    Example: check_nesting("p", "div")
    Example: check_nesting("persName", "body", recursive=True)
    """
    try:
        store: OddStore = _get_store(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    return store.check_nesting(child, parent, recursive=recursive)


@mcp.tool()
async def validate_document(
    ctx: Context,
    file_path: str | None = None,
    xml_content: str | None = None,
    authority_files: list[str] | None = None,
    authority_contents: list[str] | None = None,
    use_odd: bool = False,
) -> dict:
    """Validate a TEI XML document against the TEI P5 specification.

    Checks content model compliance, attribute validity, closed value lists,
    empty required-content elements, reference integrity, and deprecation usage.
    Set use_odd=True to query the customised schema.

    Provide either file_path (a local file path) or xml_content (the raw XML
    string). When using a remote server, pass xml_content directly since the
    server cannot access your local filesystem.

    Authority files can likewise be provided as local file paths
    (authority_files) or as raw XML strings (authority_contents).

    Returns a dict with 'issues' (list of validation issues), 'summary'
    (counts by severity and rule), and 'limitations' (what was NOT checked).
    """
    try:
        validator: TEIValidator = _get_validator(ctx, use_odd)
        return validator.validate_file(
            path=file_path,
            xml_content=xml_content,
            authority_files=authority_files,
            authority_contents=authority_contents,
        )
    except (ValueError, FileNotFoundError) as e:
        return {"error": str(e)}


@mcp.tool()
async def validate_element(
    element: str,
    parent: str,
    use_odd: bool = False,
    ctx: Context = None,
) -> dict:
    """Validate a single TEI element in context for incremental editing.

    Accepts a raw XML snippet (e.g., '<add place="above">text</add>') or
    a JSON-formatted string with keys 'name', 'attributes', 'children'.
    Set use_odd=True to query the customised schema.

    Args:
        element: XML snippet string or JSON string with element details.
        parent: The parent element name (required for nesting validation).

    Returns a dict with 'issues', 'summary', and 'limitations'.
    """
    import json

    try:
        validator: TEIValidator = _get_validator(ctx, use_odd)
    except ValueError as e:
        return {"error": str(e)}
    # Try JSON parse for structured input
    if not element.strip().startswith("<"):
        try:
            element = json.loads(element)
        except json.JSONDecodeError:
            return {
                "error": "element must be an XML snippet or JSON object "
                "with 'name', 'attributes', 'children' keys"
            }
    return validator.validate_element(element, parent)


def main():
    """Entry point for the tei-mcp console script."""
    mcp.run()
