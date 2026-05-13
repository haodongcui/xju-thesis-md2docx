from __future__ import annotations

import datetime as dt
from xml.sax.saxutils import escape

from ..constants import *
from ..media import MediaManager


def numbering_xml() -> str:
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


def native_sect_pr_xml(
    *,
    with_header: bool = False,
    footer_kind: str | None = None,
    section_type: str | None = None,
    page_number_format: str | None = None,
    page_number_start: int | None = None,
) -> str:
    parts = ["<w:sectPr>"]
    if section_type:
        parts.append(f'<w:type w:val="{section_type}"/>')
    if with_header:
        parts.append(f'<w:headerReference w:type="default" r:id="{REL_ID_HEADER}"/>')
    if footer_kind == "empty":
        parts.append(f'<w:footerReference w:type="default" r:id="{REL_ID_EMPTY_FOOTER}"/>')
    elif footer_kind == "page":
        parts.append(f'<w:footerReference w:type="default" r:id="{REL_ID_PAGE_FOOTER}"/>')
    if page_number_format or page_number_start is not None:
        attrs: list[str] = []
        if page_number_format:
            attrs.append(f'w:fmt="{page_number_format}"')
        if page_number_start is not None:
            attrs.append(f'w:start="{page_number_start}"')
        parts.append(f"<w:pgNumType {' '.join(attrs)}/>")
    parts.append('<w:pgSz w:w="11907" w:h="16840"/>')
    parts.append(
        '<w:pgMar w:top="1440" w:right="1797" w:bottom="1440" '
        'w:left="1797" w:header="850" w:footer="992" w:gutter="0"/>'
    )
    parts.append('<w:cols w:space="720"/>')
    parts.append('<w:docGrid w:linePitch="384"/>')
    parts.append("</w:sectPr>")
    return "".join(parts)


def default_sect_pr_xml() -> str:
    return native_sect_pr_xml(with_header=True, footer_kind="page", page_number_format="decimal", page_number_start=1)


def document_xml(elements: list[str], sect_pr: str | None = None) -> str:
    sect_pr = sect_pr or default_sect_pr_xml()
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:m="{M_NS}" xmlns:wp="{WP_NS}" xmlns:a="{A_NS}" xmlns:pic="{PIC_NS}">'
        f"<w:body>{''.join(elements)}{sect_pr}</w:body>"
        "</w:document>"
    )


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:styles xmlns:w="{W_NS}">'
        "<w:docDefaults>"
        '<w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>'
        '<w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault>'
        "<w:pPrDefault/>"
        "</w:docDefaults>"
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
        '<w:pPr><w:widowControl w:val="0"/><w:jc w:val="both"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体" w:cs="Times New Roman"/>'
        '<w:kern w:val="2"/><w:sz w:val="21"/><w:szCs w:val="24"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_BODY}"><w:name w:val="XJU Body"/><w:basedOn w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:widowControl w:val="0"/><w:jc w:val="both"/><w:spacing w:after="0" w:line="360" w:lineRule="auto"/><w:ind w:firstLineChars="200" w:firstLine="480"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:kern w:val="2"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_HEADING_1}"><w:name w:val="XJU Heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:keepNext/><w:keepLines/><w:numPr><w:numId w:val="1"/></w:numPr><w:spacing w:beforeLines="300" w:before="720" w:afterLines="200" w:after="480" w:line="288" w:lineRule="auto"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/></w:pPr>'
        '<w:rPr><w:bCs/><w:snapToGrid w:val="0"/><w:kern w:val="44"/><w:sz w:val="32"/><w:szCs w:val="44"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_HEADING_2}"><w:name w:val="XJU Heading 2"/><w:basedOn w:val="{STYLE_HEADING_1}"/><w:next w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:numPr><w:ilvl w:val="1"/></w:numPr><w:spacing w:beforeLines="100" w:before="100" w:afterLines="50" w:after="50"/><w:jc w:val="both"/><w:outlineLvl w:val="1"/></w:pPr>'
        '<w:rPr><w:bCs w:val="0"/><w:sz w:val="30"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_HEADING_3}"><w:name w:val="XJU Heading 3"/><w:basedOn w:val="{STYLE_HEADING_2}"/><w:next w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:numPr><w:ilvl w:val="2"/></w:numPr><w:spacing w:beforeLines="50" w:before="50" w:afterLines="0" w:after="0"/><w:outlineLvl w:val="2"/></w:pPr>'
        '<w:rPr><w:bCs/><w:sz w:val="28"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_FRONT_HEADING}"><w:name w:val="XJU Front Heading"/><w:basedOn w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:jc w:val="center"/><w:spacing w:beforeLines="300" w:before="720" w:afterLines="200" w:after="480" w:line="240" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="黑体" w:hAnsi="黑体" w:eastAsia="黑体"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_TOC_FIELD}"><w:name w:val="XJU TOC Field"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:spacing w:after="0" w:line="288" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8313"/></w:tabs><w:spacing w:after="0" w:line="288" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="TOC2"><w:name w:val="toc 2"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8313"/></w:tabs><w:ind w:left="240"/><w:spacing w:after="0" w:line="288" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="TOC3"><w:name w:val="toc 3"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8313"/></w:tabs><w:ind w:left="480"/><w:spacing w:after="0" w:line="288" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_HEADER}"><w:name w:val="XJU Header"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="auto"/></w:pBdr><w:tabs><w:tab w:val="center" w:pos="4153"/><w:tab w:val="right" w:pos="8306"/></w:tabs><w:snapToGrid w:val="0"/><w:jc w:val="center"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_FOOTER}"><w:name w:val="XJU Footer"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:tabs><w:tab w:val="center" w:pos="4153"/><w:tab w:val="right" w:pos="8306"/></w:tabs><w:snapToGrid w:val="0"/><w:spacing w:line="288" w:lineRule="auto"/><w:ind w:firstLineChars="200" w:firstLine="200"/><w:jc w:val="left"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_CAPTION}"><w:name w:val="XJU Caption"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:jc w:val="center"/><w:spacing w:beforeLines="0" w:before="0" w:afterLines="0" w:after="0" w:line="360" w:lineRule="auto"/><w:ind w:left="0" w:firstLine="0"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:b/><w:bCs/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_REFERENCE}"><w:name w:val="XJU Reference"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_QUOTE}"><w:name w:val="XJU Quote"/><w:basedOn w:val="{STYLE_BODY}"/>'
        '<w:pPr><w:ind w:left="720"/><w:spacing w:after="120" w:line="360" w:lineRule="auto"/></w:pPr><w:rPr><w:i/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_CODE_BLOCK}"><w:name w:val="XJU Code Block"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:spacing w:after="120"/><w:shd w:val="clear" w:fill="F5F5F5"/><w:outlineLvl w:val="9"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:eastAsia="等线"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_MATH_BLOCK}"><w:name w:val="XJU Math Block"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:jc w:val="center"/><w:spacing w:before="120" w:after="120" w:line="360" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math" w:eastAsia="Cambria Math"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="{STYLE_TABLE_TEXT}"><w:name w:val="XJU Table Text"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:spacing w:after="0" w:line="360" w:lineRule="auto"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:style>'
        "</w:styles>"
    )


