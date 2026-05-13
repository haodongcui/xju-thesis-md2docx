from __future__ import annotations

from xml.sax.saxutils import escape


def xml_text(text: str) -> str:
    if text == "":
        return '<w:t xml:space="preserve"></w:t>'
    text = escape(text)
    if text.startswith(" ") or text.endswith(" ") or "  " in text:
        return f'<w:t xml:space="preserve">{text}</w:t>'
    return f"<w:t>{text}</w:t>"


def run_text_xml(
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    superscript: bool = False,
    font_ascii: str | None = None,
    font_hansi: str | None = None,
    font_eastasia: str | None = None,
    size: int | None = None,
) -> str:
    rpr: list[str] = []
    fonts: list[str] = []
    if font_ascii:
        fonts.append(f'w:ascii="{escape(font_ascii)}"')
    if font_hansi:
        fonts.append(f'w:hAnsi="{escape(font_hansi)}"')
    if font_eastasia:
        fonts.append(f'w:eastAsia="{escape(font_eastasia)}"')
    if fonts:
        rpr.append(f"<w:rFonts {' '.join(fonts)}/>")
    if bold:
        rpr.append("<w:b/><w:bCs/>")
    if italic:
        rpr.append("<w:i/><w:iCs/>")
    if underline:
        rpr.append('<w:u w:val="single"/>')
    if superscript:
        rpr.append('<w:vertAlign w:val="superscript"/>')
    if size is not None:
        rpr.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    rpr_xml = f"<w:rPr>{''.join(rpr)}</w:rPr>" if rpr else ""
    return f"<w:r>{rpr_xml}{xml_text(text)}</w:r>"


def break_run_xml() -> str:
    return "<w:r><w:br/></w:r>"


def tab_run_xml() -> str:
    return "<w:r><w:tab/></w:r>"


def field_char_run_xml(kind: str, *, dirty: bool = False) -> str:
    dirty_attr = ' w:dirty="true"' if dirty else ""
    return f'<w:r><w:fldChar w:fldCharType="{kind}"{dirty_attr}/></w:r>'


def instr_text_run_xml(text: str) -> str:
    return f'<w:r><w:instrText xml:space="preserve">{escape(text)}</w:instrText></w:r>'


def spacing_xml(
    *,
    line: int | None = None,
    before: int | None = None,
    after: int | None = None,
    before_lines: int | None = None,
    after_lines: int | None = None,
    line_rule: str = "auto",
) -> str:
    attrs: list[str] = []
    if before_lines is not None:
        attrs.append(f'w:beforeLines="{before_lines}"')
    if before is not None:
        attrs.append(f'w:before="{before}"')
    if after_lines is not None:
        attrs.append(f'w:afterLines="{after_lines}"')
    if after is not None:
        attrs.append(f'w:after="{after}"')
    if line is not None:
        attrs.append(f'w:line="{line}"')
        attrs.append(f'w:lineRule="{line_rule}"')
    if not attrs:
        return ""
    return f"<w:spacing {' '.join(attrs)}/>"


def indent_xml(
    *,
    first_line_chars: int | None = None,
    first_line: int | None = None,
    left_chars: int | None = None,
    left: int | None = None,
    right: int | None = None,
    hanging: int | None = None,
) -> str:
    attrs: list[str] = []
    if first_line_chars is not None:
        attrs.append(f'w:firstLineChars="{first_line_chars}"')
    if first_line is not None:
        attrs.append(f'w:firstLine="{first_line}"')
    if left_chars is not None:
        attrs.append(f'w:leftChars="{left_chars}"')
    if left is not None:
        attrs.append(f'w:left="{left}"')
    if right is not None:
        attrs.append(f'w:right="{right}"')
    if hanging is not None:
        attrs.append(f'w:hanging="{hanging}"')
    if not attrs:
        return ""
    return f"<w:ind {' '.join(attrs)}/>"
