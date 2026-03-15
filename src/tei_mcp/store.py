"""In-memory store for parsed TEI ODD specification entities."""

from __future__ import annotations

import difflib
import re
import xml.etree.ElementTree as ET
from collections import deque
from datetime import date
from typing import TypeVar

from tei_mcp.models import AttDef, ClassDef, ElementDef, MacroDef, ModuleDef


def _build_deprecation_obj(valid_until: str, info: str) -> dict | None:
    """Build deprecation dict or None if not deprecated."""
    if not valid_until:
        return None
    expired = date.fromisoformat(valid_until) < date.today()
    return {
        "expired": expired,
        "valid_until": valid_until,
        "severity": "error" if expired else "warning",
        "info": info,
    }

_ANY = "*"

T = TypeVar("T")


class OddStore:
    """Dict-based index store providing O(1) lookup by ident for all entity types."""

    def __init__(
        self,
        elements: dict[str, ElementDef],
        classes: dict[str, ClassDef],
        macros: dict[str, MacroDef],
        modules: dict[str, ModuleDef],
    ) -> None:
        self.elements = elements
        self.classes = classes
        self.macros = macros
        self.modules = modules

        # Build reverse indexes
        self._class_members: dict[str, list[str]] = {}
        for ident, elem in self.elements.items():
            for cls in elem.classes:
                self._class_members.setdefault(cls, []).append(ident)
        for ident, cls_def in self.classes.items():
            for cls in cls_def.classes:
                self._class_members.setdefault(cls, []).append(ident)

        self._module_elements: dict[str, list[ElementDef]] = {}
        for elem in self.elements.values():
            self._module_elements.setdefault(elem.module, []).append(elem)

    @property
    def element_count(self) -> int:
        """Number of parsed element definitions."""
        return len(self.elements)

    @property
    def class_count(self) -> int:
        """Number of parsed class definitions."""
        return len(self.classes)

    @property
    def macro_count(self) -> int:
        """Number of parsed macro definitions."""
        return len(self.macros)

    @property
    def module_count(self) -> int:
        """Number of parsed module definitions."""
        return len(self.modules)

    def get_element(self, ident: str) -> ElementDef | None:
        """Look up an element definition by ident. Returns None if not found."""
        return self.elements.get(ident)

    def get_class(self, ident: str) -> ClassDef | None:
        """Look up a class definition by ident. Returns None if not found."""
        return self.classes.get(ident)

    def get_macro(self, ident: str) -> MacroDef | None:
        """Look up a macro definition by ident. Returns None if not found."""
        return self.macros.get(ident)

    def get_module(self, ident: str) -> ModuleDef | None:
        """Look up a module definition by ident. Returns None if not found."""
        return self.modules.get(ident)

    # --- Case-insensitive lookup ---

    def _get_ci(self, ident: str, collection: dict[str, T]) -> T | None:
        """Case-insensitive lookup: try exact match first, then lowercase scan."""
        result = collection.get(ident)
        if result is not None:
            return result
        lower = ident.lower()
        for key, value in collection.items():
            if key.lower() == lower:
                return value
        return None

    def get_element_ci(self, ident: str) -> ElementDef | None:
        """Case-insensitive element lookup."""
        return self._get_ci(ident, self.elements)

    def get_class_ci(self, ident: str) -> ClassDef | None:
        """Case-insensitive class lookup."""
        return self._get_ci(ident, self.classes)

    def get_macro_ci(self, ident: str) -> MacroDef | None:
        """Case-insensitive macro lookup."""
        return self._get_ci(ident, self.macros)

    def get_module_ci(self, ident: str) -> ModuleDef | None:
        """Case-insensitive module lookup."""
        return self._get_ci(ident, self.modules)

    # --- Reverse index accessors ---

    def get_class_members(self, ident: str) -> list[str]:
        """Return idents of elements and subclasses that declare membership in the given class."""
        return self._class_members.get(ident, [])

    def get_module_elements(self, module: str) -> list[ElementDef]:
        """Return ElementDef objects for all elements in the given module."""
        return self._module_elements.get(module, [])

    # --- Search ---

    def search(
        self,
        pattern: str,
        entity_type: str | None = None,
        max_results: int = 50,
    ) -> list[dict] | dict:
        """Search entities by regex pattern across ident, gloss, and desc fields.

        Returns list of match dicts, or error dict if regex is invalid.
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}

        # Build candidate list: (type_name, entity) tuples
        candidates: list[tuple[str, object]] = []
        if entity_type is None or entity_type == "element":
            candidates.extend(("element", e) for e in self.elements.values())
        if entity_type is None or entity_type == "class":
            candidates.extend(("class", c) for c in self.classes.values())
        if entity_type is None or entity_type == "macro":
            candidates.extend(("macro", m) for m in self.macros.values())
        if entity_type is None or entity_type == "module":
            candidates.extend(("module", m) for m in self.modules.values())

        results: list[dict] = []
        for type_name, entity in candidates:
            ident = entity.ident  # type: ignore[union-attr]
            gloss = entity.gloss  # type: ignore[union-attr]
            desc = entity.desc  # type: ignore[union-attr]

            match_field = None
            if regex.search(ident):
                match_field = "ident"
            elif regex.search(gloss):
                match_field = "gloss"
            elif regex.search(desc):
                match_field = "desc"

            if match_field is not None:
                results.append({
                    "type": type_name,
                    "ident": ident,
                    "gloss": gloss,
                    "match_field": match_field,
                })
                if len(results) >= max_results:
                    break

        return results

    # --- Suggestions ---

    def suggest_names(
        self,
        query: str,
        entity_type: str,
        max_suggestions: int = 5,
    ) -> list[str]:
        """Suggest similar entity names using difflib fuzzy matching."""
        if len(query) < 2:
            return []

        # Select the appropriate collection
        collections: dict[str, dict] = {
            "element": self.elements,
            "class": self.classes,
            "macro": self.macros,
            "module": self.modules,
        }
        collection = collections.get(entity_type, {})
        if not collection:
            return []

        # Build lowercase -> original mapping
        names = list(collection.keys())
        lower_names = [n.lower() for n in names]
        lower_to_original = dict(zip(lower_names, names))

        matches = difflib.get_close_matches(
            query.lower(), lower_names, n=max_suggestions, cutoff=0.4
        )
        return [lower_to_original[m] for m in matches]

    # --- Attribute resolution ---

    def resolve_attributes(self, name: str) -> dict:
        """Resolve all attributes (local + inherited) for an element or class.

        Returns a dict with 'element' (entity ident) and 'attributes' (flat list).
        Local attributes appear first with source='local', then inherited in BFS order.
        If a local attribute overrides an inherited one, an 'overrides' field is added.
        """
        entity = self.get_element_ci(name) or self.get_class_ci(name)
        if entity is None:
            suggestions = self.suggest_names(name, "element") or self.suggest_names(
                name, "class"
            )
            return {"error": f"'{name}' not found", "suggestions": suggestions}

        # Local attributes by ident for override detection
        local_by_ident: dict[str, AttDef] = {a.ident: a for a in entity.attributes}

        # BFS through att.* class hierarchy to collect inherited attributes
        inherited: list[dict] = []
        seen_idents: set[str] = set(local_by_ident.keys())
        visited_classes: set[str] = set()
        queue: deque[str] = deque()

        for cls_ident in entity.classes:
            cls_def = self.classes.get(cls_ident)
            if cls_def is not None and cls_def.class_type == "atts":
                queue.append(cls_ident)

        while queue:
            cls_ident = queue.popleft()
            if cls_ident in visited_classes:
                continue
            visited_classes.add(cls_ident)

            cls_def = self.classes.get(cls_ident)
            if cls_def is None:
                continue

            for attr in cls_def.attributes:
                if attr.ident not in seen_idents:
                    attr_dict = {
                        "name": attr.ident,
                        "source": cls_ident,
                        "datatype": attr.datatype,
                        "values": list(attr.values),
                        "closed": attr.closed,
                    }
                    depr = _build_deprecation_obj(attr.valid_until, attr.deprecation_info)
                    if depr:
                        attr_dict["deprecation"] = depr
                    inherited.append(attr_dict)
                    seen_idents.add(attr.ident)

            for super_cls in cls_def.classes:
                super_def = self.classes.get(super_cls)
                if super_def is not None and super_def.class_type == "atts":
                    queue.append(super_cls)

        # Build local entries with override detection
        result_attrs: list[dict] = []
        for attr in entity.attributes:
            entry: dict = {
                "name": attr.ident,
                "source": "local",
                "datatype": attr.datatype,
                "values": list(attr.values),
                "closed": attr.closed,
            }
            # Check if this overrides an inherited attribute
            for cls_ident in visited_classes:
                cls_def = self.classes.get(cls_ident)
                if cls_def and any(a.ident == attr.ident for a in cls_def.attributes):
                    entry["overrides"] = cls_ident
                    break
            depr = _build_deprecation_obj(attr.valid_until, attr.deprecation_info)
            if depr:
                entry["deprecation"] = depr
            result_attrs.append(entry)

        result_attrs.extend(inherited)
        return {"element": entity.ident, "attributes": result_attrs}

    # --- Class hierarchy chain ---

    def get_class_chain(self, name: str) -> dict:
        """Return class membership chains for an element or class.

        Each direct class membership produces a separate chain walked to its root.
        Each chain step includes ident, type, and gloss.
        """
        entity = self.get_element_ci(name) or self.get_class_ci(name)
        if entity is None:
            suggestions = self.suggest_names(name, "element") or self.suggest_names(
                name, "class"
            )
            return {"error": f"'{name}' not found", "suggestions": suggestions}

        chains: list[list[dict]] = []
        for cls_ident in entity.classes:
            cls_def = self.classes.get(cls_ident)
            if cls_def is None:
                continue
            chain: list[dict] = [
                {
                    "ident": cls_def.ident,
                    "type": cls_def.class_type,
                    "gloss": cls_def.gloss,
                }
            ]
            visited: set[str] = {cls_ident}
            current = cls_def
            while current.classes:
                next_cls = None
                for super_ident in current.classes:
                    if super_ident in visited:
                        continue
                    super_def = self.classes.get(super_ident)
                    if super_def is not None:
                        chain.append(
                            {
                                "ident": super_def.ident,
                                "type": super_def.class_type,
                                "gloss": super_def.gloss,
                            }
                        )
                        visited.add(super_ident)
                        next_cls = super_def
                if next_cls is None:
                    break
                current = next_cls
            chains.append(chain)

        return {"entity": entity.ident, "chains": chains}

    # --- Content model expansion ---

    def expand_content_model(self, name: str) -> dict:
        """Expand a content model for an element or macro into a structured JSON tree.

        Returns a dict tree with sequence, alternation, classRef, element, text,
        empty, dataRef, and anyElement node types. ClassRef nodes include resolved
        concrete element lists. MacroRef nodes are resolved inline.
        """
        elem = self.get_element_ci(name)
        if elem is not None:
            tree = self._parse_content_tree(elem.content_raw)
            tree["name"] = elem.ident
            return tree

        macro = self.get_macro_ci(name)
        if macro is not None:
            tree = self._parse_content_tree(macro.content_raw)
            tree["name"] = macro.ident
            return tree

        suggestions = self.suggest_names(name, "element") + self.suggest_names(
            name, "macro"
        )
        return {"error": f"'{name}' not found", "suggestions": suggestions}

    def _parse_content_tree(
        self, xml_str: str, visited_macros: set[str] | None = None
    ) -> dict:
        """Parse a content XML string into a structured dict tree."""
        if not xml_str:
            return {"type": "empty"}

        if visited_macros is None:
            visited_macros = set()

        root = ET.fromstring(xml_str)
        children = list(root)

        if len(children) == 0:
            # Check if root itself is <empty/>
            tag = root.tag.split("}")[1] if "}" in root.tag else root.tag
            if tag == "empty":
                return {"type": "empty"}
            return {"type": "empty"}

        if len(children) == 1:
            return self._parse_node(children[0], visited_macros)

        # Multiple children: wrap in implicit sequence
        return {
            "type": "sequence",
            "min": 1,
            "max": 1,
            "children": [self._parse_node(c, visited_macros) for c in children],
        }

    def _parse_node(self, el: ET.Element, visited_macros: set[str]) -> dict:
        """Parse a single XML element node into a content model dict."""
        tag = el.tag.split("}")[1] if "}" in el.tag else el.tag

        min_val = int(el.get("minOccurs", "1"))
        max_raw = el.get("maxOccurs", "1")
        max_val: int | str = "unbounded" if max_raw == "unbounded" else int(max_raw)

        if tag == "sequence":
            return {
                "type": "sequence",
                "min": min_val,
                "max": max_val,
                "children": [self._parse_node(c, visited_macros) for c in el],
            }

        if tag == "alternate":
            return {
                "type": "alternation",
                "min": min_val,
                "max": max_val,
                "children": [self._parse_node(c, visited_macros) for c in el],
            }

        if tag == "elementRef":
            return {
                "type": "element",
                "name": el.get("key", ""),
                "min": min_val,
                "max": max_val,
            }

        if tag == "classRef":
            class_name = el.get("key", "")
            return {
                "type": "classRef",
                "class": class_name,
                "min": min_val,
                "max": max_val,
                "elements": self._resolve_class_to_elements(class_name),
            }

        if tag == "macroRef":
            macro_name = el.get("key", "")
            if macro_name in visited_macros:
                return {"type": "error", "message": f"Circular macro reference: {macro_name}"}
            macro = self.get_macro(macro_name)
            if macro is None:
                return {"type": "error", "message": f"Macro not found: {macro_name}"}
            visited_macros.add(macro_name)
            return self._parse_content_tree(macro.content_raw, visited_macros)

        if tag == "textNode":
            return {"type": "text"}

        if tag == "empty":
            return {"type": "empty"}

        if tag == "dataRef":
            return {
                "type": "dataRef",
                "key": el.get("key", el.get("name", "")),
                "min": min_val,
                "max": max_val,
            }

        if tag == "anyElement":
            return {
                "type": "anyElement",
                "min": min_val,
                "max": max_val,
            }

        return {"type": "unknown", "tag": tag}

    def _resolve_class_to_elements(self, class_name: str) -> list[dict]:
        """Resolve a class name to concrete elements via BFS through subclasses."""
        results: list[dict] = []
        visited: set[str] = set()
        queue: deque[tuple[str, str]] = deque([(class_name, class_name)])

        while queue:
            cls, via = queue.popleft()
            if cls in visited:
                continue
            visited.add(cls)

            for member in self.get_class_members(cls):
                if member in self.elements:
                    results.append({"name": member, "via": via})
                elif member in self.classes:
                    queue.append((member, via))

        return results

    # --- Nesting validation ---

    def check_nesting(
        self, child: str, parent: str, recursive: bool = False
    ) -> dict:
        """Check whether *child* can appear inside *parent*.

        Direct mode (default) checks immediate parent-child validity.
        Recursive mode checks if *child* is reachable anywhere inside *ancestor*
        via BFS with cycle detection and path tracking.
        """
        child_elem = self.get_element_ci(child)
        if child_elem is None:
            return {
                "error": f"Child element '{child}' not found",
                "suggestions": self.suggest_names(child, "element"),
            }
        parent_elem = self.get_element_ci(parent)
        if parent_elem is None:
            return {
                "error": f"Parent element '{parent}' not found",
                "suggestions": self.suggest_names(parent, "element"),
            }

        child_ident = child_elem.ident
        parent_ident = parent_elem.ident

        if recursive:
            return self._check_nesting_recursive(child_ident, parent_ident)
        return self._check_nesting_direct(child_ident, parent_ident)

    def _check_nesting_direct(self, child: str, parent: str) -> dict:
        """Check if *child* is a valid direct child of *parent*."""
        children = self._collect_direct_children(parent)

        if _ANY in children:
            return {
                "valid": True,
                "child": child,
                "parent": parent,
                "reason": f"'{parent}' allows any element (anyElement in content model)",
            }

        if child in children:
            # Try to find which classRef the child came through for a richer reason
            via_class = self._find_class_for_child(parent, child)
            if via_class:
                return {
                    "valid": True,
                    "child": child,
                    "parent": parent,
                    "reason": f"'{child}' is allowed as direct child of '{parent}' via classRef {via_class}",
                }
            return {
                "valid": True,
                "child": child,
                "parent": parent,
                "reason": f"'{child}' is allowed as direct child of '{parent}'",
            }

        return {
            "valid": False,
            "child": child,
            "parent": parent,
            "reason": f"'{child}' is not in '{parent}' content model",
        }

    def _find_class_for_child(self, parent: str, child: str) -> str | None:
        """Walk the content tree to find which classRef contains *child*."""
        elem = self.elements.get(parent)
        if elem is None:
            return None
        tree = self._parse_content_tree(elem.content_raw)
        return self._walk_tree_for_class(tree, child)

    def _walk_tree_for_class(self, node: dict, child: str) -> str | None:
        """Recursively search content tree for a classRef whose elements include *child*."""
        if node.get("type") == "classRef":
            for elem in node.get("elements", []):
                if elem["name"] == child:
                    return node["class"]
            return None
        for c in node.get("children", []):
            result = self._walk_tree_for_class(c, child)
            if result is not None:
                return result
        return None

    def _check_nesting_recursive(self, child: str, ancestor: str) -> dict:
        """BFS to check if *child* is reachable inside *ancestor*."""
        queue: deque[tuple[str, list[str]]] = deque([(ancestor, [ancestor])])
        visited: set[str] = {ancestor}

        while queue:
            current, path = queue.popleft()
            direct_children = self._collect_direct_children(current)

            if _ANY in direct_children or child in direct_children:
                return {
                    "reachable": True,
                    "child": child,
                    "ancestor": ancestor,
                    "path": path + [child],
                    "reason": f"'{child}' reachable inside '{ancestor}' via {' > '.join(path + [child])}",
                }

            for elem_name in direct_children:
                if elem_name == _ANY:
                    continue
                if elem_name not in visited and elem_name in self.elements:
                    visited.add(elem_name)
                    queue.append((elem_name, path + [elem_name]))

        return {
            "reachable": False,
            "child": child,
            "ancestor": ancestor,
            "path": [],
            "reason": f"'{child}' is not reachable inside '{ancestor}'",
        }

    # --- Valid children query ---

    def valid_children(self, name: str) -> dict:
        """Return a flat deduplicated list of allowed child elements with metadata.

        Response shape: {"element": str, "children": [{"name": str, "required": bool}],
        "allows_text": bool, "allows_any_element": bool, "empty": bool}
        """
        elem = self.get_element_ci(name)
        if elem is None:
            return {
                "error": f"'{name}' not found",
                "suggestions": self.suggest_names(name, "element"),
            }

        tree = self._parse_content_tree(elem.content_raw)
        children_dict: dict[str, bool] = {}  # name -> required
        meta = self._collect_children_with_metadata(tree, children_dict, context_min=1)

        children_list = sorted(
            [{"name": n, "required": r} for n, r in children_dict.items()],
            key=lambda c: c["name"],
        )

        return {
            "element": elem.ident,
            "children": children_list,
            "allows_text": meta["has_text"],
            "allows_any_element": meta["has_any"],
            "empty": meta["empty"],
        }

    def _collect_children_with_metadata(
        self, node: dict, result: dict[str, bool], context_min: int = 1
    ) -> dict:
        """Walk content tree collecting child elements with required flags.

        Returns meta dict {"has_text": bool, "has_any": bool, "empty": bool}.
        """
        meta = {"has_text": False, "has_any": False, "empty": False}
        node_type = node.get("type")

        if node_type == "element":
            effective_min = node.get("min", 1) * context_min
            name = node["name"]
            if name in result:
                # If either existing or new says required, keep required
                result[name] = result[name] or (effective_min > 0)
            else:
                result[name] = effective_min > 0

        elif node_type == "classRef":
            effective_min = node.get("min", 1) * context_min
            for elem in node.get("elements", []):
                name = elem["name"]
                required = effective_min > 0
                if name in result:
                    result[name] = result[name] or required
                else:
                    result[name] = required

        elif node_type == "text":
            meta["has_text"] = True

        elif node_type == "anyElement":
            meta["has_any"] = True

        elif node_type == "empty":
            meta["empty"] = True

        elif node_type == "alternation":
            # Children of alternation are never required (any one suffices)
            for child in node.get("children", []):
                child_meta = self._collect_children_with_metadata(
                    child, result, context_min=0
                )
                meta["has_text"] = meta["has_text"] or child_meta["has_text"]
                meta["has_any"] = meta["has_any"] or child_meta["has_any"]
                meta["empty"] = meta["empty"] or child_meta["empty"]

        elif node_type == "sequence":
            seq_min = node.get("min", 1) * context_min
            for child in node.get("children", []):
                child_meta = self._collect_children_with_metadata(
                    child, result, context_min=seq_min
                )
                meta["has_text"] = meta["has_text"] or child_meta["has_text"]
                meta["has_any"] = meta["has_any"] or child_meta["has_any"]
                meta["empty"] = meta["empty"] or child_meta["empty"]

        return meta

    def _collect_direct_children(self, name: str) -> set[str]:
        """Collect the set of element idents that can appear as direct children."""
        elem = self.elements.get(name)
        if elem is None:
            return set()
        tree = self._parse_content_tree(elem.content_raw)
        result: set[str] = set()
        self._collect_elements_from_tree(tree, result)
        return result

    def _collect_elements_from_tree(self, node: dict, result: set[str]) -> None:
        """Walk a content model tree and collect element names into result set."""
        node_type = node.get("type")
        if node_type == "element":
            result.add(node["name"])
        elif node_type == "classRef":
            for elem in node.get("elements", []):
                result.add(elem["name"])
        elif node_type == "anyElement":
            result.add(_ANY)
        elif node_type in ("sequence", "alternation"):
            for child in node.get("children", []):
                self._collect_elements_from_tree(child, result)
