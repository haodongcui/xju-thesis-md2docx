from __future__ import annotations

from ...constants import W_NS
from ...layout import StyleBundle
from ...ooxml.parts import settings_xml
from ...styles import DocumentDefaultsSpec, StyleCatalog, StyleRoleMap, StyleSpec
from ...styles.ooxml import styles_xml as render_styles_xml


STYLE_BODY = "XjuBody"
STYLE_HEADING_1 = "XjuHeading1"
STYLE_HEADING_2 = "XjuHeading2"
STYLE_HEADING_3 = "XjuHeading3"
STYLE_FRONT_HEADING = "XjuFrontHeading"
STYLE_TOC_FIELD = "XjuTocField"
STYLE_CAPTION = "XjuCaption"
STYLE_REFERENCE = "XjuReference"
STYLE_QUOTE = "XjuQuote"
STYLE_CODE_BLOCK = "XjuCodeBlock"
STYLE_MATH_BLOCK = "XjuMathBlock"
STYLE_TABLE_TEXT = "XjuTableText"
STYLE_HEADER = "XjuHeader"
STYLE_FOOTER = "XjuFooter"


def xju_numbering_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:numbering xmlns:w="{W_NS}" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
        'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" '
        'xmlns:w16se="http://schemas.microsoft.com/office/word/2015/wordml/symex">'
        '<w:abstractNum w:abstractNumId="0">'
        '<w:multiLevelType w:val="multilevel"/>'
        '<w:lvl w:ilvl="0">'
        '<w:start w:val="1"/>'
        '<w:numFmt w:val="decimal"/>'
        f'<w:pStyle w:val="{STYLE_HEADING_1}"/>'
        '<w:suff w:val="space"/>'
        '<w:lvlText w:val="%1  "/>'
        '<w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="0" w:hanging="0"/></w:pPr>'
        '</w:lvl>'
        '<w:lvl w:ilvl="1">'
        '<w:start w:val="1"/>'
        '<w:numFmt w:val="decimal"/>'
        f'<w:pStyle w:val="{STYLE_HEADING_2}"/>'
        '<w:suff w:val="space"/>'
        '<w:lvlText w:val="%1.%2"/>'
        '<w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="0" w:hanging="0"/></w:pPr>'
        '</w:lvl>'
        '<w:lvl w:ilvl="2">'
        '<w:start w:val="1"/>'
        '<w:numFmt w:val="decimal"/>'
        f'<w:pStyle w:val="{STYLE_HEADING_3}"/>'
        '<w:suff w:val="space"/>'
        '<w:lvlText w:val="%1.%2.%3"/>'
        '<w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="0" w:hanging="0"/></w:pPr>'
        '</w:lvl>'
        '</w:abstractNum>'
        '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
        '</w:numbering>'
    )


def xju_font_table_xml() -> str:
    fonts = [
        '<w:font w:name="Times New Roman"/>',
        (
            '<w:font w:name="宋体"><w:altName w:val="SimSun"/>'
            '<w:charset w:val="86"/><w:family w:val="auto"/><w:pitch w:val="variable"/></w:font>'
        ),
        (
            '<w:font w:name="黑体"><w:altName w:val="SimHei"/>'
            '<w:charset w:val="86"/><w:family w:val="modern"/><w:pitch w:val="fixed"/></w:font>'
        ),
        (
            '<w:font w:name="楷体_GB2312"><w:altName w:val="楷体"/>'
            '<w:charset w:val="86"/><w:family w:val="modern"/><w:pitch w:val="default"/></w:font>'
        ),
        '<w:font w:name="Cambria Math"/>',
        '<w:font w:name="Courier New"/>',
        '<w:font w:name="等线"><w:altName w:val="DengXian"/></w:font>',
    ]
    body = "".join(fonts)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:fonts xmlns:w="{W_NS}">{body}</w:fonts>'
    )


def xju_style_roles() -> StyleRoleMap:
    return StyleRoleMap(
        {
            "base.normal": "Normal",
            "body.title": STYLE_HEADING_1,
            "body.normal": STYLE_BODY,
            "body.heading.level1": STYLE_HEADING_1,
            "body.heading.level2": STYLE_HEADING_2,
            "body.heading.level3": STYLE_HEADING_3,
            "front.heading": STYLE_FRONT_HEADING,
            "toc.field": STYLE_TOC_FIELD,
            "toc.level1": "TOC1",
            "toc.level2": "TOC2",
            "toc.level3": "TOC3",
            "caption.default": STYLE_CAPTION,
            "reference.item": STYLE_REFERENCE,
            "quote.block": STYLE_QUOTE,
            "code.block": STYLE_CODE_BLOCK,
            "math.block": STYLE_MATH_BLOCK,
            "table.cell": STYLE_TABLE_TEXT,
            "header.default": STYLE_HEADER,
            "footer.default": STYLE_FOOTER,
        }
    )


