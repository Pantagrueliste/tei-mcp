"""Tests for ODD XML parser and OddStore."""

from pathlib import Path

import pytest


def test_parse_odd_returns_oddstore(test_odd_path: Path):
    """parse_odd returns an OddStore instance."""
    from tei_mcp.parser import parse_odd
    from tei_mcp.store import OddStore

    store = parse_odd(test_odd_path)
    assert isinstance(store, OddStore)


def test_parse_odd_entity_counts(test_odd_path: Path):
    """parse_odd produces correct counts: 3 elements, 2 classes, 1 macro, 2 modules."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    assert store.element_count == 3
    assert store.class_count == 2
    assert store.macro_count == 1
    assert store.module_count == 2


def test_element_p_fields(test_odd_path: Path):
    """Parsed ElementDef for 'p' has correct ident, module, gloss, desc, classes, attributes."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    p = store.get_element("p")
    assert p is not None
    assert p.ident == "p"
    assert p.module == "core"
    assert p.gloss == "paragraph"
    assert p.desc == "marks paragraphs in prose."
    assert p.classes == ("model.pLike", "att.global")
    assert p.attributes == ("part",)


def test_element_p_english_selected_over_german(test_odd_path: Path):
    """Parser picks English gloss/desc, not German, for multi-lang element."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    p = store.get_element("p")
    assert p is not None
    # English, not German
    assert p.gloss == "paragraph"
    assert "Absatz" not in p.gloss
    assert p.desc == "marks paragraphs in prose."
    assert "Absaetze" not in p.desc


def test_classdef_model_type(test_odd_path: Path):
    """ClassDef with type='model' has class_type='model'."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    cls = store.get_class("model.pLike")
    assert cls is not None
    assert cls.class_type == "model"


def test_classdef_atts_type(test_odd_path: Path):
    """ClassDef with type='atts' has class_type='atts' and attributes."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    cls = store.get_class("att.global")
    assert cls is not None
    assert cls.class_type == "atts"
    assert len(cls.attributes) > 0
    assert "xml:id" in cls.attributes
    assert "n" in cls.attributes


def test_macrodef_content_raw(test_odd_path: Path):
    """Parsed MacroDef has content_raw containing XML string of content element."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    macro = store.get_macro("macro.paraContent")
    assert macro is not None
    assert macro.content_raw != ""
    assert "<" in macro.content_raw  # It's XML
    assert "alternate" in macro.content_raw or "content" in macro.content_raw


def test_moduledef_fields(test_odd_path: Path):
    """Parsed ModuleDef has ident, gloss, desc."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    mod = store.get_module("core")
    assert mod is not None
    assert mod.ident == "core"
    assert mod.gloss == "core module"
    assert mod.desc == "provides elements available in all TEI documents."


def test_oddstore_get_element_nonexistent(test_odd_path: Path):
    """OddStore.get_element returns None for nonexistent ident."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    assert store.get_element("nonexistent") is None


def test_oddstore_get_class_nonexistent(test_odd_path: Path):
    """OddStore.get_class returns None for nonexistent ident."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    assert store.get_class("nonexistent") is None


def test_oddstore_get_macro_nonexistent(test_odd_path: Path):
    """OddStore.get_macro returns None for nonexistent ident."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    assert store.get_macro("nonexistent") is None


def test_oddstore_get_module_nonexistent(test_odd_path: Path):
    """OddStore.get_module returns None for nonexistent ident."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    assert store.get_module("nonexistent") is None


def test_element_content_raw_nonempty(test_odd_path: Path):
    """ElementDef.content_raw is a non-empty XML string for elements with content."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    p = store.get_element("p")
    assert p is not None
    assert p.content_raw != ""
    assert "<" in p.content_raw
    # Should contain the content element serialized as XML
    assert "macroRef" in p.content_raw or "content" in p.content_raw
