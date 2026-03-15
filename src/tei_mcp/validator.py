"""TEI document validator using lxml and OddStore."""

from __future__ import annotations

from lxml import etree

from tei_mcp.store import OddStore

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS_PREFIX = "{http://www.w3.org/XML/1998/namespace}"

LIMITATIONS = {
    "not_checked": [
        "Schematron constraints (co-occurrence rules, conditional requirements)",
        "Datatype patterns (teidata.* regex validation)",
        "Element ordering within sequences (only presence is checked, not order)",
        "Processing instructions and comments",
        "Elements from non-TEI namespaces",
    ],
    "note": (
        "This tool checks structural validity against the TEI P5 spec. "
        "For full schema validation, use a RELAX NG or Schematron validator."
    ),
}


def _strip_ns(tag: str) -> str:
    """Strip namespace URI from element tag.

    e.g. '{http://www.tei-c.org/ns/1.0}persName' -> 'persName'
    """
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _strip_ns_attr(attr: str) -> str:
    """Convert lxml attribute name to OddStore format.

    Maps '{http://www.w3.org/XML/1998/namespace}id' -> 'xml:id'.
    Strips other namespace prefixes. Passes bare names through.
    """
    if attr.startswith(XML_NS_PREFIX):
        return "xml:" + attr[len(XML_NS_PREFIX):]
    if attr.startswith("{"):
        return attr.split("}", 1)[1]
    return attr


class TEIValidator:
    """Validates TEI XML documents against an OddStore specification."""

    def __init__(self, store: OddStore) -> None:
        self.store = store

    def validate_file(
        self, path: str, authority_files: list[str] | None = None
    ) -> dict:
        """Parse a TEI XML file with lxml and return validation results.

        Returns a dict with:
        - issues: list of issue dicts (severity, line, element, message, rule)
        - summary: dict with total, by_severity, by_rule counts
        - limitations: dict listing what is NOT checked
        """
        tree = etree.parse(path)
        root = tree.getroot()
        issues: list[dict] = []

        # Walk all elements (skeleton -- no check methods called yet)
        for elem in root.iter(etree.Element):
            if not isinstance(elem.tag, str):
                continue
            tag = _strip_ns(elem.tag)
            if not self.store.get_element(tag):
                continue  # skip non-TEI elements

        summary = self._build_summary(issues)
        return {
            "issues": issues,
            "summary": summary,
            "limitations": LIMITATIONS,
        }

    def _build_summary(self, issues: list[dict]) -> dict:
        """Build summary counts from issue list."""
        by_severity = {"error": 0, "warning": 0, "info": 0}
        by_rule: dict[str, int] = {}
        for issue in issues:
            sev = issue["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1
            rule = issue["rule"]
            by_rule[rule] = by_rule.get(rule, 0) + 1
        return {
            "total": len(issues),
            "by_severity": by_severity,
            "by_rule": by_rule,
        }