def xju_style_catalog() -> StyleCatalog:
    return StyleCatalog(
        defaults=DocumentDefaultsSpec(
            run_props=(
                '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                '<w:sz w:val="24"/><w:szCs w:val="24"/>',
            )
        ),
        styles=(
            StyleSpec(
                style_id="Normal",
                name="Normal",
                default=True,
                paragraph_props=('<w:widowControl w:val="0"/>', '<w:jc w:val="both"/>'),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体" w:cs="Times New Roman"/>',
                    '<w:kern w:val="2"/>',
                    '<w:sz w:val="21"/><w:szCs w:val="24"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_BODY,
                name="XJU Body",
                based_on="Normal",
                q_format=True,
                paragraph_props=(
                    '<w:widowControl w:val="0"/>',
                    '<w:jc w:val="both"/>',
                    '<w:spacing w:after="0" w:line="360" w:lineRule="auto"/>',
                    '<w:ind w:firstLineChars="200" w:firstLine="480"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    '<w:kern w:val="2"/>',
                    '<w:sz w:val="24"/><w:szCs w:val="24"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_HEADING_1,
                name="XJU Heading 1",
                based_on="Normal",
                next_style="Normal",
                q_format=True,
                paragraph_props=(
                    "<w:keepNext/>",
                    "<w:keepLines/>",
                    '<w:numPr><w:numId w:val="1"/></w:numPr>',
                    '<w:spacing w:beforeLines="300" w:before="720" w:afterLines="200" w:after="480" w:line="288" w:lineRule="auto"/>',
                    '<w:jc w:val="center"/>',
                    '<w:outlineLvl w:val="0"/>',
                ),
                run_props=(
                    "<w:bCs/>",
                    '<w:snapToGrid w:val="0"/>',
                    '<w:kern w:val="44"/>',
                    '<w:sz w:val="32"/><w:szCs w:val="44"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_HEADING_2,
                name="XJU Heading 2",
                based_on=STYLE_HEADING_1,
                next_style="Normal",
                q_format=True,
                paragraph_props=(
                    '<w:numPr><w:ilvl w:val="1"/></w:numPr>',
                    '<w:spacing w:beforeLines="100" w:before="100" w:afterLines="50" w:after="50"/>',
                    '<w:jc w:val="both"/>',
                    '<w:outlineLvl w:val="1"/>',
                ),
                run_props=('<w:bCs w:val="0"/>', '<w:sz w:val="30"/>'),
            ),
            StyleSpec(
                style_id=STYLE_HEADING_3,
                name="XJU Heading 3",
                based_on=STYLE_HEADING_2,
                next_style="Normal",
                q_format=True,
                paragraph_props=(
                    '<w:numPr><w:ilvl w:val="2"/></w:numPr>',
                    '<w:spacing w:beforeLines="50" w:before="50" w:afterLines="0" w:after="0"/>',
                    '<w:outlineLvl w:val="2"/>',
                ),
                run_props=("<w:bCs/>", '<w:sz w:val="28"/>'),
            ),
            StyleSpec(
                style_id=STYLE_FRONT_HEADING,
                name="XJU Front Heading",
                based_on="Normal",
                q_format=True,
                paragraph_props=(
                    '<w:jc w:val="center"/>',
                    '<w:spacing w:beforeLines="300" w:before="720" w:afterLines="200" w:after="480" w:line="240" w:lineRule="auto"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/>',
                    '<w:sz w:val="32"/><w:szCs w:val="32"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_TOC_FIELD,
                name="XJU TOC Field",
                based_on="Normal",
                paragraph_props=('<w:spacing w:after="0" w:line="288" w:lineRule="auto"/>',),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    '<w:sz w:val="24"/><w:szCs w:val="24"/>',
                ),
            ),
            StyleSpec(
                style_id="TOC1",
                name="toc 1",
                based_on="Normal",
                paragraph_props=(
                    '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8313"/></w:tabs>',
                    '<w:spacing w:after="0" w:line="288" w:lineRule="auto"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    '<w:sz w:val="24"/><w:szCs w:val="24"/>',
                ),
            ),
            StyleSpec(
                style_id="TOC2",
                name="toc 2",
                based_on="Normal",
                paragraph_props=(
                    '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8313"/></w:tabs>',
                    '<w:ind w:left="240"/>',
                    '<w:spacing w:after="0" w:line="288" w:lineRule="auto"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    '<w:sz w:val="24"/><w:szCs w:val="24"/>',
                ),
            ),
            StyleSpec(
                style_id="TOC3",
                name="toc 3",
                based_on="Normal",
                paragraph_props=(
                    '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8313"/></w:tabs>',
                    '<w:ind w:left="480"/>',
                    '<w:spacing w:after="0" w:line="288" w:lineRule="auto"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    '<w:sz w:val="24"/><w:szCs w:val="24"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_HEADER,
                name="XJU Header",
                based_on="Normal",
                paragraph_props=(
                    '<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="auto"/></w:pBdr>',
                    '<w:tabs><w:tab w:val="center" w:pos="4153"/><w:tab w:val="right" w:pos="8306"/></w:tabs>',
                    '<w:snapToGrid w:val="0"/>',
                    '<w:jc w:val="center"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/>',
                    '<w:sz w:val="18"/><w:szCs w:val="18"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_FOOTER,
                name="XJU Footer",
                based_on="Normal",
                paragraph_props=(
                    '<w:tabs><w:tab w:val="center" w:pos="4153"/><w:tab w:val="right" w:pos="8306"/></w:tabs>',
                    '<w:snapToGrid w:val="0"/>',
                    '<w:spacing w:line="288" w:lineRule="auto"/>',
                    '<w:ind w:firstLineChars="200" w:firstLine="200"/>',
                    '<w:jc w:val="left"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    '<w:sz w:val="18"/><w:szCs w:val="18"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_CAPTION,
                name="XJU Caption",
                based_on="Normal",
                paragraph_props=(
                    '<w:jc w:val="center"/>',
                    '<w:spacing w:beforeLines="0" w:before="0" w:afterLines="0" w:after="0" w:line="360" w:lineRule="auto"/>',
                    '<w:ind w:left="0" w:firstLine="0"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    "<w:b/>",
                    "<w:bCs/>",
                    '<w:sz w:val="21"/><w:szCs w:val="21"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_REFERENCE,
                name="XJU Reference",
                based_on="Normal",
                paragraph_props=('<w:spacing w:line="360" w:lineRule="auto"/>',),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    '<w:sz w:val="21"/><w:szCs w:val="21"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_QUOTE,
                name="XJU Quote",
                based_on=STYLE_BODY,
                paragraph_props=(
                    '<w:ind w:left="720"/>',
                    '<w:spacing w:after="120" w:line="360" w:lineRule="auto"/>',
                ),
                run_props=("<w:i/>",),
            ),
            StyleSpec(
                style_id=STYLE_CODE_BLOCK,
                name="XJU Code Block",
                based_on="Normal",
                paragraph_props=(
                    '<w:spacing w:after="120"/>',
                    '<w:shd w:val="clear" w:fill="F5F5F5"/>',
                    '<w:outlineLvl w:val="9"/>',
                ),
                run_props=(
                    '<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:eastAsia="等线"/>',
                    '<w:sz w:val="20"/><w:szCs w:val="20"/>',
                ),
            ),
            StyleSpec(
                style_id=STYLE_MATH_BLOCK,
                name="XJU Math Block",
                based_on="Normal",
                paragraph_props=(
                    '<w:jc w:val="center"/>',
                    '<w:spacing w:before="120" w:after="120" w:line="360" w:lineRule="auto"/>',
                ),
                run_props=('<w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math" w:eastAsia="Cambria Math"/>',),
            ),
            StyleSpec(
                style_id=STYLE_TABLE_TEXT,
                name="XJU Table Text",
                based_on="Normal",
                paragraph_props=('<w:spacing w:after="0" w:line="360" w:lineRule="auto"/>',),
                run_props=(
                    '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>',
                    '<w:sz w:val="21"/><w:szCs w:val="21"/>',
                ),
            ),
        ),
    )


def xju_styles_xml() -> str:
    return render_styles_xml(xju_style_catalog())


def xju_style_bundle() -> StyleBundle:
    from .header_footer import empty_footer_xml, header_xml, page_footer_xml

    return StyleBundle(
        styles_xml=xju_styles_xml(),
        numbering_xml=xju_numbering_xml(),
        settings_xml=settings_xml(),
        font_table_xml=xju_font_table_xml(),
        header_xml=header_xml(),
        empty_footer_xml=empty_footer_xml(),
        page_footer_xml=page_footer_xml(),
    )
