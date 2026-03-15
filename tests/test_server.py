"""Tests for FastMCP server shell with lifespan-based data loading."""

import io
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


def test_server_logging_to_stderr():
    """Server module logger writes to stderr, never stdout."""
    from tei_mcp.server import logger

    # The tei-mcp logger must resolve to a handler that writes to stderr.
    # In pytest, basicConfig may be pre-empted, so we verify by actually
    # emitting a log record and checking no stdout output occurs.
    assert logger.name == "tei-mcp"

    # Capture stdout to prove logging does not write there
    old_stdout = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        logger.info("test message for stderr verification")
    finally:
        sys.stdout = old_stdout
    assert buf.getvalue() == "", "Logger must not write to stdout"


def test_server_instance_name():
    """Server can be instantiated and has name 'tei-mcp'."""
    from tei_mcp.server import mcp

    assert mcp.name == "tei-mcp"


def test_no_stdout_on_import(capsys):
    """No stdout output during server module import."""
    # Force reimport to capture any output
    import importlib

    import tei_mcp.server

    importlib.reload(tei_mcp.server)
    captured = capsys.readouterr()
    assert captured.out == "", f"Unexpected stdout: {captured.out!r}"


@pytest.mark.asyncio
async def test_lifespan_loads_store(test_odd_path: Path):
    """Lifespan loads store from test fixture and store has expected entity counts."""
    from tei_mcp.server import app_lifespan, mcp

    # Patch ensure_odd_file to return our test fixture path
    with patch(
        "tei_mcp.server.ensure_odd_file",
        new_callable=AsyncMock,
        return_value=test_odd_path,
    ):
        async with app_lifespan(mcp._mcp_server) as context:
            store = context["store"]
            assert store.element_count == 16
            assert store.class_count == 14
            assert store.macro_count == 1
            assert store.module_count == 4


def test_main_callable():
    """main() entry point exists and is callable."""
    from tei_mcp.server import main

    assert callable(main)


# --- Deprecation in tool response tests ---


class _FakeContext:
    """Minimal context stub providing lifespan_context with a store."""

    def __init__(self, store):
        self.lifespan_context = {"store": store}


@pytest.fixture
def ctx(test_odd_path: Path):
    """Return a FakeContext wrapping a parsed store."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    return _FakeContext(store)


@pytest.mark.asyncio
async def test_lookup_element_deprecated(ctx):
    """lookup_element('re') returns deprecation object with expired=True."""
    from tei_mcp.server import lookup_element

    result = await lookup_element("re", ctx)
    assert "deprecation" in result
    depr = result["deprecation"]
    assert depr["expired"] is True
    assert depr["valid_until"] == "2024-01-15"
    assert depr["severity"] == "error"
    assert "<gi>entry</gi>" in depr["info"]


@pytest.mark.asyncio
async def test_lookup_element_not_deprecated(ctx):
    """lookup_element('p') returns dict WITHOUT 'deprecation' key."""
    from tei_mcp.server import lookup_element

    result = await lookup_element("p", ctx)
    assert "deprecation" not in result


@pytest.mark.asyncio
async def test_lookup_element_deprecated_attr_count(ctx):
    """lookup_element('attRef') returns deprecated_attribute_count == 1."""
    from tei_mcp.server import lookup_element

    result = await lookup_element("attRef", ctx)
    assert result["deprecated_attribute_count"] == 1


@pytest.mark.asyncio
async def test_lookup_class_deprecated_attr(ctx):
    """lookup_class('att.ref') returns attributes with deprecation on 'name' attr."""
    from tei_mcp.server import lookup_class

    result = await lookup_class("att.ref", ctx)
    attrs = result["attributes"]
    name_attr = next(a for a in attrs if a["ident"] == "name")
    assert "deprecation" in name_attr
    assert name_attr["deprecation"]["valid_until"] == "2026-11-13"


# --- valid_children tool tests ---


@pytest.mark.asyncio
async def test_valid_children_tool(ctx):
    """MCP tool valid_children delegates to store and returns result."""
    from tei_mcp.server import valid_children

    result = await valid_children("persName", ctx)
    assert "error" not in result
    assert result["element"] == "persName"
    assert result["allows_text"] is True
    child_names = [c["name"] for c in result["children"]]
    assert "surname" in child_names
