from __future__ import annotations

from pathlib import Path

from ...builders.document import build_document_elements
from .frontmatter import (
    build_blank_paragraph,
    build_body_paragraph,
    build_cover_elements,
    build_front_heading,
    build_keyword_paragraph,
    build_statement_body_paragraph,
    build_statement_signature_paragraph,
    build_taskbook_elements,
)
from ...frontmatter import parse_inline_image_value, split_statement_content
from ...markdown import (
    extract_abstract_and_keywords,
    parse_cover_info,
    parse_markdown_document,
)
from ...math.converter import MathConverter
from ...media import MediaManager
from ...ooxml.render import (
    add_section_to_paragraph_xml,
    page_break_xml,
    toc_field_paragraph_xml,
)
from ..base import ThesisProfile


def build_document(
    text: str,
    *,
    thesis_profile: ThesisProfile,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
    markdown_dir: Path | None = None,
    cover_assets_dir: Path | None = None,
    media_manager: MediaManager | None = None,
) -> tuple[list[str], str, str]:
    markdown_title, front_sections, body_text = parse_markdown_document(text)
    front_spec = thesis_profile.front_matter_spec()
    cover_info = parse_cover_info(front_sections.get(front_spec.cover_info_key, ""))
    thesis_title = cover_info.get("论文题目") or markdown_title or front_spec.default_title
    profile = thesis_profile.body_style_profile()
    layout = thesis_profile.document_layout()

    # Keep the cover and its blank verso page in an empty-footer section. The
    # second page break carries the section properties, so the declaration starts
    # on physical page 3 while Roman numbering still starts at I.
    cover_sect = thesis_profile.section_from_spec(layout.cover)
    front_sect = thesis_profile.section_from_spec(layout.front_matter)
    body_start_sect = thesis_profile.section_from_spec(layout.body_start)
    body_continue_sect = thesis_profile.section_from_spec(layout.body_continue)

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

    declaration = front_sections.get(front_spec.declaration_key or "", "").strip()
    if declaration:
        elements.append(build_front_heading(front_spec.declaration_title, statement=True))
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

    taskbook = front_sections.get(front_spec.taskbook_key or "", "").strip()
    if taskbook:
        elements.extend(build_taskbook_elements(taskbook, cover_info))

    cn_abstract, cn_keywords = extract_abstract_and_keywords(
        front_sections.get(front_spec.cn_abstract_key or "", ""),
        front_spec.cn_keyword_prefix,
    )
    if cn_abstract or cn_keywords:
        elements.append(build_front_heading(front_spec.cn_abstract_title, page_break_before=bool(taskbook)))
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

    en_abstract, en_keywords = extract_abstract_and_keywords(
        front_sections.get(front_spec.en_abstract_key or "", ""),
        front_spec.en_keyword_prefix,
    )
    if en_abstract or en_keywords:
        elements.append(build_front_heading(front_spec.en_abstract_title, english=True))
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

    elements.append(build_front_heading(front_spec.toc_title, toc=True))
    toc_style = thesis_profile.style_roles().require("toc.field")
    elements.append(add_section_to_paragraph_xml(toc_field_paragraph_xml(style=toc_style), front_sect))

    body_elements, body_has_section_breaks = build_document_elements(
        body_text,
        profile=profile,
        rules=thesis_profile.body_parse_rules(),
        treat_first_heading_as_title=False,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
        markdown_dir=markdown_dir,
        media_manager=media_manager,
    )
    elements.extend(body_elements)
    body_sect = body_continue_sect if body_has_section_breaks else body_start_sect
    return elements, body_sect, thesis_title
