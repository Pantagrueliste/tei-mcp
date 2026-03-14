"""Tests for ODD XML parser and OddStore."""

from pathlib import Path

import pytest

from tei_mcp.models import AttDef


def test_parse_odd_returns_oddstore(test_odd_path: Path):
    """parse_odd returns an OddStore instance."""
    from tei_mcp.parser import parse_odd
    from tei_mcp.store import OddStore

    store = parse_odd(test_odd_path)
    assert isinstance(store, OddStore)


def test_parse_odd_entity_counts(test_odd_path: Path):
    """parse_odd produces correct counts: 3 elements, 4 classes, 1 macro, 2 modules."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    assert store.element_count == 3
    assert store.class_count == 4  # model.pLike, att.global, att.naming, att.canonical
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
    assert len(p.attributes) == 1
    assert isinstance(p.attributes[0], AttDef)
    assert p.attributes[0].ident == "part"
    assert p.attributes[0].datatype == "teidata.enumerated"
    assert p.attributes[0].closed is True
    assert "Y" in p.attributes[0].values
    assert "N" in p.attributes[0].values


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
    """ClassDef with type='atts' has class_type='atts' and AttDef attributes."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    cls = store.get_class("att.global")
    assert cls is not None
    assert cls.class_type == "atts"
    assert len(cls.attributes) > 0
    assert all(isinstance(a, AttDef) for a in cls.attributes)
    assert cls.attributes[0].ident == "xml:id"
    assert cls.attributes[0].datatype == "ID"
    assert cls.attributes[1].ident == "n"
    assert cls.attributes[1].datatype == "teidata.text"


def test_parse_att_def_extracts_datatype_key(test_odd_path: Path):
    """_parse_att_def extracts datatype from dataRef key= attribute."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    p = store.get_element("p")
    assert p is not None
    part = p.attributes[0]
    assert part.datatype == "teidata.enumerated"


def test_parse_att_def_extracts_datatype_name(test_odd_path: Path):
    """_parse_att_def extracts datatype from dataRef name= attribute (XSD types)."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    persName = store.get_element("persName")
    assert persName is not None
    # ref has dataRef name="anyURI"
    ref_att = next(a for a in persName.attributes if a.ident == "ref")
    assert ref_att.datatype == "anyURI"


def test_parse_att_def_extracts_vallist_closed(test_odd_path: Path):
    """_parse_att_def extracts valList items and closed=True for type='closed'."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    p = store.get_element("p")
    assert p is not None
    part = p.attributes[0]
    assert part.closed is True
    assert part.values == ("Y", "N", "I", "M", "F")


def test_parse_att_def_no_vallist(test_odd_path: Path):
    """_parse_att_def returns empty values and closed=False when no valList."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    persName = store.get_element("persName")
    assert persName is not None
    type_att = next(a for a in persName.attributes if a.ident == "type")
    assert type_att.values == ()
    assert type_att.closed is False


def test_parse_att_def_semi_vallist(test_odd_path: Path):
    """_parse_att_def extracts values from semi-open valList (closed=False)."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    cls = store.get_class("att.naming")
    assert cls is not None
    role_att = next(a for a in cls.attributes if a.ident == "role")
    assert role_att.values == ("author", "editor")
    assert role_att.closed is False  # type="semi" is not closed


def test_persname_has_att_naming_class(test_odd_path: Path):
    """persName has att.naming in its classes (fixture enrichment)."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    persName = store.get_element("persName")
    assert persName is not None
    assert "att.naming" in persName.classes


def test_att_naming_inherits_from_att_canonical(test_odd_path: Path):
    """att.naming has att.canonical in its classes (transitive inheritance)."""
    from tei_mcp.parser import parse_odd

    store = parse_odd(test_odd_path)
    cls = store.get_class("att.naming")
    assert cls is not None
    assert "att.canonical" in cls.classes


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