def content_types_xml(image_extensions: set[str] | None = None) -> str:
    defaults = [
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
    ]
    for ext in sorted(image_extensions or set()):
        content_type = IMAGE_CONTENT_TYPES.get(ext)
        if content_type:
            defaults.append(f'<Default Extension="{ext}" ContentType="{content_type}"/>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        f'{"".join(defaults)}'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
        '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
        '<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>'
        '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
        '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
        '<Override PartName="/word/footer2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    )


def rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def document_rels_xml(media_manager: MediaManager | None = None) -> str:
    relationships = [
        f'<Relationship Id="{REL_ID_STYLES}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
        f'<Relationship Id="{REL_ID_NUMBERING}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>',
        f'<Relationship Id="{REL_ID_SETTINGS}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>',
        f'<Relationship Id="{REL_ID_FONT_TABLE}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>',
        f'<Relationship Id="{REL_ID_HEADER}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>',
        f'<Relationship Id="{REL_ID_EMPTY_FOOTER}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>',
        f'<Relationship Id="{REL_ID_PAGE_FOOTER}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer2.xml"/>',
    ]
    if media_manager:
        for item in media_manager.images:
            relationships.append(
                f'<Relationship Id="{item.rel_id}" Type="{IMAGE_REL_TYPE}" Target="{item.part_name}"/>'
            )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(relationships)}'
        "</Relationships>"
    )


def settings_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:settings xmlns:w="{W_NS}">'
        '<w:updateFields w:val="true"/>'
        '<w:zoom w:percent="100"/>'
        "<w:bordersDoNotSurroundHeader/>"
        "<w:bordersDoNotSurroundFooter/>"
        '<w:defaultTabStop w:val="420"/>'
        '<w:drawingGridHorizontalSpacing w:val="105"/>'
        '<w:drawingGridVerticalSpacing w:val="156"/>'
        '<w:displayHorizontalDrawingGridEvery w:val="0"/>'
        '<w:displayVerticalDrawingGridEvery w:val="2"/>'
        '<w:characterSpacingControl w:val="compressPunctuation"/>'
        '<w:themeFontLang w:val="en-US" w:eastAsia="zh-CN"/>'
        "<w:compat>"
        "<w:spaceForUL/>"
        "<w:balanceSingleByteDoubleByteWidth/>"
        "<w:doNotLeaveBackslashAlone/>"
        "<w:ulTrailSpace/>"
        "<w:doNotExpandShiftReturn/>"
        "<w:adjustLineHeightInTable/>"
        "<w:useFELayout/>"
        '<w:compatSetting w:name="compatibilityMode" '
        'w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>'
        '<w:compatSetting w:name="overrideTableStyleFontSizeAndJustification" '
        'w:uri="http://schemas.microsoft.com/office/word" w:val="1"/>'
        '<w:compatSetting w:name="enableOpenTypeFeatures" '
        'w:uri="http://schemas.microsoft.com/office/word" w:val="1"/>'
        '<w:compatSetting w:name="doNotFlipMirrorIndents" '
        'w:uri="http://schemas.microsoft.com/office/word" w:val="1"/>'
        '<w:compatSetting w:name="differentiateMultirowTableHeaders" '
        'w:uri="http://schemas.microsoft.com/office/word" w:val="1"/>'
        "</w:compat>"
        "</w:settings>"
    )


def font_table_xml() -> str:
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


def core_xml(title: str) -> str:
    created = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<cp:coreProperties xmlns:cp="{CP_NS}" xmlns:dc="{DC_NS}" xmlns:dcterms="{DCTERMS_NS}" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="{XSI_NS}">'
        f"<dc:title>{escape(title)}</dc:title>"
        "<dc:creator>Codex</dc:creator>"
        "<cp:lastModifiedBy>Codex</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def app_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="{VT_NS}">'
        "<Application>Codex</Application>"
        "</Properties>"
    )
