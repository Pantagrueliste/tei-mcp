"""Frozen dataclass models for TEI ODD specification entities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ElementDef:
    """A TEI element definition parsed from an elementSpec."""

    ident: str
    module: str
    gloss: str
    desc: str
    classes: tuple[str, ...]
    attributes: tuple[str, ...]
    content_raw: str


@dataclass(frozen=True)
class ClassDef:
    """A TEI class definition parsed from a classSpec."""

    ident: str
    module: str
    class_type: str  # "model" or "atts"
    gloss: str
    desc: str
    classes: tuple[str, ...]
    attributes: tuple[str, ...]


@dataclass(frozen=True)
class MacroDef:
    """A TEI macro definition parsed from a macroSpec."""

    ident: str
    module: str
    gloss: str
    desc: str
    content_raw: str


@dataclass(frozen=True)
class ModuleDef:
    """A TEI module definition parsed from a moduleSpec."""

    ident: str
    gloss: str
    desc: str
