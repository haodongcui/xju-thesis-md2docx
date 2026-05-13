from __future__ import annotations

from xml.sax.saxutils import escape

from ..constants import EMU_PER_INCH, FIGURE_ROW_MAX_HEIGHT_IN, FIGURE_ROW_MAX_WIDTH_IN
from ..media import MediaImage, MediaManager, fit_extent_emu
from .paragraphs import formatted_paragraph_xml, paragraph_xml
from .xml import spacing_xml


def image_run_xml(
    item: MediaImage,
    *,
    docpr_id: int,
    alt_text: str = "",
    width_emu: int | None = None,
    height_emu: int | None = None,
) -> str:
    width_emu = width_emu or item.width_emu
    height_emu = height_emu or item.height_emu
    descr = escape(alt_text or item.filename)
    name = escape(item.filename)
    return (
        "<w:r><w:drawing>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{width_emu}" cy="{height_emu}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{docpr_id}" name="{name}" descr="{descr}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        "<a:graphic>"
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        "<pic:pic>"
        "<pic:nvPicPr>"
        f'<pic:cNvPr id="{docpr_id}" name="{name}"/>'
        "<pic:cNvPicPr/>"
        "</pic:nvPicPr>"
        "<pic:blipFill>"
        f'<a:blip r:embed="{item.rel_id}"/>'
        "<a:stretch><a:fillRect/></a:stretch>"
        "</pic:blipFill>"
        "<pic:spPr>"
        '<a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{width_emu}" cy="{height_emu}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        "</pic:spPr>"
        "</pic:pic>"
        "</a:graphicData>"
        "</a:graphic>"
        "</wp:inline>"
        "</w:drawing></w:r>"
    )


def image_paragraph_xml(item: MediaImage, media_manager: MediaManager, *, alt_text: str = "") -> str:
    # `<w:keepNext/>` keeps the image with its following caption paragraph on the
    # same page when feasible, avoiding figure/caption splits across page breaks.
    return paragraph_xml(
        align="center",
        runs=[image_run_xml(item, docpr_id=media_manager.next_drawing_id(), alt_text=alt_text)],
        ppr_extra=spacing_xml(after=120) + "<w:keepNext/>",
    )


def figure_row_xml(
    items: list[tuple[MediaImage | None, str]],
    media_manager: MediaManager,
) -> str:
    if not items:
        return ""

    col_count = len(items)
    col_width = max(1800, 9000 // col_count)
    max_width_emu = int(FIGURE_ROW_MAX_WIDTH_IN * EMU_PER_INCH)
    max_height_emu = int(FIGURE_ROW_MAX_HEIGHT_IN * EMU_PER_INCH)
    common_height_emu = max_height_emu
    for item, _ in items:
        if item is None or item.width_emu <= 0 or item.height_emu <= 0:
            continue
        height_limit_by_width = int(max_width_emu * item.height_emu / item.width_emu)
        common_height_emu = min(common_height_emu, max(1, height_limit_by_width))
    common_height_emu = max(1, min(common_height_emu, max_height_emu))
    tbl_pr = (
        "<w:tblPr>"
        '<w:tblW w:w="9000" w:type="dxa"/>'
        '<w:jc w:val="center"/>'
        "<w:tblBorders>"
        '<w:top w:val="nil"/>'
        '<w:left w:val="nil"/>'
        '<w:bottom w:val="nil"/>'
        '<w:right w:val="nil"/>'
        '<w:insideH w:val="nil"/>'
        '<w:insideV w:val="nil"/>'
        "</w:tblBorders>"
        "</w:tblPr>"
    )
    tbl_grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{col_width}"/>' for _ in range(col_count)) + "</w:tblGrid>"

    cells: list[str] = []
    for item, alt_text in items:
        body: list[str] = []
        tc_pr = f'<w:tcPr><w:tcW w:w="{col_width}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
        if item is None:
            body.append(
                formatted_paragraph_xml(
                    "图片待补充",
                    align="center",
                    ppr_extra=spacing_xml(after=60),
                    run_kwargs={"italic": True},
                )
            )
        else:
            width_emu = max(1, int(item.width_emu * common_height_emu / item.height_emu))
            height_emu = common_height_emu
            if width_emu > max_width_emu:
                width_emu, height_emu = fit_extent_emu(
                    item.width_emu,
                    item.height_emu,
                    max_width_emu=max_width_emu,
                    max_height_emu=max_height_emu,
                )
            body.append(
                paragraph_xml(
                    align="center",
                    runs=[
                        image_run_xml(
                            item,
                            docpr_id=media_manager.next_drawing_id(),
                            alt_text=alt_text,
                            width_emu=width_emu,
                            height_emu=height_emu,
                        )
                    ],
                    ppr_extra=spacing_xml(after=80),
                )
            )
        if alt_text:
            body.append(paragraph_xml(alt_text, align="center", ppr_extra=spacing_xml(after=0)))
        cells.append(f"<w:tc>{tc_pr}{''.join(body)}</w:tc>")

    # `cantSplit` keeps every image in the side-by-side row on a single page; the
    # outer paragraph following this table is set to `keepNext` so that the row
    # stays adjacent to its caption.
    tr_pr = "<w:trPr><w:cantSplit/></w:trPr>"
    return f"<w:tbl>{tbl_pr}{tbl_grid}<w:tr>{tr_pr}{''.join(cells)}</w:tr></w:tbl>"


