from __future__ import annotations

import re
from pathlib import Path

from ..builders.elements import build_caption_paragraph, build_reference_paragraph
from ..constants import *
from ..markdown import join_soft_wrapped_lines
from ..math.converter import MathConverter
from ..media import MediaImage, MediaManager
from ..ooxml.parts import native_sect_pr_xml
from ..ooxml.render import (
    figure_row_xml,
    image_paragraph_xml,
    is_caption_paragraph,
    math_paragraph_xml,
    page_break_xml,
    paragraph_with_inline_math_xml,
    paragraph_xml,
    section_break_paragraph_xml,
    table_xml,
)
from ..ooxml.xml import indent_xml, spacing_xml
from ..table_utils import (
    is_table_separator,
    parse_table_split_spec,
    split_markdown_row,
    split_table_rows,
)

def normalize_appendix_heading(text: str, appendix_index: int) -> str:
    cleaned = re.sub(r"^附录\s*[A-Z0-9]+\s*", "", text).strip()
    if cleaned:
        return f"附录{appendix_index} {cleaned}"
    return f"附录{appendix_index}"


def normalize_appendix_references(text: str, appendix_index: int) -> str:
    def replace_heading(match: re.Match[str]) -> str:
        prefix = match.group(1)
        item_no = match.group(2)
        return f"{prefix} 附录{appendix_index}-{item_no}"

    return re.sub(r"([图表])\s*[A-Z]-(\d+)", replace_heading, text)


def strip_heading_prefix(text: str) -> str:
    stripped = re.sub(r"^\d+(?:\.\d+)*\s+", "", text).strip()
    return stripped or text.strip()


def heading_paragraph_xml(
    text: str,
    level: int,
    profile: dict[str, object],
    *,
    numbered: bool = True,
    keep_with_next: bool = True,
) -> str:
    if level == 1:
        style = profile.get("heading1")
    elif level == 2:
        style = profile.get("heading2")
    else:
        style = profile.get("heading3")

    if numbered:
        heading_text = strip_heading_prefix(text) if profile.get("strip_heading_numbers") else text.strip()
        # 范例实测：Heading2 实例覆盖样式，使 before=240(1行), after=120(0.5行), line=360(1.5倍)
        # 基础 styleId="2" 只有 before=100, after=50，不符合规范，此处显式覆盖
        if level == 2:
            ppr_extra = (
                ("<w:keepNext/><w:keepLines/>" if keep_with_next else "")
                + spacing_xml(before=240, after=120, line=360)
                + indent_xml(left=0, first_line=0)
            )
            return paragraph_xml(heading_text, style=str(style) if style else None, align="left", ppr_extra=ppr_extra)
        elif level == 1:
            ppr_extra = spacing_xml(before_lines=80, before=0, line=240) + indent_xml(left=0, first_line=0)
        else:
            ppr_extra = (
                ("<w:keepNext/><w:keepLines/>" if keep_with_next else "")
                + spacing_xml(before=120, line=360)
                + indent_xml(left=0, first_line_chars=200, first_line=560)
            )
            return paragraph_xml(heading_text, style=str(style) if style else None, align="left", ppr_extra=ppr_extra)
        return paragraph_xml(heading_text, style=str(style) if style else None, ppr_extra=ppr_extra)

    ppr_extra = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
    if level == 1:
        ppr_extra += spacing_xml(line=240)
    elif level == 3:
        # 规范：三级标题左起空两字符 (2 × 四号 14pt = 560 twips)
        ppr_extra += (
            ("<w:keepNext/><w:keepLines/>" if keep_with_next else "")
            + spacing_xml(before=120, line=360)
            + indent_xml(left=0, first_line_chars=200, first_line=560)
        )
        return paragraph_xml(text.strip(), style=str(style) if style else None, align="left", ppr_extra=ppr_extra)
    return paragraph_xml(text.strip(), style=str(style) if style else None, ppr_extra=ppr_extra)


def acknowledgement_heading_paragraph_xml(text: str, profile: dict[str, object]) -> str:
    style = profile.get("heading1")
    # The official sample keeps acknowledgement in the level-1/TOC family, but
    # its heading sits at the front-matter vertical position instead of the
    # lower reference-heading position. Override only paragraph spacing here.
    ppr_extra = (
        '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
        '<w:snapToGrid w:val="0"/>'
        + spacing_xml(before_lines=0, before=0, after_lines=200, after=480, line=240)
    )
    return paragraph_xml(text.strip(), style=str(style) if style else None, ppr_extra=ppr_extra)


