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
    assert len(members) == 14  # all elements with att.global


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


# --- Nesting validation tests ---


def test_check_nesting_direct_valid(parsed_store):
    """check_nesting('p', 'div') returns valid=True; reason mentions model.pLike or model.common."""
    result = parsed_store.check_nesting("p", "div")
    assert result["valid"] is True
    assert result["child"] == "p"
    assert result["parent"] == "div"
    assert "reason" in result
    # Reason should mention the class path
    reason = result["reason"].lower()
    assert "model.plike" in reason or "model.common" in reason


def test_check_nesting_direct_invalid(parsed_store):
    """check_nesting('div', 'p') returns valid=False."""
    result = parsed_store.check_nesting("div", "p")
    assert result["valid"] is False
    assert result["child"] == "div"
    assert result["parent"] == "p"
    assert "reason" in result


def test_check_nesting_direct_element_ref(parsed_store):
    """check_nesting('surname', 'persName') returns valid=True (direct elementRef)."""
    result = parsed_store.check_nesting("surname", "persName")
    assert result["valid"] is True
    assert result["child"] == "surname"
    assert result["parent"] == "persName"


def test_check_nesting_recursive_reachable(parsed_store):
    """check_nesting('persName', 'body', recursive=True) returns reachable=True with path."""
    result = parsed_store.check_nesting("persName", "body", recursive=True)
    assert result["reachable"] is True
    assert result["child"] == "persName"
    assert result["ancestor"] == "body"
    assert isinstance(result["path"], list)
    assert result["path"][0] == "body"
    assert result["path"][-1] == "persName"
    assert len(result["path"]) >= 2
    assert "reason" in result


def test_check_nesting_recursive_unreachable(parsed_store):
    """check_nesting('body', 'persName', recursive=True) returns reachable=False."""
    result = parsed_store.check_nesting("body", "persName", recursive=True)
    assert result["reachable"] is False
    assert result["child"] == "body"
    assert result["ancestor"] == "persName"
    assert result["path"] == []


def test_check_nesting_cycle(parsed_store):
    """check_nesting('div', 'div', recursive=True) handles cycle without infinite loop."""
    result = parsed_store.check_nesting("div", "div", recursive=True)
    assert result["reachable"] is True
    assert result["path"] == ["div", "div"]


def test_check_nesting_not_found(parsed_store):
    """check_nesting('nonexistent', 'div') returns error dict with suggestions."""
    result = parsed_store.check_nesting("nonexistent", "div")
    assert "error" in result
    assert "suggestions" in result


def test_check_nesting_case_insensitive(parsed_store):
    """check_nesting('P', 'DIV') works case-insensitively."""
    result = parsed_store.check_nesting("P", "DIV")
    assert result["valid"] is True
    assert result["child"] == "p"
    assert result["parent"] == "div"


# --- Deprecation in resolve_attributes tests ---


def test_resolve_attributes_deprecated(parsed_store):
    """resolve_attributes('attRef') returns attr 'name' with deprecation object."""
    result = parsed_store.resolve_attributes("attRef")
    assert "error" not in result
    attrs = result["attributes"]
    name_attr = next(a for a in attrs if a["name"] == "name")
    assert "deprecation" in name_attr
    depr = name_attr["deprecation"]
    assert depr["expired"] is False  # 2026-11-13 is future
    assert depr["valid_until"] == "2026-11-13"
    assert depr["severity"] == "warning"
    assert "ident" in depr["info"]


def test_resolve_attributes_no_deprecation(parsed_store):
    """resolve_attributes('p') returns attr 'part' WITHOUT a 'deprecation' key."""
    result = parsed_store.resolve_attributes("p")
    assert "error" not in result
    attrs = result["attributes"]
    part_attr = next(a for a in attrs if a["name"] == "part")
    assert "deprecation" not in part_attr


# --- valid_children tests ---


def test_valid_children_basic(parsed_store):
    """valid_children('persName') returns flat list with surname, forename, roleName; allows_text=True."""
    result = parsed_store.valid_children("persName")
    assert "error" not in result
    assert result["element"] == "persName"
    assert result["allows_text"] is True
    assert result["allows_any_element"] is False
    assert result["empty"] is False
    child_names = [c["name"] for c in result["children"]]
    assert "surname" in child_names
    assert "forename" in child_names
    assert "roleName" in child_names
    # Each child has a required flag
    for child in result["children"]:
        assert "name" in child
        assert "required" in child


