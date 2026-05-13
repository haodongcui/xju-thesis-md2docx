from __future__ import annotations

import zipfile
from pathlib import Path

from .constants import *
from .math.converter import MathConverter
from .media import MediaManager
from .ooxml.render import extract_reference_anchors
from .profiles import DEFAULT_PROFILE_NAME, ThesisProfile, get_profile


def build_thesis_document(
    text: str,
    *,
    thesis_profile: ThesisProfile | None = None,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
    markdown_dir: Path | None = None,
    cover_assets_dir: Path | None = None,
    media_manager: MediaManager | None = None,
) -> tuple[list[str], str, str]:
    active_profile = thesis_profile or get_profile(DEFAULT_PROFILE_NAME)
    return active_profile.build_document(
        text,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
        markdown_dir=markdown_dir,
        cover_assets_dir=cover_assets_dir,
        media_manager=media_manager,
    )


def write_docx(
    markdown_path: Path,
    output_path: Path,
    *,
    cover_assets_dir: Path | None = None,
    use_cover_assets: bool = True,
    enable_formula_conversion: bool = True,
    profile: str | ThesisProfile | None = None,
) -> None:
    active_profile = get_profile(profile)
    text = markdown_path.read_text(encoding="utf-8")
    resolved_cover_assets_dir = active_profile.resolve_cover_assets_dir(
        markdown_path,
        cover_assets_dir,
        use_cover_assets=use_cover_assets,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    math_converter = MathConverter() if enable_formula_conversion else None
    if math_converter is not None:
        math_converter.preload_from_markdown(text)
    reference_anchors = extract_reference_anchors(text)
    media_manager = MediaManager(starting_rid=IMAGE_STARTING_RID)
    elements, sect_pr, doc_title = build_thesis_document(
        text,
        thesis_profile=active_profile,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
        markdown_dir=markdown_path.parent,
        cover_assets_dir=resolved_cover_assets_dir,
        media_manager=media_manager,
    )
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", active_profile.content_types_xml(media_manager.image_extensions()))
        zf.writestr("_rels/.rels", active_profile.rels_xml())
        zf.writestr("docProps/core.xml", active_profile.core_xml(doc_title))
        zf.writestr("docProps/app.xml", active_profile.app_xml())
        zf.writestr("word/document.xml", active_profile.document_xml(elements, sect_pr=sect_pr))
        zf.writestr("word/styles.xml", active_profile.styles_xml())
        zf.writestr("word/numbering.xml", active_profile.numbering_xml())
        zf.writestr("word/settings.xml", active_profile.settings_xml())
        zf.writestr("word/fontTable.xml", active_profile.font_table_xml())
        zf.writestr("word/header1.xml", active_profile.header_xml())
        zf.writestr("word/footer1.xml", active_profile.empty_footer_xml())
        zf.writestr("word/footer2.xml", active_profile.page_footer_xml())
        zf.writestr("word/_rels/document.xml.rels", active_profile.document_rels_xml(media_manager))
        for image in media_manager.images:
            zf.writestr(f"word/{image.part_name}", image.source_path.read_bytes())

    if math_converter is not None:
        math_converter.emit_warning()
