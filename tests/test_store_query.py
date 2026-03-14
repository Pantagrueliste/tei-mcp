"""Tests for OddStore query methods: case-insensitive lookup, reverse indexes, search, suggestions, resolve_attributes, get_class_chain."""

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
    assert "p" in members
    assert "persName" in members
    assert "div" in members
    assert len(members) == 12  # all elements with att.global


def test_get_class_members_with_subclass(parsed_store):
    """model.common members includes model.pLike (a subclass)."""
    members = parsed_store.get_class_members("model.common")
    assert "model.pLike" in members


def test_get_module_elements(parsed_store):
    """core module returns ElementDef objects for elements with module='core'."""
    elems = parsed_store.get_module_elements("core")
    assert isinstance(elems, list)
    assert len(elems) == 5  # p, head, hi, note, gap have module="core"
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


# --- resolve_attributes tests ---


def test_resolve_attributes_persname_local_first(parsed_store):
    """resolve_attributes('persName') returns local attrs (type, ref) before inherited."""
    result = parsed_store.resolve_attributes("persName")
    assert "error" not in result
    assert result["element"] == "persName"
    attrs = result["attributes"]
    # Local attributes first
    local_attrs = [a for a in attrs if a["source"] == "local"]
    assert len(local_attrs) == 2
    local_names = [a["name"] for a in local_attrs]
    assert "type" in local_names
    assert "ref" in local_names


def test_resolve_attributes_persname_includes_inherited(parsed_store):
    """resolve_attributes('persName') includes inherited attrs from att.global and att.naming."""
    result = parsed_store.resolve_attributes("persName")
    attrs = result["attributes"]
    inherited_names = [a["name"] for a in attrs if a["source"] != "local"]
    # att.global: xml:id, n; att.naming: role
    # att.canonical: ref is skipped because local ref overrides it
    assert "xml:id" in inherited_names
    assert "n" in inherited_names
    assert "role" in inherited_names


def test_resolve_attributes_local_override(parsed_store):
    """persName's local 'ref' overrides att.canonical's 'ref' and has overrides field."""
    result = parsed_store.resolve_attributes("persName")
    attrs = result["attributes"]
    local_ref = next(a for a in attrs if a["name"] == "ref" and a["source"] == "local")
    assert local_ref["overrides"] == "att.canonical"
    # att.canonical's ref should NOT appear as inherited
    inherited_ref = [a for a in attrs if a["name"] == "ref" and a["source"] != "local"]
    assert len(inherited_ref) == 0


def test_resolve_attributes_has_datatype_and_values(parsed_store):
    """Each attribute in resolve_attributes has datatype, values, closed fields."""
    result = parsed_store.resolve_attributes("persName")
    for attr in result["attributes"]:
        assert "name" in attr
        assert "source" in attr
        assert "datatype" in attr
        assert "values" in attr
        assert "closed" in attr


def test_resolve_attributes_for_class(parsed_store):
    """resolve_attributes works for class names (att.global returns its own attrs)."""
    result = parsed_store.resolve_attributes("att.global")
    assert "error" not in result
    assert result["element"] == "att.global"
    names = [a["name"] for a in result["attributes"]]
    assert "xml:id" in names
    assert "n" in names


def test_resolve_attributes_not_found(parsed_store):
    """resolve_attributes for nonexistent name returns error + suggestions."""
    result = parsed_store.resolve_attributes("nonexistent")
    assert "error" in result
    assert "suggestions" in result


def test_resolve_attributes_case_insensitive(parsed_store):
    """resolve_attributes('PERSNAME') works case-insensitively."""
    result = parsed_store.resolve_attributes("PERSNAME")
    assert "error" not in result
    assert result["element"] == "persName"


def test_resolve_attributes_no_attributes(parsed_store):
    """resolve_attributes for element with no local or inherited attrs returns empty list."""
    # model.pLike has no attributes and its superclass model.common is a model class (not atts)
    result = parsed_store.resolve_attributes("model.pLike")
    assert "error" not in result
    assert result["attributes"] == []


def test_resolve_attributes_bfs_ordering(parsed_store):
    """Inherited attrs appear in BFS order -- att.global before att.naming's superclass attrs."""
    result = parsed_store.resolve_attributes("persName")
    attrs = result["attributes"]
    inherited = [a for a in attrs if a["source"] != "local"]
    # att.global attrs (xml:id, n) should appear before att.naming's attrs (role)
    # because both att.global and att.naming are direct memberships, processed in order
    inherited_names = [a["name"] for a in inherited]
    xmlid_idx = inherited_names.index("xml:id")
    role_idx = inherited_names.index("role")
    assert xmlid_idx < role_idx


# --- get_class_chain tests ---


def test_get_class_chain_persname(parsed_store):
    """get_class_chain('persName') returns separate chains for each direct class membership."""
    result = parsed_store.get_class_chain("persName")
    assert "error" not in result
    assert result["entity"] == "persName"
    chains = result["chains"]
    # persName has 3 direct classes: model.nameLike.agent, att.global, att.naming
    chain_starts = [c[0]["ident"] for c in chains]
    assert "model.nameLike.agent" in chain_starts
    assert "att.global" in chain_starts
    assert "att.naming" in chain_starts


