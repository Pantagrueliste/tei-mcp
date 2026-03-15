"""ODD customisation: parse an ODD file and produce a constrained OddStore."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from dataclasses import replace

from tei_mcp.models import AttDef, ElementDef
from tei_mcp.parser import NS, _TEI_NS, _parse_att_def
from tei_mcp.store import OddStore

# Tag constants using the TEI namespace
_MODULE_REF = f"{{{_TEI_NS}}}moduleRef"
_SCHEMA_SPEC = f"{{{_TEI_NS}}}schemaSpec"
_ELEMENT_SPEC_TAG = f"{{{_TEI_NS}}}elementSpec"
_ATT_DEF = f"{{{_TEI_NS}}}attDef"


def apply_customisation(base_store: OddStore, odd_path: str) -> OddStore:
    """Parse an ODD customisation file and return a constrained OddStore.

    The base store is never mutated. A new OddStore is constructed from
    deep copies of the base store's dicts, filtered and modified according
    to the ODD's moduleRef and elementSpec directives.

    Args:
        base_store: The full TEI P5 OddStore to constrain.
        odd_path: Path to the ODD customisation XML file.

    Returns:
        A new OddStore with only the elements allowed by the customisation,
        and with attribute modifications applied.

    Raises:
        ValueError: If the ODD file contains no schemaSpec or no moduleRef elements.
    """
    tree = ET.parse(odd_path)
    root = tree.getroot()

    # Find schemaSpec anywhere in the tree (ODD files are TEI documents)
    schema_spec = None
    for el in root.iter(_SCHEMA_SPEC):
        schema_spec = el
        break

    if schema_spec is None:
        raise ValueError("ODD file contains no schemaSpec element")

    # Deep copy base store dicts so base_store is never mutated
    elements = copy.deepcopy(dict(base_store.elements))
    classes = copy.deepcopy(dict(base_store.classes))
    macros = copy.deepcopy(dict(base_store.macros))
    modules = copy.deepcopy(dict(base_store.modules))

    # Step 1: Compute allowed elements from moduleRef directives
    allowed, has_module_refs = _compute_allowed_elements(schema_spec, base_store)

    if not has_module_refs:
        raise ValueError("ODD file contains no moduleRef elements")

    # Step 2: Filter elements dict to only allowed set
    elements = {k: v for k, v in elements.items() if k in allowed}

    # Step 3: Process elementSpec mode="delete"
    for spec in schema_spec.iter(_ELEMENT_SPEC_TAG):
        mode = spec.get("mode", "")
        ident = spec.get("ident", "")
        if mode == "delete":
            elements.pop(ident, None)

    # Step 4: Process elementSpec mode="change" (attributes only)
    for spec in schema_spec.iter(_ELEMENT_SPEC_TAG):
        mode = spec.get("mode", "")
        ident = spec.get("ident", "")
        if mode == "change" and ident in elements:
            elements[ident] = _apply_element_change(elements[ident], spec)

    return OddStore(elements=elements, classes=classes, macros=macros, modules=modules)


def _compute_allowed_elements(
    schema_spec: ET.Element, base_store: OddStore
) -> tuple[set[str], bool]:
    """Compute the set of allowed element idents from moduleRef directives.

    Returns:
        A tuple of (allowed_idents, has_module_refs).
    """
    allowed: set[str] = set()
    has_module_refs = False

    for mod_ref in schema_spec.iter(_MODULE_REF):
        has_module_refs = True
        module_key = mod_ref.get("key", "")
        if not module_key:
            continue

        # Get all elements in this module from the base store
        module_elements = {e.ident for e in base_store.get_module_elements(module_key)}

        include_attr = mod_ref.get("include", "").split()
        except_attr = mod_ref.get("except", "").split()

        if include_attr:
            # Only include the explicitly listed elements
            allowed |= module_elements & set(include_attr)
        elif except_attr:
            # Include all except the listed elements
            allowed |= module_elements - set(except_attr)
        else:
            # Include all elements from the module
            allowed |= module_elements

    return allowed, has_module_refs


def _apply_element_change(elem: ElementDef, spec: ET.Element) -> ElementDef:
    """Apply attribute modifications from an elementSpec mode='change'.

    Processes attDef elements with mode='delete', 'change', or 'add'.
    """
    attrs = list(elem.attributes)

    for att_def_el in spec.iter(_ATT_DEF):
        att_ident = att_def_el.get("ident", "")
        att_mode = att_def_el.get("mode", "")

        if att_mode == "delete":
            attrs = [a for a in attrs if a.ident != att_ident]
        elif att_mode == "change":
            for i, a in enumerate(attrs):
                if a.ident == att_ident:
                    attrs[i] = _modify_att_def(a, att_def_el)
                    break
        elif att_mode == "add":
            attrs.append(_parse_att_def(att_def_el))

    return replace(elem, attributes=tuple(attrs))


def _modify_att_def(existing: AttDef, el: ET.Element) -> AttDef:
    """Merge modifications from an attDef mode='change' into an existing AttDef.

    Only overrides fields that are present in the customisation element.
    Uses dataclasses.replace() to produce a new frozen AttDef instance.
    """
    kwargs: dict = {}

    # Check for valList -- if present, extract values and closed flag
    vl = el.find("tei:valList", NS)
    if vl is not None:
        values = tuple(vi.get("ident", "") for vi in vl.findall("tei:valItem", NS))
        closed = vl.get("type", "") == "closed"
        kwargs["values"] = values
        kwargs["closed"] = closed

    # Check for datatype/dataRef -- if present, override datatype
    dt_el = el.find("tei:datatype", NS)
    if dt_el is not None:
        dr = dt_el.find("tei:dataRef", NS)
        if dr is not None:
            kwargs["datatype"] = dr.get("key", "") or dr.get("name", "")

    # Check for desc -- if present, override desc
    desc_el = el.find("tei:desc", NS)
    if desc_el is not None and desc_el.text:
        kwargs["desc"] = desc_el.text.strip()

    if not kwargs:
        return existing

    return replace(existing, **kwargs)
