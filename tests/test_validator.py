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


# ---- Task 1: Content model, attribute, and empty element checks ----


def _make_tei(tmp_path: Path, body_content: str, filename: str = "test.xml") -> Path:
    """Helper: write a minimal TEI doc wrapping body_content and return path."""
    xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        f"<text><body>{body_content}</body></text>"
        "</TEI>"
    )
    p = tmp_path / filename
    p.write_text(xml, encoding="utf-8")
    return p


def test_invalid_child_flagged(parsed_store, tmp_path):
    """A TEI doc with <p><gap/></p> should NOT flag gap (gap is phrase-level).
    But <body><head>X</head></body> where head is not a valid child of body
    should flag it -- actually head IS in model.divTop which body allows.
    Use <p><div><p>X</p></div></p> -- div is not a valid child of p."""
    # div is NOT in p's children list (p allows phrase-level: hi, persName, etc.)
    path = _make_tei(tmp_path, "<p><div><p>inner</p></div></p>")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    content_errors = [i for i in result["issues"] if i["rule"] == "content-model"]
    assert len(content_errors) >= 1
    assert any(i["element"] == "div" for i in content_errors)


def test_valid_child_no_error(parsed_store, tmp_path):
    """<p><hi>text</hi></p> produces no content-model errors."""
    path = _make_tei(tmp_path, "<p><hi>text</hi></p>")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    content_errors = [i for i in result["issues"] if i["rule"] == "content-model"]
    assert len(content_errors) == 0


def test_allows_any_element_skips_check(parsed_store, tmp_path):
    """egXML allows anyElement -- children should not be flagged."""
    # egXML allows any element, so <egXML><foobar/></egXML> should not flag foobar
    xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        "<text><body><p><egXML><foobar/></egXML></p></body></text>"
        "</TEI>"
    )
    p = tmp_path / "anyelem.xml"
    p.write_text(xml, encoding="utf-8")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(p))
    content_errors = [i for i in result["issues"] if i["rule"] == "content-model"]
    # No content-model errors from egXML's children
    assert not any(
        i["element"] == "foobar" and "egXML" in i["message"] for i in content_errors
    )


def test_unknown_attribute(parsed_store, tmp_path):
    """<p foobar='x'> produces unknown-attribute error for foobar."""
    path = _make_tei(tmp_path, '<p foobar="x">text</p>')
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    attr_errors = [i for i in result["issues"] if i["rule"] == "unknown-attribute"]
    assert len(attr_errors) >= 1
    assert any("foobar" in i["message"] for i in attr_errors)


def test_known_attribute_no_error(parsed_store, tmp_path):
    """<p part='Y'> produces no attribute errors (part is valid on p)."""
    path = _make_tei(tmp_path, '<p part="Y">text</p>')
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    attr_errors = [
        i
        for i in result["issues"]
        if i["rule"] in ("unknown-attribute", "closed-value-list")
    ]
    assert len(attr_errors) == 0


def test_xml_id_not_flagged(parsed_store, tmp_path):
    """xml:id attribute is NOT flagged as unknown."""
    xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        '<text><body><p xml:id="p1">text</p></body></text>'
        "</TEI>"
    )
    p = tmp_path / "xmlid.xml"
    p.write_text(xml, encoding="utf-8")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(p))
    attr_errors = [i for i in result["issues"] if i["rule"] == "unknown-attribute"]
    assert not any("xml:id" in i["message"] for i in attr_errors)


def test_closed_value_list(parsed_store, tmp_path):
    """p/@part with invalid value 'INVALID' produces closed-value-list error."""
    path = _make_tei(tmp_path, '<p part="INVALID">text</p>')
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    cvl_errors = [i for i in result["issues"] if i["rule"] == "closed-value-list"]
    assert len(cvl_errors) >= 1
    assert any("INVALID" in i["message"] for i in cvl_errors)


def test_closed_value_list_valid(parsed_store, tmp_path):
    """p/@part='Y' (valid value from closed list) produces no error."""
    path = _make_tei(tmp_path, '<p part="Y">text</p>')
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    cvl_errors = [i for i in result["issues"] if i["rule"] == "closed-value-list"]
    assert len(cvl_errors) == 0


def test_empty_element_flagged(parsed_store, tmp_path):
    """<p></p> (empty, no text) produces empty-element error."""
    path = _make_tei(tmp_path, "<p></p>")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    empty_errors = [i for i in result["issues"] if i["rule"] == "empty-element"]
    assert len(empty_errors) >= 1
    assert any(i["element"] == "p" for i in empty_errors)


