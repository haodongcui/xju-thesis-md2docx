from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionSpec:
    with_header: bool = False
    footer_kind: str | None = None
    section_type: str | None = None
    page_number_format: str | None = None
    page_number_start: int | None = None


@dataclass(frozen=True)
class DocumentLayout:
    cover: SectionSpec
    front_matter: SectionSpec
    body_start: SectionSpec
    body_continue: SectionSpec


@dataclass(frozen=True)
class DocxPackageParts:
    content_types: str = "[Content_Types].xml"
    package_rels: str = "_rels/.rels"
    core_props: str = "docProps/core.xml"
    app_props: str = "docProps/app.xml"
    document: str = "word/document.xml"
    styles: str = "word/styles.xml"
    numbering: str = "word/numbering.xml"
    settings: str = "word/settings.xml"
    font_table: str = "word/fontTable.xml"
    header: str = "word/header1.xml"
    empty_footer: str = "word/footer1.xml"
    page_footer: str = "word/footer2.xml"
    document_rels: str = "word/_rels/document.xml.rels"


@dataclass(frozen=True)
class FrontMatterSpec:
    cover_info_key: str
    declaration_key: str | None = None
    declaration_title: str = ""
    taskbook_key: str | None = None
    cn_abstract_key: str | None = None
    cn_abstract_title: str = ""
    cn_keyword_prefix: str = ""
    en_abstract_key: str | None = None
    en_abstract_title: str = ""
    en_keyword_prefix: str = ""
    toc_title: str = ""
    default_title: str = "Untitled"


@dataclass(frozen=True)
class StyleBundle:
    styles_xml: str
    numbering_xml: str
    settings_xml: str
    font_table_xml: str
    header_xml: str
    empty_footer_xml: str
    page_footer_xml: str
