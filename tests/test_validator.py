"""Tests for TEIValidator scaffold and validate_file response shape."""

from pathlib import Path

import pytest


VALID_TEI = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>Test</title></titleStmt>
  <publicationStmt><p>Test</p></publicationStmt>
  <sourceDesc><p>Test</p></sourceDesc></fileDesc></teiHeader>
  <text><body><p>Hello world</p></body></text>
</TEI>
"""


@pytest.fixture
def valid_tei_path(tmp_path: Path) -> Path:
    """Write a minimal valid TEI file and return its path."""
    p = tmp_path / "valid.xml"
    p.write_text(VALID_TEI, encoding="utf-8")
    return p


def test_validator_init(parsed_store):
    """TEIValidator(store) stores the OddStore instance."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    assert v.store is parsed_store


def test_validate_file_returns_shape(parsed_store, valid_tei_path):
    """validate_file returns dict with issues, summary, and limitations."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(valid_tei_path))

    assert isinstance(result, dict)
    assert "issues" in result
    assert "summary" in result
    assert "limitations" in result

    assert isinstance(result["issues"], list)

    summary = result["summary"]
    assert "total" in summary
    assert "by_severity" in summary
    assert "by_rule" in summary


def test_limitations_always_present(parsed_store, valid_tei_path):
    """Limitations field lists the five areas not checked."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(valid_tei_path))

    lim = result["limitations"]
    assert isinstance(lim, dict)
    assert "not_checked" in lim
    assert "note" in lim

    not_checked = lim["not_checked"]
    assert isinstance(not_checked, list)
    assert len(not_checked) == 5

    # Each area should be mentioned
    joined = " ".join(not_checked).lower()
    assert "schematron" in joined
    assert "datatype" in joined
    assert "ordering" in joined
    assert "processing instruction" in joined
    assert "non-tei namespace" in joined


def test_summary_counts_zero_for_valid(parsed_store, valid_tei_path):
    """For a valid document, summary.total == 0 and by_severity all zeros."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(valid_tei_path))

    summary = result["summary"]
    assert summary["total"] == 0
    assert summary["by_severity"]["error"] == 0
    assert summary["by_severity"]["warning"] == 0
    assert summary["by_severity"]["info"] == 0


def test_strip_ns():
    """_strip_ns handles namespaced and bare tags."""
    from tei_mcp.validator import _strip_ns

    assert _strip_ns("{http://www.tei-c.org/ns/1.0}persName") == "persName"
    assert _strip_ns("persName") == "persName"


def test_strip_ns_attr():
    """_strip_ns_attr maps xml: namespace and passes through bare attrs."""
    from tei_mcp.validator import _strip_ns_attr

    assert _strip_ns_attr("{http://www.w3.org/XML/1998/namespace}id") == "xml:id"
    assert _strip_ns_attr("type") == "type"


def test_validate_file_parses_with_line_numbers(parsed_store, valid_tei_path):
    """lxml parsing preserves sourceline on elements (not None)."""
    from lxml import etree

    tree = etree.parse(str(valid_tei_path))
    root = tree.getroot()
    for elem in root.iter():
        if isinstance(elem.tag, str):
            assert elem.sourceline is not None, f"sourceline is None for {elem.tag}"
