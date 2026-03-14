"""Tests for frozen dataclass models."""

import dataclasses

import pytest

from tei_mcp.models import AttDef, ClassDef, ElementDef, MacroDef, ModuleDef


class TestAttDef:
    def test_frozen_rejects_mutation(self):
        att = AttDef(
            ident="part",
            desc="specifies whether or not the paragraph is complete.",
            datatype="teidata.enumerated",
            values=("Y", "N", "I", "M", "F"),
            closed=True,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            att.ident = "other"

    def test_stores_all_fields(self):
        att = AttDef(
            ident="ref",
            desc="provides a reference.",
            datatype="teidata.pointer",
            values=(),
            closed=False,
        )
        assert att.ident == "ref"
        assert att.desc == "provides a reference."
        assert att.datatype == "teidata.pointer"
        assert att.values == ()
        assert att.closed is False

    def test_serializes_via_asdict(self):
        att = AttDef(
            ident="type",
            desc="indicates a type.",
            datatype="teidata.text",
            values=(),
            closed=False,
        )
        d = dataclasses.asdict(att)
        assert d == {
            "ident": "type",
            "desc": "indicates a type.",
            "datatype": "teidata.text",
            "values": (),
            "closed": False,
        }

    def test_closed_true_with_values(self):
        att = AttDef(
            ident="part",
            desc="",
            datatype="teidata.enumerated",
            values=("Y", "N"),
            closed=True,
        )
        assert att.closed is True
        assert att.values == ("Y", "N")

    def test_empty_defaults(self):
        att = AttDef(ident="n", desc="", datatype="", values=(), closed=False)
        assert att.datatype == ""
        assert att.values == ()
        assert att.closed is False


class TestElementDef:
    def test_frozen_rejects_mutation(self):
        elem = ElementDef(
            ident="p",
            module="core",
            gloss="paragraph",
            desc="marks paragraphs in prose.",
            classes=("model.pLike",),
            attributes=(AttDef(ident="part", desc="", datatype="teidata.enumerated", values=("Y", "N"), closed=True),),
            content_raw="<content/>",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            elem.ident = "div"

    def test_stores_all_fields(self):
        type_att = AttDef(ident="type", desc="indicates a type.", datatype="teidata.text", values=(), closed=False)
        ref_att = AttDef(ident="ref", desc="provides a reference.", datatype="anyURI", values=(), closed=False)
        elem = ElementDef(
            ident="persName",
            module="namesdates",
            gloss="personal name",
            desc="contains a proper noun referring to a person.",
            classes=("model.nameLike.agent", "att.global"),
            attributes=(type_att, ref_att),
            content_raw="<content><textNode/></content>",
        )
        assert elem.ident == "persName"
        assert elem.module == "namesdates"
        assert elem.gloss == "personal name"
        assert elem.desc == "contains a proper noun referring to a person."
        assert elem.classes == ("model.nameLike.agent", "att.global")
        assert elem.attributes[0].ident == "type"
        assert elem.attributes[1].ident == "ref"
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
            attributes=(
                AttDef(ident="xml:id", desc="", datatype="ID", values=(), closed=False),
                AttDef(ident="n", desc="", datatype="teidata.text", values=(), closed=False),
            ),
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