def test_valid_children_deduplication(parsed_store):
    """valid_children('div') returns each element name exactly once."""
    result = parsed_store.valid_children("div")
    assert "error" not in result
    child_names = [c["name"] for c in result["children"]]
    assert len(child_names) == len(set(child_names))


def test_valid_children_required_flag(parsed_store):
    """valid_children('body') has children from model.common with required=True."""
    result = parsed_store.valid_children("body")
    assert "error" not in result
    # body has <classRef key="model.common" minOccurs=1> in a sequence -- required
    children = result["children"]
    assert len(children) > 0
    # At least some children should be required (from model.common with minOccurs=1)
    required_children = [c for c in children if c["required"]]
    assert len(required_children) > 0


def test_valid_children_alternation_not_required(parsed_store):
    """valid_children('div') has children inside an alternation -- all required=False."""
    result = parsed_store.valid_children("div")
    assert "error" not in result
    children = result["children"]
    # All children in div are inside alternation nodes, so none should be required
    for child in children:
        assert child["required"] is False, f"{child['name']} should not be required (alternation context)"


def test_valid_children_allows_text(parsed_store):
    """valid_children('head') has allows_text=True."""
    result = parsed_store.valid_children("head")
    assert "error" not in result
    assert result["allows_text"] is True


def test_valid_children_empty(parsed_store):
    """valid_children('gap') returns children=[], allows_text=False, empty=True."""
    result = parsed_store.valid_children("gap")
    assert "error" not in result
    assert result["children"] == []
    assert result["allows_text"] is False
    assert result["allows_any_element"] is False
    assert result["empty"] is True


def test_valid_children_any_element(parsed_store):
    """valid_children('egXML') returns allows_any_element=True, children=[]."""
    result = parsed_store.valid_children("egXML")
    assert "error" not in result
    assert result["allows_any_element"] is True
    assert result["children"] == []
    assert result["allows_text"] is True


def test_valid_children_not_found(parsed_store):
    """valid_children('notreal') returns error dict with suggestions."""
    result = parsed_store.valid_children("notreal")
    assert "error" in result
    assert "suggestions" in result


def test_valid_children_sorted(parsed_store):
    """valid_children returns children sorted alphabetically by name."""
    result = parsed_store.valid_children("persName")
    child_names = [c["name"] for c in result["children"]]
    assert child_names == sorted(child_names)


# --- check_nesting_batch tests ---


def test_check_nesting_batch_multiple(parsed_store):
    """Batch with two valid pairs returns results list with 2 entries, both valid=True."""
    pairs = [{"child": "p", "parent": "div"}, {"child": "head", "parent": "div"}]
    result = parsed_store.check_nesting_batch(pairs)
    assert result["count"] == 2
    assert len(result["results"]) == 2
    assert result["results"][0]["valid"] is True
    assert result["results"][1]["valid"] is True


def test_check_nesting_batch_mixed_results(parsed_store):
    """Batch with valid and invalid pairs returns correct valid/invalid per pair."""
    pairs = [{"child": "p", "parent": "div"}, {"child": "div", "parent": "p"}]
    result = parsed_store.check_nesting_batch(pairs)
    assert result["count"] == 2
    assert result["results"][0]["valid"] is True
    assert result["results"][1]["valid"] is False


def test_check_nesting_batch_error_isolation(parsed_store):
    """Batch with typo in one pair: first pair succeeds, second pair has error with suggestions."""
    pairs = [{"child": "p", "parent": "div"}, {"child": "perName", "parent": "div"}]
    result = parsed_store.check_nesting_batch(pairs)
    assert result["count"] == 2
    assert result["results"][0]["valid"] is True
    assert "error" in result["results"][1]
    assert "persName" in result["results"][1]["suggestions"]


def test_check_nesting_batch_recursive(parsed_store):
    """Batch with recursive=True returns results with 'reachable' key."""
    pairs = [{"child": "persName", "parent": "body"}]
    result = parsed_store.check_nesting_batch(pairs, recursive=True)
    assert result["count"] == 1
    assert result["results"][0]["reachable"] is True


def test_check_nesting_batch_empty(parsed_store):
    """Batch with empty pairs list returns count=0 and empty results."""
    result = parsed_store.check_nesting_batch([])
    assert result == {"results": [], "count": 0}


def test_check_nesting_batch_malformed_pair(parsed_store):
    """Pair missing 'child' or 'parent' key returns descriptive error for that pair."""
    pairs = [{"child": "p"}, {"parent": "div"}, "not-a-dict"]
    result = parsed_store.check_nesting_batch(pairs)
    assert result["count"] == 3
    for r in result["results"]:
        assert "error" in r
