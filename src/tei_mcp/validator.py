"""TEI document validator using lxml and OddStore."""

from __future__ import annotations

from lxml import etree

from tei_mcp.store import OddStore, _build_deprecation_obj

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
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
        self,
        path: str | None = None,
        authority_files: list[str] | None = None,
        xml_content: str | None = None,
        authority_contents: list[str] | None = None,
    ) -> dict:
        """Parse a TEI XML document and return validation results.

        Provide either ``path`` (a file path on disk) or ``xml_content``
        (the raw XML string). Exactly one must be given.

        Authority files can likewise be provided as file paths
        (``authority_files``) or as raw XML strings (``authority_contents``).

        Returns a dict with:
        - issues: list of issue dicts (severity, line, element, message, rule)
        - summary: dict with total, by_severity, by_rule counts
        - limitations: dict listing what is NOT checked
        """
        if path and xml_content:
            raise ValueError("Provide either path or xml_content, not both.")
        if not path and not xml_content:
            raise ValueError("Provide either path or xml_content.")

        if xml_content:
            root = etree.fromstring(xml_content.encode("utf-8"))
        else:
            tree = etree.parse(path)
            root = tree.getroot()
        issues: list[dict] = []

        # Collect xml:id values for reference integrity
        id_set = self._collect_ids(root)
        if authority_files:
            for af in authority_files:
                af_tree = etree.parse(af)
                id_set |= self._collect_ids(af_tree.getroot())
        if authority_contents:
            for ac in authority_contents:
                af_root = etree.fromstring(ac.encode("utf-8"))
                id_set |= self._collect_ids(af_root)

        # Walk all elements
        for elem in root.iter(etree.Element):
            if not isinstance(elem.tag, str):
                continue
            tag = _strip_ns(elem.tag)
            if not self.store.get_element(tag):
                continue  # skip non-TEI elements

            self._check_content_model(elem, tag, issues)
            self._check_required_children(elem, tag, issues)
            self._check_attributes(elem, tag, issues)
            self._check_empty(elem, tag, issues)
            self._check_refs(elem, tag, id_set, issues)
            self._check_deprecation(elem, tag, issues)

        summary = self._build_summary(issues)
        return {
            "issues": issues,
            "summary": summary,
            "limitations": LIMITATIONS,
        }

    def _check_content_model(
        self, elem: etree._Element, tag: str, issues: list[dict]
    ) -> None:
        """Check that all child elements are allowed by the parent's content model."""
        vc = self.store.valid_children(tag)
        if "error" in vc:
            return
        if vc["allows_any_element"]:
            return

        allowed = {c["name"] for c in vc["children"]}

        for child in elem:
            if not isinstance(child.tag, str):
                continue
            child_tag = _strip_ns(child.tag)
            if child_tag not in allowed and self.store.get_element(child_tag):
                issues.append(
                    {
                        "severity": "error",
                        "line": child.sourceline,
                        "element": child_tag,
                        "message": f"<{child_tag}> is not allowed as child of <{tag}>",
                        "rule": "content-model",
                    }
                )

    def _check_required_children(
        self, elem: etree._Element, tag: str, issues: list[dict]
    ) -> None:
        """Check that elements with required children have at least one present."""
        vc = self.store.valid_children(tag)
        if "error" in vc:
            return
        if vc["empty"]:
            return

        required = {c["name"] for c in vc["children"] if c["required"]}
        if not required:
            return

        actual = {_strip_ns(c.tag) for c in elem if isinstance(c.tag, str)}
        has_text = elem.text and elem.text.strip()

        # If none of the required children appear and no text content
        if not required.intersection(actual) and not has_text:
            issues.append(
                {
                    "severity": "warning",
                    "line": elem.sourceline,
                    "element": tag,
                    "message": (
                        f"<{tag}> is missing required children: "
                        f"{', '.join(sorted(required))}"
                    ),
                    "rule": "required-children",
                }
            )

    def _check_attributes(
        self, elem: etree._Element, tag: str, issues: list[dict]
    ) -> None:
        """Check that all attributes are valid and closed value lists are respected."""
        resolved = self.store.resolve_attributes(tag)
        if "error" in resolved:
            return

        known_attrs = {a["name"]: a for a in resolved["attributes"]}

        for attr_name in elem.attrib:
            local = _strip_ns_attr(attr_name)
            if local not in known_attrs:
                issues.append(
                    {
                        "severity": "error",
                        "line": elem.sourceline,
                        "element": tag,
                        "message": f"Attribute @{local} is not valid on <{tag}>",
                        "rule": "unknown-attribute",
                    }
                )
            else:
                attr_def = known_attrs[local]
                if attr_def["closed"] and attr_def["values"]:
                    value = elem.get(attr_name)
                    if value not in attr_def["values"]:
                        issues.append(
                            {
                                "severity": "error",
                                "line": elem.sourceline,
                                "element": tag,
                                "message": (
                                    f"@{local}='{value}' not in allowed values: "
                                    f"{attr_def['values']}"
                                ),
                                "rule": "closed-value-list",
                            }
                        )

    def _check_empty(
        self, elem: etree._Element, tag: str, issues: list[dict]
    ) -> None:
        """Check that non-empty content model elements have content."""
        vc = self.store.valid_children(tag)
        if "error" in vc:
            return
        if vc["empty"]:
            return

        if len(elem) == 0 and (not elem.text or not elem.text.strip()):
            issues.append(
                {
                    "severity": "error",
                    "line": elem.sourceline,
                    "element": tag,
                    "message": f"<{tag}> is empty but its content model requires content",
                    "rule": "empty-element",
                }
            )

    def _collect_ids(self, root: etree._Element) -> set[str]:
        """Collect all xml:id values from an element tree."""
        ids: set[str] = set()
        for elem in root.iter():
            if not isinstance(elem.tag, str):
                continue
            xml_id = elem.get(f"{{{XML_NS}}}id")
            if xml_id:
                ids.add(xml_id)
        return ids

    def _check_refs(
        self,
        elem: etree._Element,
        tag: str,
        id_set: set[str],
        issues: list[dict],
    ) -> None:
        """Check ref/target attribute targets against known xml:id values."""
        for attr_name, attr_value in elem.attrib.items():
            local_attr = _strip_ns_attr(attr_name)
            if local_attr not in ("ref", "target"):
                continue
            if not attr_value:
                continue
            for ref_val in attr_value.split():
                if ref_val == "#":
                    issues.append(
                        {
                            "severity": "warning",
                            "line": elem.sourceline,
                            "element": tag,
                            "message": (
                                f"Bare '#' in @{local_attr} -- "
                                "likely a forgotten placeholder"
                            ),
                            "rule": "ref-integrity",
                        }
                    )
                elif ref_val.startswith("#"):
                    target = ref_val[1:]
                    if target not in id_set:
                        issues.append(
                            {
                                "severity": "error",
                                "line": elem.sourceline,
                                "element": tag,
                                "message": (
                                    f"@{local_attr}='{ref_val}' -- "
                                    f"target '{target}' not found in document"
                                ),
                                "rule": "ref-integrity",
                            }
                        )

    def _check_deprecation(
        self, elem: etree._Element, tag: str, issues: list[dict]
    ) -> None:
        """Check for deprecated elements and attributes."""
        elem_def = self.store.get_element(tag)
        if elem_def is None:
            return

        # Check element deprecation
        if elem_def.valid_until:
            dep = _build_deprecation_obj(
                elem_def.valid_until, elem_def.deprecation_info
            )
            if dep is not None:
                issues.append(
                    {
                        "severity": dep["severity"],
                        "line": elem.sourceline,
                        "element": tag,
                        "message": (
                            f"<{tag}> is deprecated "
                            f"(validUntil {dep['valid_until']}). "
                            f"{dep['info']}"
                        ),
                        "rule": "deprecation",
                    }
                )

        # Check attribute deprecation
        resolved = self.store.resolve_attributes(tag)
        if "error" in resolved:
            return
        attr_map = {a["name"]: a for a in resolved["attributes"]}
        for attr_name in elem.attrib:
            local = _strip_ns_attr(attr_name)
            if local in attr_map:
                attr_def = attr_map[local]
                dep_info = attr_def.get("deprecation")
                if dep_info:
                    issues.append(
                        {
                            "severity": dep_info["severity"],
                            "line": elem.sourceline,
                            "element": tag,
                            "message": (
                                f"Attribute @{local} on <{tag}> is deprecated "
                                f"(validUntil {dep_info['valid_until']}). "
                                f"{dep_info['info']}"
                            ),
                            "rule": "deprecation",
                        }
                    )

    def validate_element(self, element: str | dict, parent: str) -> dict:
        """Validate a single element in context of a stated parent.

        Args:
            element: Either an XML snippet string (detected by leading '<')
                     or a dict with keys 'name', 'attributes', 'children'.
            parent: The parent element name for nesting validation.

        Returns a dict with 'issues', 'summary', and 'limitations'.
        All issues have line=None (no document context).
        """
        issues: list[dict] = []

        # --- Parse input ---
        if isinstance(element, str) and element.strip().startswith("<"):
            # XML snippet
            parsed = etree.fromstring(element.encode("utf-8"))
            tag = _strip_ns(parsed.tag)
            attrs = {_strip_ns_attr(k): v for k, v in parsed.attrib.items()}
            lxml_elem = parsed
        elif isinstance(element, dict):
            tag = element["name"]
            attrs = element.get("attributes", {})
            lxml_elem = None
        else:
            return {
                "error": "element must be an XML snippet (string starting with '<') "
                "or a dict with 'name', 'attributes', 'children' keys"
            }

        # --- Nesting check against stated parent ---
        vc = self.store.valid_children(parent)
        if "error" not in vc and not vc["allows_any_element"]:
            allowed = {c["name"] for c in vc["children"]}
            if tag not in allowed and self.store.get_element(tag):
                issues.append(
                    {
                        "severity": "error",
                        "line": None,
                        "element": tag,
                        "message": f"<{tag}> is not allowed as child of <{parent}>",
                        "rule": "content-model",
                    }
                )

        # --- Attribute checks ---
        resolved = self.store.resolve_attributes(tag)
        if "error" not in resolved:
            known_attrs = {a["name"]: a for a in resolved["attributes"]}
            for attr_name, attr_value in attrs.items():
                if attr_name not in known_attrs:
                    issues.append(
                        {
                            "severity": "error",
                            "line": None,
                            "element": tag,
                            "message": f"Attribute @{attr_name} is not valid on <{tag}>",
                            "rule": "unknown-attribute",
                        }
                    )
                else:
                    attr_def = known_attrs[attr_name]
                    if attr_def["closed"] and attr_def["values"]:
                        if attr_value not in attr_def["values"]:
                            issues.append(
                                {
                                    "severity": "error",
                                    "line": None,
                                    "element": tag,
                                    "message": (
                                        f"@{attr_name}='{attr_value}' not in allowed values: "
                                        f"{attr_def['values']}"
                                    ),
                                    "rule": "closed-value-list",
                                }
                            )

        # --- Empty check ---
        elem_def = self.store.get_element(tag)
        if elem_def:
            vc_self = self.store.valid_children(tag)
            if "error" not in vc_self and not vc_self["empty"]:
                if lxml_elem is not None:
                    has_children = len(lxml_elem) > 0
                    has_text = lxml_elem.text and lxml_elem.text.strip()
                else:
                    children = element.get("children", [])
                    has_children = len(children) > 0
                    has_text = False  # structured input has no text info

                if not has_children and not has_text:
                    issues.append(
                        {
                            "severity": "error",
                            "line": None,
                            "element": tag,
                            "message": f"<{tag}> is empty but its content model requires content",
                            "rule": "empty-element",
                        }
                    )

        # --- Deprecation check ---
        if elem_def and elem_def.valid_until:
            dep = _build_deprecation_obj(
                elem_def.valid_until, elem_def.deprecation_info
            )
            if dep is not None:
                issues.append(
                    {
                        "severity": dep["severity"],
                        "line": None,
                        "element": tag,
                        "message": (
                            f"<{tag}> is deprecated "
                            f"(validUntil {dep['valid_until']}). "
                            f"{dep['info']}"
                        ),
                        "rule": "deprecation",
                    }
                )

        # Attribute deprecation
        if "error" not in resolved:
            attr_map = {a["name"]: a for a in resolved["attributes"]}
            for attr_name in attrs:
                if attr_name in attr_map:
                    dep_info = attr_map[attr_name].get("deprecation")
                    if dep_info:
                        issues.append(
                            {
                                "severity": dep_info["severity"],
                                "line": None,
                                "element": tag,
                                "message": (
                                    f"Attribute @{attr_name} on <{tag}> is deprecated "
                                    f"(validUntil {dep_info['valid_until']}). "
                                    f"{dep_info['info']}"
                                ),
                                "rule": "deprecation",
                            }
                        )

        # --- Content model checks on element's own children (XML snippet only) ---
        if lxml_elem is not None:
            vc_self = self.store.valid_children(tag)
            if "error" not in vc_self and not vc_self["allows_any_element"]:
                allowed_children = {c["name"] for c in vc_self["children"]}
                for child in lxml_elem:
                    if not isinstance(child.tag, str):
                        continue
                    child_tag = _strip_ns(child.tag)
                    if child_tag not in allowed_children and self.store.get_element(child_tag):
                        issues.append(
                            {
                                "severity": "error",
                                "line": None,
                                "element": child_tag,
                                "message": f"<{child_tag}> is not allowed as child of <{tag}>",
                                "rule": "content-model",
                            }
                        )

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
