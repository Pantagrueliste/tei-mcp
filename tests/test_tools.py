"""Integration tests for MCP tool functions registered in server.py."""

from __future__ import annotations

import pytest


class FakeContext:
    """Minimal stand-in for fastmcp.Context providing lifespan_context."""

    def __init__(self, store):
        self.lifespan_context = {"store": store}


@pytest.fixture
def ctx(parsed_store):
    """Return a FakeContext wrapping the parsed_store fixture."""
    return FakeContext(parsed_store)


# ---------------------------------------------------------------------------
# Import tool functions -- they are module-level async functions in server.py
# ---------------------------------------------------------------------------
from tei_mcp.server import (  # noqa: E402
    class_membership_chain,
    list_attributes,
    list_module_elements,
    lookup_class,
    lookup_element,
    lookup_macro,
    search,
)


# ---------------------------------------------------------------------------
# lookup_element
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_element_found(ctx):
    result = await lookup_element("p", ctx)
    assert isinstance(result, dict)
    for key in ("ident", "module", "gloss", "desc", "classes", "attributes", "content_raw"):
        assert key in result, f"Missing key: {key}"
    assert result["ident"] == "p"


@pytest.mark.asyncio
async def test_lookup_element_case_insensitive(ctx):
    result = await lookup_element("persname", ctx)
    assert isinstance(result, dict)
    assert result["ident"] == "persName"


@pytest.mark.asyncio
async def test_lookup_element_not_found(ctx):
    result = await lookup_element("nonexistent", ctx)
    assert isinstance(result, dict)
    assert "error" in result
    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)


# ---------------------------------------------------------------------------
# lookup_class
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_class_with_members(ctx):
    result = await lookup_class("att.global", ctx)
    assert isinstance(result, dict)
    for key in ("ident", "class_type", "desc", "members", "classes"):
        assert key in result, f"Missing key: {key}"
    assert isinstance(result["members"], list)


@pytest.mark.asyncio
async def test_lookup_class_not_found(ctx):
    result = await lookup_class("nonexistent", ctx)
    assert isinstance(result, dict)
    assert "error" in result
    assert "suggestions" in result


# ---------------------------------------------------------------------------
# lookup_macro
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_macro_found(ctx):
    result = await lookup_macro("macro.paraContent", ctx)
    assert isinstance(result, dict)
    for key in ("ident", "module", "gloss", "desc", "content_raw"):
        assert key in result, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_lookup_macro_not_found(ctx):
    result = await lookup_macro("nonexistent", ctx)
    assert isinstance(result, dict)
    assert "error" in result
    assert "suggestions" in result


# ---------------------------------------------------------------------------
# list_module_elements
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_module_elements_found(ctx):
    result = await list_module_elements("core", ctx)
    assert isinstance(result, dict)
    assert "module" in result
    assert "gloss" in result
    assert "elements" in result
    assert isinstance(result["elements"], list)
    if result["elements"]:
        elem = result["elements"][0]
        assert "ident" in elem
        assert "gloss" in elem


@pytest.mark.asyncio
async def test_list_module_elements_not_found(ctx):
    result = await list_module_elements("nonexistent", ctx)
    assert isinstance(result, dict)
    assert "error" in result
    assert "suggestions" in result


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_matches_fields(ctx):
    results = await search("pers", ctx=ctx)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert any("match_field" in r for r in results)


@pytest.mark.asyncio
async def test_search_result_shape(ctx):
    results = await search("p", ctx=ctx)
    assert isinstance(results, list)
    for r in results:
        for key in ("type", "ident", "gloss", "match_field"):
            assert key in r, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_search_invalid_regex(ctx):
    result = await search("[invalid", ctx=ctx)
    assert isinstance(result, dict)
    assert "error" in result


@pytest.mark.asyncio
async def test_search_entity_type_filter(ctx):
    results = await search(".*", entity_type="element", ctx=ctx)
    assert isinstance(results, list)
    for r in results:
        assert r["type"] == "element"


@pytest.mark.asyncio
async def test_search_max_results(ctx):
    results = await search(".*", max_results=2, ctx=ctx)
    assert isinstance(results, list)
    assert len(results) <= 2


# ---------------------------------------------------------------------------
# list_attributes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_attributes_found(ctx):
    result = await list_attributes("persName", ctx)
    assert isinstance(result, dict)
    assert "element" in result
    assert "attributes" in result
    assert isinstance(result["attributes"], list)
    # Should have both local and inherited attrs
    sources = {a["source"] for a in result["attributes"]}
    assert "local" in sources
    # At least one inherited attribute from att.global (e.g., xml:id, n)
    assert any(s != "local" for s in sources)


@pytest.mark.asyncio
async def test_list_attributes_attr_shape(ctx):
    result = await list_attributes("persName", ctx)
    for attr in result["attributes"]:
        for key in ("name", "source", "datatype", "values", "closed"):
            assert key in attr, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_list_attributes_case_insensitive(ctx):
    result = await list_attributes("PERSNAME", ctx)
    assert isinstance(result, dict)
    assert "element" in result
    assert result["element"] == "persName"


@pytest.mark.asyncio
async def test_list_attributes_not_found(ctx):
    result = await list_attributes("nonexistent", ctx)
    assert isinstance(result, dict)
    assert "error" in result
    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)


@pytest.mark.asyncio
async def test_list_attributes_class_name(ctx):
    result = await list_attributes("att.global", ctx)
    assert isinstance(result, dict)
    assert "attributes" in result


# ---------------------------------------------------------------------------
# class_membership_chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_class_membership_chain_found(ctx):
    result = await class_membership_chain("persName", ctx)
    assert isinstance(result, dict)
    assert "entity" in result
    assert "chains" in result
    assert isinstance(result["chains"], list)
    assert len(result["chains"]) >= 1


@pytest.mark.asyncio
async def test_class_membership_chain_steps(ctx):
    result = await class_membership_chain("persName", ctx)
    for chain in result["chains"]:
        assert isinstance(chain, list)
        for step in chain:
            for key in ("ident", "type", "gloss"):
                assert key in step, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_class_membership_chain_not_found(ctx):
    result = await class_membership_chain("nonexistent", ctx)
    assert isinstance(result, dict)
    assert "error" in result
    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)


@pytest.mark.asyncio
async def test_class_membership_chain_class_name(ctx):
    result = await class_membership_chain("att.naming", ctx)
    assert isinstance(result, dict)
    assert "entity" in result
    assert "chains" in result
    # att.naming should have a chain through att.canonical
    all_idents = [step["ident"] for chain in result["chains"] for step in chain]
    assert "att.canonical" in all_idents