def native_style_profile() -> dict[str, object]:
    return {
        "title": STYLE_HEADING_1,
        "heading1": STYLE_HEADING_1,
        "heading2": STYLE_HEADING_2,
        "heading3": STYLE_HEADING_3,
        "normal": STYLE_BODY,
        "quote": STYLE_QUOTE,
        "code": STYLE_CODE_BLOCK,
        "code_ppr_extra": '<w:outlineLvl w:val="9"/>',
        "math": STYLE_MATH_BLOCK,
        "table": STYLE_TABLE_TEXT,
        "normal_first_line_chars": 200,
        "normal_first_line": 480,
        "normal_ppr_extra": '<w:widowControl w:val="0"/>' + spacing_xml(line=360),
        "normal_run": {
            "font_ascii": "Times New Roman",
            "font_hansi": "Times New Roman",
            "font_eastasia": "宋体",
            "size": 24,
        },
        "caption": STYLE_CAPTION,
        "skip_reference_notes": True,
        "strip_heading_numbers": True,
    }


def build_document_elements(
    text: str,
    profile: dict[str, object] | None = None,
    *,
    treat_first_heading_as_title: bool = True,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
    markdown_dir: Path | None = None,
    media_manager: MediaManager | None = None,
) -> list[str]:
    lines = text.splitlines()
    elements: list[str] = []
    paragraph_buffer: list[str] = []
    i = 0
    in_code = False
    code_lines: list[str] = []
    in_math = False
    math_lines: list[str] = []
    current_top_heading = ""
    in_appendix = False
    current_chapter_number = ""
    current_appendix_index = 0
    formula_counters: dict[str, int] = {}
    page_break_marker = page_break_xml()
    chapter_section_break_count = 0
    pending_table_split: list[int] | None = None
    last_table_caption_text: str | None = None

    profile = profile or native_style_profile()

    def is_chapter_section_break(element: str) -> bool:
        return "<w:sectPr>" in element and 'w:type w:val="nextPage"' in element

    def append_chapter_page_break() -> None:
        nonlocal chapter_section_break_count
        if elements and elements[-1] != page_break_marker and not is_chapter_section_break(elements[-1]):
            if chapter_section_break_count == 0:
                sect_pr = native_sect_pr_xml(
                    section_type="nextPage",
                    with_header=True,
                    footer_kind="page",
                    page_number_format="decimal",
                    page_number_start=1,
                )
            else:
                sect_pr = native_sect_pr_xml(section_type="nextPage", with_header=True, footer_kind="page")
            elements.append(section_break_paragraph_xml(sect_pr))
            chapter_section_break_count += 1

    def next_formula_number() -> str | None:
        if in_appendix and current_appendix_index > 0:
            scope = f"附录{current_appendix_index}"
        else:
            scope = current_chapter_number
        if not scope:
            return None
        formula_counters[scope] = formula_counters.get(scope, 0) + 1
        return f"（{scope}-{formula_counters[scope]}）"

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer, last_table_caption_text
        if not paragraph_buffer:
            return
        paragraph = join_soft_wrapped_lines(paragraph_buffer).strip()
        paragraph_buffer = []
        if not paragraph:
            return

        if in_appendix and current_appendix_index > 0:
            paragraph = normalize_appendix_references(paragraph, current_appendix_index)

        if current_top_heading == "参考文献":
            if profile.get("skip_reference_notes") and paragraph.startswith("说明："):
                return
            if re.match(r"^\[\d+\]", paragraph):
                elements.append(build_reference_paragraph(paragraph, reference_anchors=reference_anchors))
                return

        if is_caption_paragraph(paragraph):
            # Table captions appear immediately above the table they label, so
            # `keepNext` keeps them on the same page as the table when possible.
            # Figure captions appear after the image, so they do not need it.
            keep_next_caption = paragraph.lstrip().startswith("表")
            if keep_next_caption:
                last_table_caption_text = paragraph
            caption_style = profile.get("caption") or profile.get("normal")
            elements.append(
                build_caption_paragraph(
                    paragraph,
                    style=str(caption_style) if caption_style else None,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                    keep_next=keep_next_caption,
                )
            )
            return

        normal_run = profile.get("normal_run")
        ppr_extra = str(profile.get("normal_ppr_extra", ""))
        if normal_run:
            elements.append(
                paragraph_with_inline_math_xml(
                    paragraph,
                    style=str(profile.get("normal")) if profile.get("normal") else None,
                    ppr_extra=ppr_extra,
                    first_line_chars=int(profile.get("normal_first_line_chars", 0) or 0) or None,
                    first_line=int(profile.get("normal_first_line", 0) or 0) or None,
                    run_kwargs=dict(normal_run),
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
        else:
            elements.append(
                paragraph_with_inline_math_xml(
                    paragraph,
                    style=str(profile.get("normal")) if profile.get("normal") else None,
                    first_line_chars=int(profile.get("normal_first_line_chars", 0) or 0) or None,
                    first_line=int(profile.get("normal_first_line", 0) or 0) or None,
                    ppr_extra=ppr_extra,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )

    def resolve_image(target: str) -> MediaImage | None:
        image_path = markdown_dir / target if markdown_dir else Path(target)
        return media_manager.register_image(image_path) if media_manager else None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if in_code:
            if stripped.startswith("```"):
                code_text = "\n".join(code_lines).rstrip("\n")
                if code_text:
                    elements.append(
                        paragraph_xml(
                            code_text,
                            style=str(profile.get("code")) if profile.get("code") else None,
                            preserve_breaks=True,
                            ppr_extra=str(profile.get("code_ppr_extra", "")),
                        )
                    )
                in_code = False
                code_lines = []
            else:
                code_lines.append(line.rstrip("\n"))
            i += 1
            continue

        if in_math:
            if stripped == "$$":
                math_text = "\n".join(math_lines).strip("\n")
                if math_text:
                    elements.append(
                        math_paragraph_xml(
                            math_text,
                            style=str(profile.get("math")) if profile.get("math") else None,
                            math_converter=math_converter,
                            equation_number=next_formula_number(),
                        )
                    )
                in_math = False
                math_lines = []
            else:
                math_lines.append(line.rstrip("\n"))
            i += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            in_code = True
            code_lines = []
            i += 1
            continue

        if stripped == "$$":
            flush_paragraph()
            in_math = True
            math_lines = []
            i += 1
            continue

        if not stripped:
            flush_paragraph()
            i += 1
            continue

        table_split_match = TABLE_SPLIT_COMMENT_PATTERN.match(stripped)
        if table_split_match:
            flush_paragraph()
            pending_table_split = parse_table_split_spec(table_split_match.group("spec"))
            i += 1
            continue

        if FIGURE_ROW_START_PATTERN.match(stripped):
            flush_paragraph()
            i += 1
            figure_items: list[tuple[MediaImage | None, str]] = []
            raw_block: list[str] = [line]
            while i < len(lines):
                candidate = lines[i]
                candidate_stripped = candidate.strip()
                raw_block.append(candidate)
                if FIGURE_ROW_END_PATTERN.match(candidate_stripped):
                    break
                if candidate_stripped:
                    image_match = IMAGE_PATTERN.match(candidate_stripped)
                    if image_match:
                        alt_text = image_match.group("alt").strip()
                        target = image_match.group("target").strip()
                        figure_items.append((resolve_image(target), alt_text))
                i += 1
            if figure_items and media_manager is not None:
                figure_xml = figure_row_xml(figure_items, media_manager)
                if figure_xml:
                    elements.append(figure_xml)
            else:
                paragraph_buffer.extend(raw_block)
            i += 1
            continue

        image_match = IMAGE_PATTERN.match(stripped)
        if image_match:
            flush_paragraph()
            target = image_match.group("target").strip()
            alt_text = image_match.group("alt").strip()
            item = resolve_image(target)
            if item is not None:
                elements.append(image_paragraph_xml(item, media_manager, alt_text=alt_text))
            else:
                paragraph_buffer.append(line)
            i += 1
            continue

        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            flush_paragraph()
            next_i = i + 1
            while next_i < len(lines) and not lines[next_i].strip():
                next_i += 1
            next_heading_match = re.match(r"^(#{1,6})\s+(.*)$", lines[next_i]) if next_i < len(lines) else None
            if next_heading_match and len(next_heading_match.group(1)) == 1:
                append_chapter_page_break()
            else:
                elements.append(page_break_xml())
            i += 1
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            flush_paragraph()
            raw_level = len(heading_match.group(1))
            level = min(raw_level, 3)
            heading_text = heading_match.group(2).strip()

            if raw_level == 1:
                current_top_heading = heading_text
                if heading_text == "附录":
                    in_appendix = True
                    current_appendix_index = 0
                    i += 1
                    continue
                in_appendix = False
                chapter_match = re.match(r"^(\d+)\b", heading_text)
                if chapter_match:
                    current_chapter_number = chapter_match.group(1)
            elif current_top_heading == "附录":
                in_appendix = True

            if len(elements) == 0 and treat_first_heading_as_title:
                elements.append(paragraph_xml(heading_text, style=str(profile.get("title")) if profile.get("title") else None, align="center"))
                i += 1
                continue

            if current_top_heading == "附录" and raw_level == 2:
                current_appendix_index += 1
                append_chapter_page_break()
                appendix_heading = heading_paragraph_xml(
                    normalize_appendix_heading(heading_text, current_appendix_index),
                    1,
                    profile,
                    numbered=False,
                )
                elements.append(appendix_heading)
                i += 1
                continue

            if raw_level == 1:
                append_chapter_page_break()

            is_unnumbered = False
            if heading_text in {"参考文献", "致谢", "附录"}:
                is_unnumbered = True
            elif in_appendix and level >= 2:
                is_unnumbered = True

            display_heading_text = heading_text
            if heading_text == "致谢":
                display_heading_text = "致  谢"

            previous_is_caption = bool(elements and f'w:pStyle w:val="{STYLE_CAPTION}"' in elements[-1])
            if heading_text == "致谢" and raw_level == 1:
                heading_xml = acknowledgement_heading_paragraph_xml(display_heading_text, profile)
            else:
                heading_xml = heading_paragraph_xml(
                    display_heading_text,
                    level,
                    profile,
                    numbered=not is_unnumbered,
                    keep_with_next=not previous_is_caption,
                )
            elements.append(heading_xml)
            i += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quote = stripped[1:].strip()
            elements.append(
                paragraph_xml(
                    quote,
                    style=str(profile.get("quote")) if profile.get("quote") else None,
                )
            )
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            flush_paragraph()
            rows = [split_markdown_row(line)]
            i += 2
            while i < len(lines):
                candidate = lines[i].strip()
                if not candidate or "|" not in candidate:
                    break
                rows.append(split_markdown_row(lines[i]))
                i += 1
            if rows:
                width = len(rows[0])
                normalized = [row[:width] + [""] * max(0, width - len(row)) for row in rows]
                table_chunks = split_table_rows(normalized, pending_table_split or [])
                caption_style = profile.get("caption") or profile.get("normal")
                for chunk_idx, table_chunk in enumerate(table_chunks):
                    if chunk_idx > 0 and last_table_caption_text:
                        elements.append(
                            build_caption_paragraph(
                                f"{last_table_caption_text}（续）",
                                style=str(caption_style) if caption_style else None,
                                math_converter=math_converter,
                                reference_anchors=reference_anchors,
                                keep_next=True,
                            )
                        )
                    elements.append(
                        table_xml(
                            table_chunk,
                            cell_style=str(profile.get("table", STYLE_TABLE_TEXT)),
                            math_converter=math_converter,
                            reference_anchors=reference_anchors,
                        )
                    )
                pending_table_split = None
                last_table_caption_text = None
            continue

        paragraph_buffer.append(line)
        i += 1

    flush_paragraph()

    if in_code and code_lines:
        elements.append(
            paragraph_xml(
                "\n".join(code_lines),
                style=str(profile.get("code")) if profile.get("code") else None,
                preserve_breaks=True,
                ppr_extra=str(profile.get("code_ppr_extra", "")),
            )
        )
    if in_math and math_lines:
        elements.append(
            math_paragraph_xml(
                "\n".join(math_lines),
                style=str(profile.get("math")) if profile.get("math") else None,
                math_converter=math_converter,
                equation_number=next_formula_number(),
            )
        )

    return elements, chapter_section_break_count > 0
