"""ODD XML parser that reads p5subset.xml and returns an OddStore."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from tei_mcp.models import ClassDef, ElementDef, MacroDef, ModuleDef
from tei_mcp.store import OddStore

logger = logging.getLogger("tei-mcp")

NS = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "rng": "http://relaxng.org/ns/structure/1.0",
}

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# Full namespace URIs for iter()
_TEI_NS = "http://www.tei-c.org/ns/1.0"
_ELEMENT_SPEC = f"{{{_TEI_NS}}}elementSpec"
_CLASS_SPEC = f"{{{_TEI_NS}}}classSpec"
_MACRO_SPEC = f"{{{_TEI_NS}}}macroSpec"
_MODULE_SPEC = f"{{{_TEI_NS}}}moduleSpec"


def _text(el: ET.Element, xpath: str) -> str:
    """Get text content of first matching English element, falling back to first match.

    Uses the full ``{http://www.w3.org/XML/1998/namespace}lang`` attribute key
    since ElementTree XPath does not resolve the ``xml:`` prefix in predicates.
    """
    # Try English first: iterate candidates and check xml:lang attribute directly
    for candidate in el.findall(xpath, NS):
        if candidate.get(_XML_LANG) == "en":
            if candidate.text:
                return candidate.text.strip()
            return ""
    # Fall back to first match regardless of language
    found = el.find(xpath, NS)
    if found is not None and found.text:
        return found.text.strip()
    return ""


def _get_content_raw(el: ET.Element) -> str:
    """Get raw XML string of the <content> element, or empty string if absent."""
    content = el.find("tei:content", NS)
    if content is not None:
        return ET.tostring(content, encoding="unicode")
    return ""


def _parse_element_spec(el: ET.Element) -> ElementDef:
    """Parse an <elementSpec> element into an ElementDef."""
    ident = el.get("ident", "")
    module = el.get("module", "")
    gloss = _text(el, "tei:gloss")
    desc = _text(el, "tei:desc")
    classes = tuple(
        m.get("key", "") for m in el.findall("tei:classes/tei:memberOf", NS)
    )
    attributes = tuple(
        a.get("ident", "") for a in el.findall("tei:attList//tei:attDef", NS)
    )
    content_raw = _get_content_raw(el)
    return ElementDef(
        ident=ident,
        module=module,
        gloss=gloss,
        desc=desc,
        classes=classes,
        attributes=attributes,
        content_raw=content_raw,
    )


def _parse_class_spec(el: ET.Element) -> ClassDef:
    """Parse a <classSpec> element into a ClassDef."""
    ident = el.get("ident", "")
    module = el.get("module", "")
    class_type = el.get("type", "model")
    gloss = _text(el, "tei:gloss")
    desc = _text(el, "tei:desc")
    classes = tuple(
        m.get("key", "") for m in el.findall("tei:classes/tei:memberOf", NS)
    )
    attributes = tuple(
        a.get("ident", "") for a in el.findall("tei:attList//tei:attDef", NS)
    )
    return ClassDef(
        ident=ident,
        module=module,
        class_type=class_type,
        gloss=gloss,
        desc=desc,
        classes=classes,
        attributes=attributes,
    )


def _parse_macro_spec(el: ET.Element) -> MacroDef:
    """Parse a <macroSpec> element into a MacroDef."""
    ident = el.get("ident", "")
    module = el.get("module", "")
    gloss = _text(el, "tei:gloss")
    desc = _text(el, "tei:desc")
    content_raw = _get_content_raw(el)
    return MacroDef(
        ident=ident,
        module=module,
        gloss=gloss,
        desc=desc,
        content_raw=content_raw,
    )


def _parse_module_spec(el: ET.Element) -> ModuleDef:
    """Parse a <moduleSpec> element into a ModuleDef."""
    ident = el.get("ident", "")
    gloss = _text(el, "tei:gloss")
    desc = _text(el, "tei:desc")
    return ModuleDef(ident=ident, gloss=gloss, desc=desc)


def parse_odd(path: Path) -> OddStore:
    """Parse a TEI ODD XML file and return an OddStore with all entities indexed.

    Args:
        path: Path to p5subset.xml or compatible ODD file.

    Returns:
        OddStore with elements, classes, macros, and modules indexed by ident.
    """
    logger.info("Parsing ODD file: %s", path)
    tree = ET.parse(path)
    root = tree.getroot()

    elements: dict[str, ElementDef] = {}
    classes: dict[str, ClassDef] = {}
    macros: dict[str, MacroDef] = {}
    modules: dict[str, ModuleDef] = {}

    for el in root.iter(_ELEMENT_SPEC):
        elem = _parse_element_spec(el)
        elements[elem.ident] = elem

    for el in root.iter(_CLASS_SPEC):
        cls = _parse_class_spec(el)
        classes[cls.ident] = cls

    for el in root.iter(_MACRO_SPEC):
        macro = _parse_macro_spec(el)
        macros[macro.ident] = macro

    for el in root.iter(_MODULE_SPEC):
        mod = _parse_module_spec(el)
        modules[mod.ident] = mod

    logger.info(
        "Parsed %d elements, %d classes, %d macros, %d modules",
        len(elements),
        len(classes),
        len(macros),
        len(modules),
    )

    return OddStore(
        elements=elements,
        classes=classes,
        macros=macros,
        modules=modules,
    )
