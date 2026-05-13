from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..math.converter import MathConverter
from ..media import MediaManager
from ..ooxml.header_footer import empty_footer_xml, header_xml, page_footer_xml
from ..ooxml.parts import (
    app_xml,
    content_types_xml,
    core_xml,
    document_rels_xml,
    document_xml,
    font_table_xml,
    native_sect_pr_xml,
    numbering_xml,
    rels_xml,
    settings_xml,
    styles_xml,
)


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
        return native_sect_pr_xml(
            with_header=with_header,
            footer_kind=footer_kind,
            section_type=section_type,
            page_number_format=page_number_format,
            page_number_start=page_number_start,
        )

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
        return styles_xml()

    def numbering_xml(self) -> str:
        return numbering_xml()

    def settings_xml(self) -> str:
        return settings_xml()

    def font_table_xml(self) -> str:
        return font_table_xml()

    def header_xml(self) -> str:
        return header_xml()

    def empty_footer_xml(self) -> str:
        return empty_footer_xml()

    def page_footer_xml(self) -> str:
        return page_footer_xml()

    def document_rels_xml(self, media_manager: MediaManager | None = None) -> str:
        return document_rels_xml(media_manager)
