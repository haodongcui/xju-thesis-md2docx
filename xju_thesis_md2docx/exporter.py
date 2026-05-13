from __future__ import annotations

import zipfile
from pathlib import Path

from .builders.document import build_document_elements, native_style_profile
from .builders.elements import (
    build_blank_paragraph,
    build_body_paragraph,
    build_cover_elements,
    build_front_heading,
    build_keyword_paragraph,
    build_statement_body_paragraph,
    build_statement_signature_paragraph,
    build_taskbook_elements,
    resolve_cover_assets_dir,
)
from .constants import *
from .frontmatter import parse_inline_image_value, split_statement_content
from .markdown import (
    extract_abstract_and_keywords,
    parse_cover_info,
    parse_markdown_document,
)
from .math.converter import MathConverter
from .media import MediaManager
from .ooxml.header_footer import empty_footer_xml, header_xml, page_footer_xml
from .ooxml.parts import (
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
from .ooxml.render import (
    add_section_to_paragraph_xml,
    extract_reference_anchors,
    page_break_xml,
    toc_field_paragraph_xml,
)

def build_native_document(
    text: str,
    *,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
    markdown_dir: Path | None = None,
    cover_assets_dir: Path | None = None,
    media_manager: MediaManager | None = None,
) -> tuple[list[str], str, str]:
    markdown_title, front_sections, body_text = parse_markdown_document(text)
    cover_info = parse_cover_info(front_sections.get("封面信息", ""))
    thesis_title = cover_info.get("论文题目") or markdown_title or "新疆大学本科毕业论文"
    profile = native_style_profile()

    # Keep the cover and its blank verso page in an empty-footer section. The
    # second page break carries the section properties, so the declaration starts
    # on physical page 3 while Roman numbering still starts at I.
    cover_sect = native_sect_pr_xml(with_header=True, footer_kind="empty", section_type="continuous")
    front_sect = native_sect_pr_xml(
        with_header=True,
        footer_kind="page",
        section_type="nextPage",
        page_number_format="upperRoman",
        page_number_start=1,
    )
    body_start_sect = native_sect_pr_xml(
        with_header=True,
        footer_kind="page",
        page_number_format="decimal",
        page_number_start=1,
    )
    body_continue_sect = native_sect_pr_xml(with_header=True, footer_kind="page")

    elements: list[str] = []
    elements.extend(
        build_cover_elements(
            thesis_title,
            cover_info,
            cover_assets_dir=cover_assets_dir,
            media_manager=media_manager,
        )
    )
    elements.append(page_break_xml())
    elements.append(add_section_to_paragraph_xml(page_break_xml(), cover_sect))

    declaration = front_sections.get("声明", "").strip()
    if declaration:
        elements.append(build_front_heading("声  明", statement=True))
        statement_paragraphs, author_value, date_value = split_statement_content(declaration)
        for paragraph in statement_paragraphs:
            elements.append(
                build_statement_body_paragraph(
                    paragraph,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
        signature_image = None
        signature_alt = "电子签名"
        inline_signature = parse_inline_image_value(author_value)
        if inline_signature is not None and media_manager is not None and markdown_dir is not None:
            signature_alt, signature_target = inline_signature
            signature_image = media_manager.register_image(markdown_dir / signature_target)
            if signature_image is not None:
                author_value = ""
        signature_blank_count = 10 if signature_image is not None else 14
        for _ in range(signature_blank_count):
            elements.append(build_blank_paragraph(run_size=24))
        elements.append(
            build_statement_signature_paragraph(
                "作者签名：",
                author_value,
                signature_image=signature_image,
                media_manager=media_manager,
                signature_alt=signature_alt or "电子签名",
            )
        )
        elements.append(build_statement_signature_paragraph("签字日期：", date_value, is_date=True))
        elements.append(page_break_xml())

    taskbook = front_sections.get("任务书", "").strip()
    if taskbook:
        elements.extend(build_taskbook_elements(taskbook, cover_info))

    cn_abstract, cn_keywords = extract_abstract_and_keywords(front_sections.get("摘要", ""), "关键词：")
    if cn_abstract or cn_keywords:
        elements.append(build_front_heading("摘  要", page_break_before=bool(taskbook)))
        for paragraph in cn_abstract:
            elements.append(
                build_body_paragraph(
                    paragraph,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
        keyword_paragraph = build_keyword_paragraph(cn_keywords)
        if keyword_paragraph:
            elements.append(build_blank_paragraph())
            elements.append(keyword_paragraph)
        elements.append(page_break_xml())

    en_abstract, en_keywords = extract_abstract_and_keywords(front_sections.get("ABSTRACT", ""), "KEY WORDS:")
    if en_abstract or en_keywords:
        elements.append(build_front_heading("ABSTRACT", english=True))
        for paragraph in en_abstract:
            elements.append(
                build_body_paragraph(
                    paragraph,
                    english=True,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
        keyword_paragraph = build_keyword_paragraph(en_keywords, english=True)
        if keyword_paragraph:
            elements.append(build_blank_paragraph())
            elements.append(keyword_paragraph)
        elements.append(page_break_xml())

    elements.append(build_front_heading("目  录", toc=True))
    elements.append(add_section_to_paragraph_xml(toc_field_paragraph_xml(), front_sect))

    body_elements, body_has_section_breaks = build_document_elements(
        body_text,
        profile=profile,
        treat_first_heading_as_title=False,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
        markdown_dir=markdown_dir,
        media_manager=media_manager,
    )
    elements.extend(body_elements)
    body_sect = body_continue_sect if body_has_section_breaks else body_start_sect
    return elements, body_sect, thesis_title


def write_docx(
    markdown_path: Path,
    output_path: Path,
    *,
    cover_assets_dir: Path | None = None,
    use_cover_assets: bool = True,
    enable_formula_conversion: bool = True,
) -> None:
    text = markdown_path.read_text(encoding="utf-8")
    resolved_cover_assets_dir = resolve_cover_assets_dir(markdown_path, cover_assets_dir, use_cover_assets=use_cover_assets)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    math_converter = MathConverter() if enable_formula_conversion else None
    if math_converter is not None:
        math_converter.preload_from_markdown(text)
    reference_anchors = extract_reference_anchors(text)
    media_manager = MediaManager(starting_rid=IMAGE_STARTING_RID)
    elements, sect_pr, doc_title = build_native_document(
        text,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
        markdown_dir=markdown_path.parent,
        cover_assets_dir=resolved_cover_assets_dir,
        media_manager=media_manager,
    )
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(media_manager.image_extensions()))
        zf.writestr("_rels/.rels", rels_xml())
        zf.writestr("docProps/core.xml", core_xml(doc_title))
        zf.writestr("docProps/app.xml", app_xml())
        zf.writestr("word/document.xml", document_xml(elements, sect_pr=sect_pr))
        zf.writestr("word/styles.xml", styles_xml())
        zf.writestr("word/numbering.xml", numbering_xml())
        zf.writestr("word/settings.xml", settings_xml())
        zf.writestr("word/fontTable.xml", font_table_xml())
        zf.writestr("word/header1.xml", header_xml())
        zf.writestr("word/footer1.xml", empty_footer_xml())
        zf.writestr("word/footer2.xml", page_footer_xml())
        zf.writestr("word/_rels/document.xml.rels", document_rels_xml(media_manager))
        for image in media_manager.images:
            zf.writestr(f"word/{image.part_name}", image.source_path.read_bytes())

    if math_converter is not None:
        math_converter.emit_warning()
