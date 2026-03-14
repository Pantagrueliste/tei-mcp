"""Tests for frozen dataclass models."""

import dataclasses

import pytest

from tei_mcp.models import ClassDef, ElementDef, MacroDef, ModuleDef


class TestElementDef:
    def test_frozen_rejects_mutation(self):
        elem = ElementDef(
            ident="p",
            module="core",
            gloss="paragraph",
            desc="marks paragraphs in prose.",
            classes=("model.pLike",),
            attributes=("part",),
            content_raw="<content/>",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            elem.ident = "div"

    def test_stores_all_fields(self):
        elem = ElementDef(
            ident="persName",
            module="namesdates",
            gloss="personal name",
            desc="contains a proper noun referring to a person.",
            classes=("model.nameLike.agent", "att.global"),
            attributes=("type", "ref"),
            content_raw="<content><textNode/></content>",
        )
        assert elem.ident == "persName"
        assert elem.module == "namesdates"
        assert elem.gloss == "personal name"
        assert elem.desc == "contains a proper noun referring to a person."
        assert elem.classes == ("model.nameLike.agent", "att.global")
        assert elem.attributes == ("type", "ref")
        assert elem.content_raw == "<content><textNode/></content>"


class TestClassDef:
    def test_frozen_rejects_mutation(self):
        cls = ClassDef(
            ident="model.pLike",
            module="core",
            class_type="model",
            gloss="paragraph-like elements",
            desc="groups paragraph-like elements.",
            classes=("model.common",),
            attributes=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            cls.ident = "att.global"

    def test_class_type_model(self):
        cls = ClassDef(
            ident="model.pLike",
            module="core",
            class_type="model",
            gloss="",
            desc="",
            classes=(),
            attributes=(),
        )
        assert cls.class_type == "model"

    def test_class_type_atts(self):
        cls = ClassDef(
            ident="att.global",
            module="tei",
            class_type="atts",
            gloss="",
            desc="",
            classes=(),
            attributes=("xml:id", "n"),
        )
        assert cls.class_type == "atts"


class TestMacroDef:
    def test_frozen_rejects_mutation(self):
        macro = MacroDef(
            ident="macro.paraContent",
            module="core",
            gloss="paragraph content",
            desc="defines the content of paragraphs.",
            content_raw="<content/>",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            macro.ident = "other"


class TestModuleDef:
    def test_frozen_rejects_mutation(self):
        mod = ModuleDef(
            ident="core",
            gloss="core module",
            desc="provides elements available in all TEI documents.",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            mod.ident = "drama"


class TestImport:
    def test_import_tei_mcp(self):
        import tei_mcp

        assert hasattr(tei_mcp, "__version__")