def test_empty_element_with_text_ok(parsed_store, tmp_path):
    """<p>Hello</p> does NOT produce empty-element error."""
    path = _make_tei(tmp_path, "<p>Hello</p>")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    empty_errors = [i for i in result["issues"] if i["rule"] == "empty-element"]
    # p with text content should not be flagged
    assert not any(i["element"] == "p" for i in empty_errors)


def test_element_marked_empty_no_error(parsed_store, tmp_path):
    """gap has empty:true in valid_children -- empty <gap/> should not produce error."""
    path = _make_tei(tmp_path, "<p><gap/></p>")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    empty_errors = [i for i in result["issues"] if i["rule"] == "empty-element"]
    assert not any(i["element"] == "gap" for i in empty_errors)


def test_required_children_missing(parsed_store, tmp_path):
    """body requires children (p, etc.) -- empty <body/> should flag required-children."""
    xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        "<text><body></body></text>"
        "</TEI>"
    )
    p = tmp_path / "reqchildren.xml"
    p.write_text(xml, encoding="utf-8")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(p))
    req_errors = [i for i in result["issues"] if i["rule"] == "required-children"]
    assert len(req_errors) >= 1
    assert any(i["element"] == "body" for i in req_errors)


# ---- Task 2: Reference integrity and deprecation checks ----


def test_bare_hash_warning(parsed_store, tmp_path):
    """<persName ref='#'>text</persName> produces ref-integrity warning with 'placeholder'."""
    path = _make_tei(tmp_path, '<p><persName ref="#">name</persName></p>')
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    ref_issues = [i for i in result["issues"] if i["rule"] == "ref-integrity"]
    assert len(ref_issues) >= 1
    assert any(
        i["severity"] == "warning" and "placeholder" in i["message"].lower()
        for i in ref_issues
    )


def test_ref_target_not_found(parsed_store, tmp_path):
    """<persName ref='#foo'>text</persName> where no xml:id='foo' produces error."""
    path = _make_tei(tmp_path, '<p><persName ref="#foo">name</persName></p>')
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    ref_issues = [i for i in result["issues"] if i["rule"] == "ref-integrity"]
    assert len(ref_issues) >= 1
    assert any(
        i["severity"] == "error" and "foo" in i["message"] for i in ref_issues
    )


def test_ref_target_found(parsed_store, tmp_path):
    """<persName ref='#foo'>text</persName> where another element has xml:id='foo' -- no error."""
    xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        '<text><body><p xml:id="foo">target</p>'
        '<p><persName ref="#foo">name</persName></p></body></text>'
        "</TEI>"
    )
    p = tmp_path / "reffound.xml"
    p.write_text(xml, encoding="utf-8")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(p))
    ref_issues = [i for i in result["issues"] if i["rule"] == "ref-integrity"]
    assert len(ref_issues) == 0


def test_multiple_refs_in_attr(parsed_store, tmp_path):
    """target='#a #b' where only #a exists flags #b but not #a."""
    xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        '<text><body><p xml:id="a">target</p>'
        '<p><persName ref="#a #b">name</persName></p></body></text>'
        "</TEI>"
    )
    p = tmp_path / "multirefs.xml"
    p.write_text(xml, encoding="utf-8")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(p))
    ref_issues = [i for i in result["issues"] if i["rule"] == "ref-integrity"]
    # Should flag #b but not #a
    assert any("b" in i["message"] for i in ref_issues)
    assert not any(
        i["severity"] == "error" and "'a'" in i["message"] for i in ref_issues
    )


def test_authority_file_ids(parsed_store, tmp_path):
    """validate_file with authority_files includes xml:id values from those files."""
    # Main doc references #person1, which only exists in the authority file
    main_xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        '<text><body><p><persName ref="#person1">name</persName></p></body></text>'
        "</TEI>"
    )
    auth_xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        '<person xml:id="person1"><persName>Someone</persName></person>'
        "</TEI>"
    )
    main_path = tmp_path / "main.xml"
    main_path.write_text(main_xml, encoding="utf-8")
    auth_path = tmp_path / "persons.xml"
    auth_path.write_text(auth_xml, encoding="utf-8")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    # Without authority file: should flag #person1
    result_no_auth = v.validate_file(str(main_path))
    ref_issues_no_auth = [
        i for i in result_no_auth["issues"] if i["rule"] == "ref-integrity"
    ]
    assert any("person1" in i["message"] for i in ref_issues_no_auth)

    # With authority file: should NOT flag #person1
    result_with_auth = v.validate_file(
        str(main_path), authority_files=[str(auth_path)]
    )
    ref_issues_with_auth = [
        i for i in result_with_auth["issues"] if i["rule"] == "ref-integrity"
    ]
    assert not any("person1" in i["message"] for i in ref_issues_with_auth)


