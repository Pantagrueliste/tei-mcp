"""Tests for tei_mcp.span_locked.SpanStore."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from tei_mcp.span_locked import SpanStore, TEI_NS


def make_store(tmp_path, text: str, document_id: str = "doc"):
    (tmp_path / f"{document_id}.txt").write_text(text, encoding="utf-8")
    return SpanStore(source_root=tmp_path)


# --- get_source ---

def test_get_source_returns_text(tmp_path):
    store = make_store(tmp_path, "hello world")
    assert store.get_source("doc") == "hello world"


def test_get_source_missing_raises(tmp_path):
    store = SpanStore(source_root=tmp_path)
    with pytest.raises(FileNotFoundError):
        store.get_source("nope")


# --- tag_span ---

def test_tag_span_records(tmp_path):
    store = make_store(tmp_path, "hello world")
    rec = store.tag_span("doc", 0, 5, "TEI/text/body/persName", {"ref": "#x"})
    assert rec["start"] == 0
    assert rec["end"] == 5
    assert rec["element"] == "persName"
    assert rec["attrs"] == {"ref": "#x"}
    assert rec["record_id"].startswith("r")


def test_tag_span_out_of_bounds(tmp_path):
    store = make_store(tmp_path, "hello")
    with pytest.raises(ValueError, match="out of bounds"):
        store.tag_span("doc", 0, 100, "p", {})


def test_tag_span_inverted_range(tmp_path):
    store = make_store(tmp_path, "hello")
    with pytest.raises(ValueError, match="start"):
        store.tag_span("doc", 4, 2, "p", {})


def test_tag_span_empty_element_path(tmp_path):
    store = make_store(tmp_path, "hello")
    with pytest.raises(ValueError, match="element_path"):
        store.tag_span("doc", 0, 5, "", {})


def test_list_tags(tmp_path):
    store = make_store(tmp_path, "abcdef")
    store.tag_span("doc", 0, 3, "persName", {})
    store.tag_span("doc", 3, 6, "placeName", {})
    tags = store.list_tags("doc")
    assert len(tags) == 2
    assert {t["element"] for t in tags} == {"persName", "placeName"}


def test_reset_clears_tags(tmp_path):
    store = make_store(tmp_path, "hello")
    store.tag_span("doc", 0, 5, "persName", {})
    assert len(store.list_tags("doc")) == 1
    store.reset("doc")
    assert len(store.list_tags("doc")) == 0
    # Source preserved
    assert store.get_source("doc") == "hello"


# --- compose ---

def _strip_text(tei_str: str) -> str:
    root = etree.fromstring(tei_str.encode("utf-8"))
    return etree.tostring(root, method="text", encoding="unicode")


def test_compose_no_tags(tmp_path):
    store = make_store(tmp_path, "hello world")
    tei = store.compose("doc")
    # Body wrapper is empty of children; source text becomes body.text
    assert "hello world" in tei
    assert _strip_text(tei) == "hello world"


def test_compose_single_tag(tmp_path):
    store = make_store(tmp_path, "Cicero spoke")
    store.tag_span("doc", 0, 6, "persName", {})
    tei = store.compose("doc")
    assert "<persName" in tei
    assert "Cicero" in tei
    assert _strip_text(tei) == "Cicero spoke"


def test_compose_multiple_disjoint_tags(tmp_path):
    text = "Cicero spoke in Rome on March 15."
    store = make_store(tmp_path, text)
    store.tag_span("doc", 0, 6, "persName", {})
    store.tag_span("doc", 16, 20, "placeName", {})
    store.tag_span("doc", 24, 32, "date", {})
    tei = store.compose("doc")
    assert _strip_text(tei) == text
    # All three tags present
    assert "persName" in tei and "placeName" in tei and "date" in tei


def test_compose_nested_tags(tmp_path):
    text = "Marcus Tullius Cicero of Rome"
    store = make_store(tmp_path, text)
    # Outer persName covers "Marcus Tullius Cicero" (0..21)
    store.tag_span("doc", 0, 21, "persName", {})
    # Inner forename covers "Marcus" (0..6)
    store.tag_span("doc", 0, 6, "forename", {})
    store.tag_span("doc", 25, 29, "placeName", {})
    tei = store.compose("doc")
    assert _strip_text(tei) == text


def test_compose_zero_width_tag(tmp_path):
    text = "before after"
    store = make_store(tmp_path, text)
    store.tag_span("doc", 6, 6, "lb", {})  # zero-width line break marker
    tei = store.compose("doc")
    assert "<lb" in tei
    assert _strip_text(tei) == text


def test_compose_crossing_raises(tmp_path):
    store = make_store(tmp_path, "abcdefghij")
    store.tag_span("doc", 0, 5, "a", {})
    store.tag_span("doc", 3, 8, "b", {})  # crosses a
    with pytest.raises(ValueError, match="Crossing"):
        store.compose("doc")


def test_compose_with_attrs(tmp_path):
    text = "Cicero"
    store = make_store(tmp_path, text)
    store.tag_span("doc", 0, 6, "persName", {"ref": "#cicero", "type": "ancient"})
    tei = store.compose("doc")
    root = etree.fromstring(tei.encode("utf-8"))
    pn = root.find(f"{{{TEI_NS}}}persName")
    assert pn is not None
    assert pn.get("ref") == "#cicero"
    assert pn.get("type") == "ancient"


def test_compose_with_xml_attrs(tmp_path):
    text = "X"
    store = make_store(tmp_path, text)
    store.tag_span("doc", 0, 1, "p", {"xml:id": "p1", "xml:lang": "lat"})
    tei = store.compose("doc")
    XML_NS = "http://www.w3.org/XML/1998/namespace"
    root = etree.fromstring(tei.encode("utf-8"))
    p = root.find(f"{{{TEI_NS}}}p")
    assert p is not None
    assert p.get(f"{{{XML_NS}}}id") == "p1"
    assert p.get(f"{{{XML_NS}}}lang") == "lat"


def test_compose_round_trip_invariant(tmp_path):
    text = "The quick brown fox jumps over the lazy dog. Cicero spoke in Rome."
    store = make_store(tmp_path, text)
    store.tag_span("doc", 4, 9, "hi", {})  # quick
    store.tag_span("doc", 16, 19, "hi", {})  # fox
    store.tag_span("doc", 45, 51, "persName", {})  # Cicero
    store.tag_span("doc", 61, 65, "placeName", {})  # Rome
    tei = store.compose("doc")
    assert _strip_text(tei) == text


def test_compose_unwrapped_mode(tmp_path):
    store = make_store(tmp_path, "abc")
    store.tag_span("doc", 1, 2, "hi", {})
    tei_wrapped = store.compose("doc", wrap_in_body=True)
    tei_raw = store.compose("doc", wrap_in_body=False)
    assert "<body" in tei_wrapped
    assert "<body" not in tei_raw


# --- Concurrency / determinism ---

def test_compose_is_deterministic(tmp_path):
    text = "abcdefghij"
    store = make_store(tmp_path, text)
    store.tag_span("doc", 0, 3, "x", {})
    store.tag_span("doc", 3, 6, "y", {})
    a = store.compose("doc")
    b = store.compose("doc")
    assert a == b


def test_record_ids_are_unique_and_monotone(tmp_path):
    store = make_store(tmp_path, "abcdef")
    r1 = store.tag_span("doc", 0, 1, "a", {})
    r2 = store.tag_span("doc", 1, 2, "b", {})
    r3 = store.tag_span("doc", 2, 3, "c", {})
    ids = [r["record_id"] for r in (r1, r2, r3)]
    assert len(set(ids)) == 3
    assert int(ids[0][1:]) < int(ids[1][1:]) < int(ids[2][1:])
