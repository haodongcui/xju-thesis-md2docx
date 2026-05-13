from __future__ import annotations

import re

from ...constants import *
from ...ooxml.parts import native_sect_pr_xml
from ...ooxml.render import paragraph_xml
from ...ooxml.xml import indent_xml, spacing_xml


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
        if level == 2:
            ppr_extra = (
                ("<w:keepNext/><w:keepLines/>" if keep_with_next else "")
                + spacing_xml(before=240, after=120, line=360)
                + indent_xml(left=0, first_line=0)
            )
            return paragraph_xml(heading_text, style=str(style) if style else None, align="left", ppr_extra=ppr_extra)
        if level == 1:
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
        ppr_extra += (
            ("<w:keepNext/><w:keepLines/>" if keep_with_next else "")
            + spacing_xml(before=120, line=360)
            + indent_xml(left=0, first_line_chars=200, first_line=560)
        )
        return paragraph_xml(text.strip(), style=str(style) if style else None, align="left", ppr_extra=ppr_extra)
    return paragraph_xml(text.strip(), style=str(style) if style else None, ppr_extra=ppr_extra)


def acknowledgement_heading_paragraph_xml(text: str, profile: dict[str, object]) -> str:
    style = profile.get("heading1")
    ppr_extra = (
        '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
        '<w:snapToGrid w:val="0"/>'
        + spacing_xml(before_lines=0, before=0, after_lines=200, after=480, line=240)
    )
    return paragraph_xml(text.strip(), style=str(style) if style else None, ppr_extra=ppr_extra)


def body_style_profile() -> dict[str, object]:
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
        "heading_builder": heading_paragraph_xml,
        "acknowledgement_heading_builder": acknowledgement_heading_paragraph_xml,
        "appendix_heading_normalizer": normalize_appendix_heading,
        "appendix_reference_normalizer": normalize_appendix_references,
        "section_pr_builder": native_sect_pr_xml,
    }