def test_deprecation_warning_element(parsed_store, tmp_path):
    """Deprecated element 're' (validUntil=2024-01-15) produces deprecation warning."""
    # re is in model.common, so it's a valid child of body/div/p etc.
    path = _make_tei(tmp_path, "<p><re/></p>")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    dep_issues = [i for i in result["issues"] if i["rule"] == "deprecation"]
    assert len(dep_issues) >= 1
    assert any(i["element"] == "re" for i in dep_issues)


def test_deprecation_warning_attribute(parsed_store, tmp_path):
    """Deprecated attribute 'name' on attRef (validUntil=2026-11-13) produces warning."""
    # attRef is a member of att.ref (which has deprecated 'name' attr) and att.global
    xml = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">'
        "<teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>"
        "<publicationStmt><p>T</p></publicationStmt>"
        "<sourceDesc><p>T</p></sourceDesc></fileDesc></teiHeader>"
        '<text><body><p><attRef name="test"/></p></body></text>'
        "</TEI>"
    )
    p = tmp_path / "deprattr.xml"
    p.write_text(xml, encoding="utf-8")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(p))
    dep_issues = [i for i in result["issues"] if i["rule"] == "deprecation"]
    assert any(
        "name" in i["message"].lower() and i["element"] == "attRef"
        for i in dep_issues
    )


def test_non_deprecated_no_warning(parsed_store, tmp_path):
    """Non-deprecated elements/attributes produce no deprecation issues."""
    path = _make_tei(tmp_path, "<p>Hello</p>")
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_file(str(path))
    dep_issues = [i for i in result["issues"] if i["rule"] == "deprecation"]
    assert len(dep_issues) == 0


# ---- Task 1 (Plan 03): validate_element dual input format ----


def test_validate_element_xml_snippet(parsed_store):
    """validate_element('<hi rend="bold">text</hi>', parent="p") returns no errors (hi valid child of p)."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_element('<hi>text</hi>', parent="p")
    assert isinstance(result, dict)
    assert "issues" in result
    content_errors = [i for i in result["issues"] if i["rule"] == "content-model"]
    assert len(content_errors) == 0


def test_validate_element_structured(parsed_store):
    """validate_element with dict input works same as XML snippet."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_element(
        {"name": "hi", "attributes": {}, "children": []}, parent="p"
    )
    assert isinstance(result, dict)
    assert "issues" in result
    content_errors = [i for i in result["issues"] if i["rule"] == "content-model"]
    assert len(content_errors) == 0


def test_validate_element_invalid_nesting(parsed_store):
    """validate_element('<fileDesc/>', parent='p') returns content-model error."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_element("<fileDesc/>", parent="p")
    content_errors = [i for i in result["issues"] if i["rule"] == "content-model"]
    assert len(content_errors) >= 1
    assert any("fileDesc" in i["message"] for i in content_errors)


def test_validate_element_invalid_attr(parsed_store):
    """validate_element('<p foobar="x">text</p>', parent='body') flags unknown-attribute."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_element('<p foobar="x">text</p>', parent="body")
    attr_errors = [i for i in result["issues"] if i["rule"] == "unknown-attribute"]
    assert len(attr_errors) >= 1
    assert any("foobar" in i["message"] for i in attr_errors)


def test_validate_element_no_line_numbers(parsed_store):
    """All issues from validate_element have line=None."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    # Use a case that produces issues
    result = v.validate_element('<p foobar="x">text</p>', parent="body")
    for issue in result["issues"]:
        assert issue["line"] is None, f"Expected line=None, got {issue['line']} for {issue}"


def test_validate_element_summary_and_limitations(parsed_store):
    """Response has summary and limitations fields."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    result = v.validate_element("<p>text</p>", parent="body")
    assert "summary" in result
    assert "limitations" in result
    assert isinstance(result["summary"], dict)
    assert "total" in result["summary"]


def test_validate_element_auto_detects_xml(parsed_store):
    """String starting with '<' is parsed as XML; dict is treated as structured input."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    # XML string
    r1 = v.validate_element("<p>text</p>", parent="body")
    assert isinstance(r1, dict)
    # Dict input
    r2 = v.validate_element({"name": "p", "attributes": {}, "children": []}, parent="body")
    assert isinstance(r2, dict)


def test_validate_element_deprecation(parsed_store):
    """Deprecated element via validate_element produces deprecation warning."""
    from tei_mcp.validator import TEIValidator

    v = TEIValidator(parsed_store)
    # 're' is deprecated (validUntil=2024-01-15)
    result = v.validate_element("<re/>", parent="body")
    dep_issues = [i for i in result["issues"] if i["rule"] == "deprecation"]
    assert len(dep_issues) >= 1
    assert any(i["element"] == "re" for i in dep_issues)