def test_get_class_chain_step_fields(parsed_store):
    """Each chain step has ident, type, and gloss fields."""
    result = parsed_store.get_class_chain("persName")
    for chain in result["chains"]:
        for step in chain:
            assert "ident" in step
            assert "type" in step
            assert "gloss" in step


def test_get_class_chain_att_naming(parsed_store):
    """get_class_chain('att.naming') returns chain through att.canonical."""
    result = parsed_store.get_class_chain("att.naming")
    assert "error" not in result
    chains = result["chains"]
    assert len(chains) >= 1
    # att.naming -> att.canonical
    att_canonical_chain = next(c for c in chains if c[0]["ident"] == "att.canonical")
    assert att_canonical_chain[0]["type"] == "atts"


def test_get_class_chain_not_found(parsed_store):
    """get_class_chain for nonexistent name returns error + suggestions."""
    result = parsed_store.get_class_chain("nonexistent")
    assert "error" in result
    assert "suggestions" in result


def test_get_class_chain_cycle_detection(parsed_store):
    """get_class_chain handles potential cycles without infinite loops."""
    # Even though our fixture has no cycles, the method should complete quickly
    # for any entity without hanging. Just verify it returns a result.
    result = parsed_store.get_class_chain("att.global")
    assert "error" not in result
    # att.global has no superclasses, so chains should be empty
    assert result["chains"] == []


# --- Content model expansion tests ---


def test_expand_content_model_classref(parsed_store):
    """expand_content_model('div') returns tree with classRef nodes listing concrete elements."""
    result = parsed_store.expand_content_model("div")
    assert "error" not in result
    assert result["name"] == "div"
    # Root is a sequence
    assert result["type"] == "sequence"

    # Find classRef nodes in the tree (they should have 'class' and 'elements' fields)
    def find_classrefs(node):
        found = []
        if node.get("type") == "classRef":
            found.append(node)
        for child in node.get("children", []):
            found.extend(find_classrefs(child))
        return found

    classrefs = find_classrefs(result)
    assert len(classrefs) > 0
    for cr in classrefs:
        assert "class" in cr
        assert "elements" in cr
        for elem in cr["elements"]:
            assert "name" in elem
            assert "via" in elem


def test_expand_preserves_structure(parsed_store):
    """expand_content_model('div') tree has nested sequence/alternation nodes with min/max."""
    result = parsed_store.expand_content_model("div")
    assert result["type"] == "sequence"
    assert "min" in result
    assert "max" in result
    # Should have children with nested structure (not flat element lists)
    assert "children" in result
    assert len(result["children"]) > 0
    # Check nested alternation exists somewhere
    def find_types(node, types=None):
        if types is None:
            types = set()
        types.add(node.get("type"))
        for child in node.get("children", []):
            find_types(child, types)
        return types

    types = find_types(result)
    assert "sequence" in types
    assert "alternation" in types
    assert "classRef" in types


def test_expand_macro_resolution(parsed_store):
    """expand_content_model('p') resolves macroRef to macro.paraContent inline."""
    result = parsed_store.expand_content_model("p")
    assert "error" not in result
    assert result["name"] == "p"
    # p's content is macroRef macro.paraContent, which should be resolved
    # to the alternation tree from the macro. No macroRef node should remain.
    def has_macro_ref(node):
        if node.get("type") == "macroRef":
            return True
        for child in node.get("children", []):
            if has_macro_ref(child):
                return True
        return False

    assert not has_macro_ref(result), "macroRef should be resolved inline"
    # The resolved content should be an alternation (from macro.paraContent)
    assert result["type"] == "alternation"


def test_expand_macro_direct(parsed_store):
    """expand_content_model('macro.paraContent') works on macro names directly."""
    result = parsed_store.expand_content_model("macro.paraContent")
    assert "error" not in result
    assert result["name"] == "macro.paraContent"
    # macro.paraContent is an alternation with textNode and classRefs
    assert result["type"] == "alternation"


def test_expand_empty_content(parsed_store):
    """expand_content_model('gap') returns {'type': 'empty'} for elements with empty content."""
    result = parsed_store.expand_content_model("gap")
    assert "error" not in result
    assert result["name"] == "gap"
    assert result["type"] == "empty"


def test_expand_text_node(parsed_store):
    """persName's content includes a text node in its alternation children."""
    result = parsed_store.expand_content_model("persName")
    assert result["type"] == "alternation"
    text_nodes = [c for c in result.get("children", []) if c.get("type") == "text"]
    assert len(text_nodes) > 0


def test_expand_not_found(parsed_store):
    """expand_content_model('nonexistent') returns error dict with suggestions."""
    result = parsed_store.expand_content_model("nonexistent")
    assert "error" in result
    assert "suggestions" in result


def test_expand_case_insensitive(parsed_store):
    """expand_content_model('DIV') works case-insensitively."""
    result = parsed_store.expand_content_model("DIV")
    assert "error" not in result
    assert result["name"] == "div"


def test_expand_dataref(parsed_store):
    """expand_content_model for element with dataRef returns dataRef node."""
    result = parsed_store.expand_content_model("gi")
    assert "error" not in result
    assert result["name"] == "gi"
    assert result["type"] == "dataRef"
    assert result["key"] == "teidata.name"
