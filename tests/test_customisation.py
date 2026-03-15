"""Tests for ODD customisation logic (apply_customisation)."""

from pathlib import Path

import pytest

from tei_mcp.customisation import apply_customisation


@pytest.fixture
def custom_odd_path():
    return Path(__file__).parent / "fixtures" / "test_custom.odd"


@pytest.fixture
def base_store():
    """Return the base OddStore parsed from test_odd.xml."""
    from tei_mcp.parser import parse_odd

    return parse_odd(Path(__file__).parent / "fixtures" / "test_odd.xml")


def test_module_ref_all(base_store, custom_odd_path):
    """moduleRef key='core' with no include/except keeps all core elements."""
    result = apply_customisation(base_store, str(custom_odd_path))
    # Core elements in base store: p, head, hi, note, gap
    # But note is deleted by elementSpec mode="delete", so expect p, head, hi, gap
    for elem in ("p", "head", "hi", "gap"):
        assert elem in result.elements, f"core element '{elem}' should be in customised store"


def test_module_ref_include(base_store, custom_odd_path):
    """moduleRef key='namesdates' include='persName surname' keeps only those two."""
    result = apply_customisation(base_store, str(custom_odd_path))
    # Only persName and surname from namesdates should be included
    assert "persName" in result.elements
    assert "surname" in result.elements
    # forename and roleName should be excluded (not in include list)
    assert "forename" not in result.elements
    assert "roleName" not in result.elements


def test_module_ref_except(base_store):
    """moduleRef key='core' except='gap' keeps all core elements except gap."""
    # Create a temporary ODD with except directive
    import tempfile

    odd_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text><body>
    <schemaSpec ident="test" start="TEI">
      <moduleRef key="core" except="gap"/>
      <moduleRef key="textstructure"/>
    </schemaSpec>
  </body></text>
</TEI>
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".odd", delete=False) as f:
        f.write(odd_content)
        f.flush()
        result = apply_customisation(base_store, f.name)

    # gap should be excluded
    assert "gap" not in result.elements
    # Other core elements should remain
    for elem in ("p", "head", "hi", "note"):
        assert elem in result.elements, f"core element '{elem}' should be in customised store"


def test_element_spec_delete(base_store, custom_odd_path):
    """elementSpec ident='note' mode='delete' removes note from store."""
    assert "note" in base_store.elements, "note should exist in base store"
    result = apply_customisation(base_store, str(custom_odd_path))
    assert "note" not in result.elements


def test_element_spec_change_vallist(base_store, custom_odd_path):
    """elementSpec mode='change' with attDef mode='change' restricts valList to fewer values."""
    result = apply_customisation(base_store, str(custom_odd_path))
    p = result.elements["p"]
    rend_attr = next((a for a in p.attributes if a.ident == "rend"), None)
    assert rend_attr is not None, "rend attribute should still exist"
    assert rend_attr.values == ("italic", "bold")
    assert rend_attr.closed is True


def test_attdef_delete(base_store, custom_odd_path):
    """elementSpec mode='change' with attDef mode='delete' removes the attribute."""
    # Verify part exists in base store
    base_p = base_store.elements["p"]
    assert any(a.ident == "part" for a in base_p.attributes), "part should exist in base p"

    result = apply_customisation(base_store, str(custom_odd_path))
    p = result.elements["p"]
    assert not any(a.ident == "part" for a in p.attributes), "part should be deleted"


def test_attdef_add(base_store):
    """elementSpec mode='change' with attDef mode='add' adds a new attribute."""
    import tempfile

    odd_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text><body>
    <schemaSpec ident="test" start="TEI">
      <moduleRef key="core"/>
      <moduleRef key="textstructure"/>
      <elementSpec ident="p" mode="change">
        <attList>
          <attDef ident="custom" mode="add">
            <desc xml:lang="en">A custom attribute added by ODD.</desc>
            <datatype><dataRef key="teidata.text"/></datatype>
          </attDef>
        </attList>
      </elementSpec>
    </schemaSpec>
  </body></text>
</TEI>
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".odd", delete=False) as f:
        f.write(odd_content)
        f.flush()
        result = apply_customisation(base_store, f.name)

    p = result.elements["p"]
    custom_attr = next((a for a in p.attributes if a.ident == "custom"), None)
    assert custom_attr is not None, "custom attribute should be added"
    assert custom_attr.desc == "A custom attribute added by ODD."
    assert custom_attr.datatype == "teidata.text"


def test_base_store_unchanged(base_store, custom_odd_path):
    """After apply_customisation, base store still has all original elements and attributes."""
    # Snapshot base store state
    orig_element_count = len(base_store.elements)
    orig_note = base_store.elements.get("note")
    orig_p_attrs = base_store.elements["p"].attributes

    # Apply customisation
    apply_customisation(base_store, str(custom_odd_path))

    # Base store must be unchanged
    assert len(base_store.elements) == orig_element_count
    assert "note" in base_store.elements
    assert base_store.elements["note"] is orig_note
    assert base_store.elements["p"].attributes is orig_p_attrs
    assert any(a.ident == "part" for a in base_store.elements["p"].attributes)


def test_no_module_ref_raises(base_store, tmp_path):
    """ODD file with no moduleRef elements raises a clear error."""
    odd_file = tmp_path / "no_modules.odd"
    odd_file.write_text("""\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text><body>
    <schemaSpec ident="test" start="TEI">
      <elementSpec ident="p" mode="delete"/>
    </schemaSpec>
  </body></text>
</TEI>
""")
    with pytest.raises(ValueError, match="moduleRef"):
        apply_customisation(base_store, str(odd_file))


def test_schema_spec_nested(base_store, custom_odd_path):
    """schemaSpec found even when nested inside body of full TEI document."""
    # The main fixture has schemaSpec nested inside text/body -- this test
    # verifies that the parser finds it (same as the main tests working at all).
    result = apply_customisation(base_store, str(custom_odd_path))
    # If schemaSpec wasn't found, we'd get a ValueError
    assert result is not None
    assert result.element_count > 0
