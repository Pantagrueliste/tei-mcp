"""In-memory store for parsed TEI ODD specification entities."""

from __future__ import annotations

from tei_mcp.models import ClassDef, ElementDef, MacroDef, ModuleDef


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
