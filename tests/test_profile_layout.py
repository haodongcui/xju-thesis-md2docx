from __future__ import annotations

from thesis_md2docx.layout import DocxPackageParts
from thesis_md2docx.profiles.xju_undergraduate_thesis import XjuUndergraduateThesisProfile
from thesis_md2docx.profiles.xju_undergraduate_thesis.styles import xju_style_catalog, xju_style_roles
from thesis_md2docx.styles import validate_style_catalog


def test_xju_profile_exposes_front_matter_and_layout_specs() -> None:
    profile = XjuUndergraduateThesisProfile()
    front = profile.front_matter_spec()
    layout = profile.document_layout()

    assert front.cover_info_key == "封面信息"
    assert front.declaration_key == "声明"
    assert front.taskbook_key == "任务书"
    assert front.cn_abstract_key == "摘要"
    assert front.en_abstract_key == "ABSTRACT"
    assert front.toc_title == "目  录"

    assert layout.cover.footer_kind == "empty"
    assert layout.cover.section_type == "continuous"
    assert layout.front_matter.page_number_format == "upperRoman"
    assert layout.front_matter.page_number_start == 1
    assert layout.body_start.page_number_format == "decimal"
    assert layout.body_start.page_number_start == 1


def test_xju_profile_exposes_docx_parts_and_style_bundle() -> None:
    profile = XjuUndergraduateThesisProfile()

    assert profile.package_parts() == DocxPackageParts()

    bundle = profile.style_bundle()
    assert "XJU Body" in bundle.styles_xml
    assert "<w:numbering" in bundle.numbering_xml
    assert "<w:settings" in bundle.settings_xml
    assert "新疆大学本科毕业论文（设计）" in bundle.header_xml


def test_xju_style_roles_point_to_declared_word_styles() -> None:
    profile = XjuUndergraduateThesisProfile()
    catalog = profile.style_catalog()
    roles = profile.style_roles()

    assert roles.require("body.normal") == "XjuBody"
    assert roles.require("body.heading.level1") == "XjuHeading1"
    assert roles.require("reference.item") == "XjuReference"
    assert roles.missing_styles(catalog) == ()
    assert xju_style_catalog() == catalog
    assert xju_style_roles() == roles
    assert validate_style_catalog(catalog, roles) == ()
