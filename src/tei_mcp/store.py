"""In-memory store for parsed TEI ODD specification entities."""

from __future__ import annotations

import difflib
import re
from collections import deque
from typing import TypeVar

from tei_mcp.models import AttDef, ClassDef, ElementDef, MacroDef, ModuleDef

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
                    inherited.append(
                        {
                            "name": attr.ident,
                            "source": cls_ident,
                            "datatype": attr.datatype,
                            "values": list(attr.values),
                            "closed": attr.closed,
                        }
                    )
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
