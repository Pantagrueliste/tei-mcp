"""Tests for OddStore query methods: case-insensitive lookup, reverse indexes, search, suggestions."""

from tei_mcp.models import ElementDef


# --- Case-insensitive lookup tests ---


def test_get_element_ci_exact(parsed_store):
    """Exact match 'p' returns ElementDef with ident 'p'."""
    result = parsed_store.get_element_ci("p")
    assert result is not None
    assert result.ident == "p"


def test_get_element_ci_wrong_case(parsed_store):
    """Lowercase 'persname' returns ElementDef with ident 'persName'."""
    result = parsed_store.get_element_ci("persname")
    assert result is not None
    assert result.ident == "persName"


def test_get_element_ci_not_found(parsed_store):
    """Nonexistent element returns None."""
    result = parsed_store.get_element_ci("nonexistent")
    assert result is None


def test_get_class_ci_exact(parsed_store):
    """Exact match 'att.global' works."""
    result = parsed_store.get_class_ci("att.global")
    assert result is not None
    assert result.ident == "att.global"


def test_get_class_ci_wrong_case(parsed_store):
    """Case-insensitive 'ATT.GLOBAL' works."""
    result = parsed_store.get_class_ci("ATT.GLOBAL")
    assert result is not None
    assert result.ident == "att.global"


def test_get_macro_ci(parsed_store):
    """Exact match 'macro.paraContent' works."""
    result = parsed_store.get_macro_ci("macro.paraContent")
    assert result is not None
    assert result.ident == "macro.paraContent"


def test_get_module_ci(parsed_store):
    """Exact match 'core' works."""
    result = parsed_store.get_module_ci("core")
    assert result is not None
    assert result.ident == "core"


# --- Reverse index tests ---


def test_get_class_members(parsed_store):
    """att.global members includes all elements that declare membership."""
    members = parsed_store.get_class_members("att.global")
    assert isinstance(members, list)
    # p, persName, div all have memberOf key="att.global"
    assert sorted(members) == ["div", "p", "persName"]


def test_get_class_members_with_subclass(parsed_store):
    """model.common members includes model.pLike (a subclass)."""
    members = parsed_store.get_class_members("model.common")
    assert "model.pLike" in members


def test_get_module_elements(parsed_store):
    """core module returns ElementDef objects for elements with module='core'."""
    elems = parsed_store.get_module_elements("core")
    assert isinstance(elems, list)
    assert len(elems) == 1  # only 'p' has module="core"
    assert all(isinstance(e, ElementDef) for e in elems)
    assert elems[0].ident == "p"


def test_get_module_elements_unknown(parsed_store):
    """Unknown module returns empty list."""
    elems = parsed_store.get_module_elements("nonexistent")
    assert elems == []


# --- Search tests ---


def test_search_by_ident(parsed_store):
    """Pattern 'pers' matches persName via ident field."""
    results = parsed_store.search("pers")
    assert any(r["ident"] == "persName" for r in results)


def test_search_by_gloss(parsed_store):
    """Pattern matching a gloss string returns correct entity."""
    results = parsed_store.search("paragraph content")
    assert any(r["ident"] == "macro.paraContent" for r in results)


def test_search_by_desc(parsed_store):
    """Pattern matching a desc string returns correct entity."""
    results = parsed_store.search("subdivision of the front")
    assert any(r["ident"] == "div" for r in results)


def test_search_match_field(parsed_store):
    """Each result has match_field indicating which field matched."""
    results = parsed_store.search("pers")
    pers_result = next(r for r in results if r["ident"] == "persName")
    assert pers_result["match_field"] == "ident"


def test_search_match_field_priority(parsed_store):
    """ident match takes priority over gloss/desc for match_field."""
    # 'p' matches ident 'p' and also appears in gloss/desc of others
    results = parsed_store.search("^p$")
    p_result = next(r for r in results if r["ident"] == "p")
    assert p_result["match_field"] == "ident"


def test_search_entity_type_filter(parsed_store):
    """entity_type='element' excludes classes and macros."""
    results = parsed_store.search(".", entity_type="element")
    assert all(r["type"] == "element" for r in results)


def test_search_max_results(parsed_store):
    """max_results=1 returns at most 1 result."""
    results = parsed_store.search(".", max_results=1)
    assert len(results) <= 1


def test_search_invalid_regex(parsed_store):
    """Invalid regex returns error dict."""
    result = parsed_store.search("[invalid")
    assert isinstance(result, dict)
    assert "error" in result
    assert "Invalid regex" in result["error"]


def test_search_no_duplicates(parsed_store):
    """Entity matching on multiple fields appears only once."""
    # 'paragraph' matches gloss of 'p' ('paragraph') and also desc
    results = parsed_store.search("paragraph")
    idents = [r["ident"] for r in results]
    assert len(idents) == len(set(idents))


# --- Suggestion tests ---


def test_suggest_names_element(parsed_store):
    """Query 'perName' suggests 'persName'."""
    suggestions = parsed_store.suggest_names("perName", entity_type="element")
    assert "persName" in suggestions


def test_suggest_names_short_query(parsed_store):
    """Query 'x' (len < 2) returns empty list."""
    suggestions = parsed_store.suggest_names("x", entity_type="element")
    assert suggestions == []


def test_suggest_names_no_match(parsed_store):
    """Query 'zzzzzzz' returns empty list."""
    suggestions = parsed_store.suggest_names("zzzzzzz", entity_type="element")
    assert suggestions == []
