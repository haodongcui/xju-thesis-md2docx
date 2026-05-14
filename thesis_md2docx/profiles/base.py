from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..body_rules import BodyParseRules
from ..layout import DocumentLayout, DocxPackageParts, FrontMatterSpec, SectionSpec, StyleBundle
from ..math.converter import MathConverter
from ..media import MediaManager
from ..ooxml.parts import (
    app_xml,
    content_types_xml,
    core_xml,
    document_rels_xml,
    document_xml,
    rels_xml,
)
from ..styles import StyleCatalog, StyleRoleMap


@dataclass(frozen=True)
class ThesisProfile:
    name: str
    display_name: str
    default_cover_assets_dir: Path | None = None

    def resolve_cover_assets_dir(
        self,
        markdown_path: Path,
        assets_dir: Path | None,
        *,
        use_cover_assets: bool,
    ) -> Path | None:
        if not use_cover_assets:
            return None
        if assets_dir is not None:
            return assets_dir
        if self.default_cover_assets_dir and self.default_cover_assets_dir.exists():
            return self.default_cover_assets_dir
        return None

    def body_style_profile(self) -> dict[str, object]:
        return {}

    def body_parse_rules(self) -> BodyParseRules:
        return BodyParseRules()

    def package_parts(self) -> DocxPackageParts:
        return DocxPackageParts()

    def document_layout(self) -> DocumentLayout:
        raise NotImplementedError(f"{self.name} profile must implement document_layout()")

    def front_matter_spec(self) -> FrontMatterSpec:
        raise NotImplementedError(f"{self.name} profile must implement front_matter_spec()")

    def style_catalog(self) -> StyleCatalog:
        return StyleCatalog()

    def style_roles(self) -> StyleRoleMap:
        return StyleRoleMap()

    def style_bundle(self) -> StyleBundle:
        raise NotImplementedError(f"{self.name} profile must implement style_bundle()")

    def build_document(
        self,
        text: str,
        *,
        math_converter: MathConverter | None = None,
        reference_anchors: dict[str, str] | None = None,
        markdown_dir: Path | None = None,
        cover_assets_dir: Path | None = None,
        media_manager: MediaManager | None = None,
    ) -> tuple[list[str], str, str]:
        raise NotImplementedError(f"{self.name} profile does not implement document building")

    def section_pr_xml(
        self,
        *,
        with_header: bool = False,
        footer_kind: str | None = None,
        section_type: str | None = None,
        page_number_format: str | None = None,
        page_number_start: int | None = None,
    ) -> str:
        return self.section_from_spec(
            SectionSpec(
                with_header=with_header,
                footer_kind=footer_kind,
                section_type=section_type,
                page_number_format=page_number_format,
                page_number_start=page_number_start,
            )
        )

    def section_from_spec(self, spec: SectionSpec) -> str:
        raise NotImplementedError(f"{self.name} profile must implement section_from_spec()")

    def content_types_xml(self, image_extensions: set[str] | None = None) -> str:
        return content_types_xml(image_extensions)

    def rels_xml(self) -> str:
        return rels_xml()

    def core_xml(self, title: str) -> str:
        return core_xml(title)

    def app_xml(self) -> str:
        return app_xml()

    def document_xml(self, elements: list[str], *, sect_pr: str | None = None) -> str:
        return document_xml(elements, sect_pr=sect_pr)

    def styles_xml(self) -> str:
        return self.style_bundle().styles_xml

    def numbering_xml(self) -> str:
        return self.style_bundle().numbering_xml

    def settings_xml(self) -> str:
        return self.style_bundle().settings_xml

    def font_table_xml(self) -> str:
        return self.style_bundle().font_table_xml

    def header_xml(self) -> str:
        return self.style_bundle().header_xml

    def empty_footer_xml(self) -> str:
        return self.style_bundle().empty_footer_xml

    def page_footer_xml(self) -> str:
        return self.style_bundle().page_footer_xml

    def document_rels_xml(self, media_manager: MediaManager | None = None) -> str:
        return document_rels_xml(media_manager)
