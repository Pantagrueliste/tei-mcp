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
            assert store.element_count == 3
            assert store.class_count == 2
            assert store.macro_count == 1
            assert store.module_count == 2


def test_main_callable():
    """main() entry point exists and is callable."""
    from tei_mcp.server import main

    assert callable(main)
