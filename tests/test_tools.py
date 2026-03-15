"""Integration tests for MCP tool functions registered in server.py."""

from __future__ import annotations

from pathlib import Path

import pytest


class FakeContext:
    """Minimal stand-in for fastmcp.Context providing lifespan_context."""

    def __init__(self, store):
        from tei_mcp.validator import TEIValidator

        self.lifespan_context = {
            "store": store,
            "validator": TEIValidator(store),
            "custom_store": None,
            "custom_validator": None,
        }


@pytest.fixture
def ctx(parsed_store):
    """Return a FakeContext wrapping the parsed_store fixture."""
    return FakeContext(parsed_store)


# ---------------------------------------------------------------------------
# Import tool functions -- they are module-level async functions in server.py
# ---------------------------------------------------------------------------
from tei_mcp.server import (  # noqa: E402
    check_nesting,
    class_membership_chain,
    expand_content_model,
    list_attributes,
    list_module_elements,
    load_customisation,
    lookup_class,
    lookup_element,
    lookup_macro,
    search,
    unload_customisation,
    validate_document,
    validate_element,
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


# ---------------------------------------------------------------------------
# expand_content_model
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expand_content_model_tool(ctx):
    """expand_content_model returns structured tree with type field."""
    result = await expand_content_model("div", ctx)
    assert isinstance(result, dict)
    assert "name" in result
    assert result["name"] == "div"
    assert "type" in result


@pytest.mark.asyncio
async def test_expand_content_model_tool_not_found(ctx):
    """expand_content_model for unknown name returns error with suggestions."""
    result = await expand_content_model("nonexistent", ctx)
    assert isinstance(result, dict)
    assert "error" in result
    assert "suggestions" in result


@pytest.mark.asyncio
async def test_expand_content_model_tool_macro(ctx):
    """expand_content_model works for macro names."""
    result = await expand_content_model("macro.paraContent", ctx)
    assert isinstance(result, dict)
    assert "error" not in result


# ---------------------------------------------------------------------------
# check_nesting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_nesting_tool_direct(ctx):
    """check_nesting direct mode returns valid/invalid with reason."""
    result = await check_nesting("p", "div", ctx=ctx)
    assert isinstance(result, dict)
    assert "valid" in result
    assert "reason" in result
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_check_nesting_tool_recursive(ctx):
    """check_nesting recursive mode returns reachable with path."""
    result = await check_nesting("persName", "body", recursive=True, ctx=ctx)
    assert isinstance(result, dict)
    assert "reachable" in result
    assert "path" in result
    assert result["reachable"] is True
    assert len(result["path"]) >= 2


@pytest.mark.asyncio
async def test_check_nesting_tool_not_found(ctx):
    """check_nesting for unknown element returns error with suggestions."""
    result = await check_nesting("nonexistent", "div", ctx=ctx)
    assert isinstance(result, dict)
    assert "error" in result
    assert "suggestions" in result


# ---------------------------------------------------------------------------
# validate_document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_document_tool(ctx, tmp_path):
    """validate_document returns issues/summary/limitations for a TEI file."""
    tei_xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        "<text><body><p>Hello</p></body></text>"
        "</TEI>"
    )
    p = tmp_path / "test.xml"
    p.write_text(tei_xml, encoding="utf-8")

    result = await validate_document(str(p), ctx=ctx)
    assert isinstance(result, dict)
    assert "issues" in result
    assert "summary" in result
    assert "limitations" in result
    assert isinstance(result["issues"], list)


# ---------------------------------------------------------------------------
# validate_element
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_element_tool_xml(ctx):
    """validate_element with XML snippet returns issues/summary/limitations."""
    result = await validate_element("<hi>text</hi>", "p", ctx=ctx)
    assert isinstance(result, dict)
    assert "issues" in result
    assert "summary" in result
    assert "limitations" in result


@pytest.mark.asyncio
async def test_validate_element_tool_json(ctx):
    """validate_element with JSON string parses structured input."""
    import json

    element_json = json.dumps({"name": "hi", "attributes": {}, "children": []})
    result = await validate_element(element_json, "p", ctx=ctx)
    assert isinstance(result, dict)
    assert "issues" in result


# ---------------------------------------------------------------------------
# ODD customisation integration tests
# ---------------------------------------------------------------------------

ODD_FIXTURE = str(Path(__file__).parent / "fixtures" / "test_custom.odd")


@pytest.fixture
def odd_ctx(parsed_store):
    """Return a FakeContext with custom_store/custom_validator keys (initially None)."""
    return FakeContext(parsed_store)


@pytest.mark.asyncio
async def test_load_customisation(odd_ctx):
    """load_customisation with valid ODD path succeeds, returns element count."""
    result = await load_customisation(ODD_FIXTURE, ctx=odd_ctx)
    assert isinstance(result, dict)
    assert result["status"] == "loaded"
    assert "elements" in result
    assert "base_elements" in result
    assert result["elements"] < result["base_elements"]


@pytest.mark.asyncio
async def test_unload_customisation(odd_ctx):
    """After loading, unload_customisation clears the custom store."""
    await load_customisation(ODD_FIXTURE, ctx=odd_ctx)
    result = await unload_customisation(ctx=odd_ctx)
    assert result["status"] == "unloaded"
    assert odd_ctx.lifespan_context["custom_store"] is None
    assert odd_ctx.lifespan_context["custom_validator"] is None


@pytest.mark.asyncio
async def test_use_odd_flag(odd_ctx):
    """lookup_element with use_odd=True after loading ODD uses constrained store."""
    await load_customisation(ODD_FIXTURE, ctx=odd_ctx)
    # note was deleted in the ODD customisation
    result = await lookup_element("note", odd_ctx, use_odd=True)
    assert "error" in result


@pytest.mark.asyncio
async def test_use_odd_without_load(odd_ctx):
    """Calling lookup_element with use_odd=True without loading ODD returns error."""
    result = await lookup_element("p", odd_ctx, use_odd=True)
    assert "error" in result
    assert "load_customisation" in result["error"].lower() or "no odd" in result["error"].lower()


@pytest.mark.asyncio
async def test_use_odd_false_ignores_custom(odd_ctx):
    """After loading ODD, lookup_element with use_odd=False still returns deleted element."""
    await load_customisation(ODD_FIXTURE, ctx=odd_ctx)
    # note was deleted in the ODD, but use_odd=False should still find it in base
    result = await lookup_element("note", odd_ctx, use_odd=False)
    assert "error" not in result
    assert result["ident"] == "note"


@pytest.mark.asyncio
async def test_validate_document_use_odd(odd_ctx, tmp_path):
    """validate_document with use_odd=True flags elements not in customised schema."""
    # Document contains <note> which is deleted in the ODD
    tei_xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        "<text><body><p>Hello</p><note>Deleted</note></body></text>"
        "</TEI>"
    )
    p = tmp_path / "odd_test.xml"
    p.write_text(tei_xml, encoding="utf-8")
    await load_customisation(ODD_FIXTURE, ctx=odd_ctx)
    result = await validate_document(str(p), ctx=odd_ctx, use_odd=True)
    assert isinstance(result, dict)
    assert "issues" in result
    # There should be at least one issue about "note" being unknown
    note_issues = [i for i in result["issues"] if "note" in i.get("element", "").lower()
                   or "note" in i.get("message", "").lower()]
    assert len(note_issues) >= 1
