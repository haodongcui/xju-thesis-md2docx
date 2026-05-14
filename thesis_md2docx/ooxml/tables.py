from __future__ import annotations

from ..math.converter import MathConverter
from ..table_utils import (
    choose_table_font_size,
    compute_grouped_metric_column_widths,
    compute_table_column_widths,
    format_table_header_text,
    parse_grouped_step_header,
)
from .paragraphs import paragraph_with_inline_math_xml
from .xml import spacing_xml


def table_cell_xml(
    text: str,
    *,
    width: int,
    style: str,
    align: str,
    font_size: int,
    bold: bool = False,
    bottom_border: bool = False,
    grid_span: int | None = None,
    vmerge: str | None = None,
    preserve_breaks: bool = False,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
) -> str:
    p = paragraph_with_inline_math_xml(
        text,
        style=style,
        align=align,
        ppr_extra=spacing_xml(line=360, after=0),
        preserve_breaks=preserve_breaks,
        run_kwargs={"bold": bold, "size": font_size},
        math_converter=math_converter,
        reference_anchors=reference_anchors,
    )
    tc_pr_parts = ["<w:tcPr>", f'<w:tcW w:w="{width}" w:type="dxa"/>']
    tc_pr_parts.append('<w:vAlign w:val="center"/>')
    if grid_span and grid_span > 1:
        tc_pr_parts.append(f'<w:gridSpan w:val="{grid_span}"/>')
    if vmerge == "restart":
        tc_pr_parts.append('<w:vMerge w:val="restart"/>')
    elif vmerge == "continue":
        tc_pr_parts.append("<w:vMerge/>")
    if bottom_border:
        tc_pr_parts.append(
            "<w:tcBorders>"
            '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="auto"/>'
            "</w:tcBorders>"
        )
    tc_pr_parts.append("</w:tcPr>")
    return f"<w:tc>{''.join(tc_pr_parts)}{p}</w:tc>"


def table_xml(
    rows: list[list[str]],
    cell_style: str | None = None,
    *,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
) -> str:
    cell_style = cell_style or "TableText"
    col_count = max(len(rows[0]), 1)
    header_names = [rows[0][i].strip() if i < len(rows[0]) else "" for i in range(col_count)]
    grouped_header = parse_grouped_step_header(rows[0])
    col_widths = compute_grouped_metric_column_widths(col_count) if grouped_header else compute_table_column_widths(rows)
    table_font_size = choose_table_font_size(rows)
    plain_header_layout = (
        (col_count == 7 and header_names[:2] == ["任务", "条件"])
        or (col_count == 3 and header_names[0] == "方法" and all("平均" in h for h in header_names[1:]))
    )
    tbl_pr = (
        "<w:tblPr>"
        # pct 5000 = 100% of text column width → 通栏
        '<w:tblW w:w="5000" w:type="pct"/>'
        '<w:jc w:val="center"/>'
        "<w:tblCellMar>"
        '<w:top w:w="0" w:type="dxa"/>'
        '<w:left w:w="12" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/>'
        '<w:right w:w="12" w:type="dxa"/>'
        "</w:tblCellMar>"
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
        '<w:left w:val="nil"/>'
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
        '<w:right w:val="nil"/>'
        '<w:insideH w:val="nil"/>'
        '<w:insideV w:val="nil"/>'
        "</w:tblBorders>"
        '<w:tblLayout w:type="fixed"/>'
        "</w:tblPr>"
    )
    tbl_grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{col_width}"/>' for col_width in col_widths) + "</w:tblGrid>"

    # Header rows repeat across page breaks; every row carries `cantSplit` so a
    # single row never splits mid-cell, while the table itself can still flow
    # across pages when it is too tall to fit.
    trs = []
    start_row_idx = 0
    if grouped_header:
        top_cells = [
            table_cell_xml(
                grouped_header["first"],
                width=col_widths[0],
                style=cell_style,
                align="center",
                font_size=table_font_size,
                bold=True,
                vmerge="restart",
                math_converter=math_converter,
                reference_anchors=reference_anchors,
            )
        ]
        col_offset = 1
        for task_name, steps in grouped_header["groups"]:
            span = len(steps)
            top_cells.append(
                table_cell_xml(
                    task_name,
                    width=sum(col_widths[col_offset : col_offset + span]),
                    style=cell_style,
                    align="center",
                    font_size=table_font_size,
                    bold=True,
                    grid_span=span,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
            col_offset += span
        top_cells.append(
            table_cell_xml(
                grouped_header["avg"],
                width=col_widths[-1],
                style=cell_style,
                align="center",
                font_size=table_font_size,
                bold=True,
                vmerge="restart",
                math_converter=math_converter,
                reference_anchors=reference_anchors,
            )
        )
        trs.append(f"<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>{''.join(top_cells)}</w:tr>")

        second_cells = [
            table_cell_xml(
                "",
                width=col_widths[0],
                style=cell_style,
                align="center",
                font_size=table_font_size,
                vmerge="continue",
                bottom_border=True,
                math_converter=math_converter,
                reference_anchors=reference_anchors,
            )
        ]
        col_offset = 1
        for _, steps in grouped_header["groups"]:
            for step in steps:
                second_cells.append(
                    table_cell_xml(
                        f"k={step}",
                        width=col_widths[col_offset],
                        style=cell_style,
                        align="center",
                        font_size=table_font_size,
                        bold=True,
                        bottom_border=True,
                        math_converter=math_converter,
                        reference_anchors=reference_anchors,
                    )
                )
                col_offset += 1
        second_cells.append(
            table_cell_xml(
                "",
                width=col_widths[-1],
                style=cell_style,
                align="center",
                font_size=table_font_size,
                vmerge="continue",
                bottom_border=True,
                math_converter=math_converter,
                reference_anchors=reference_anchors,
            )
        )
        trs.append(f"<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>{''.join(second_cells)}</w:tr>")
        start_row_idx = 1

    for r_idx, row in enumerate(rows[start_row_idx:], start=start_row_idx):
        cells = []
        for col_idx, cell in enumerate(row):
            cell_text = cell.strip()
            if r_idx == 0 and not grouped_header:
                display_text = " ".join(cell_text.split()) if plain_header_layout else format_table_header_text(cell_text)
            else:
                display_text = cell_text
            cells.append(
                table_cell_xml(
                    display_text,
                    width=col_widths[col_idx],
                    style=cell_style,
                    align="center",
                    font_size=table_font_size,
                    bold=r_idx == 0 and not grouped_header,
                    bottom_border=r_idx == 0 and not grouped_header,
                    preserve_breaks=r_idx == 0 and not grouped_header and "\n" in display_text,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
        tr_pr_parts = ["<w:cantSplit/>"]
        if r_idx == 0 and not grouped_header:
            # Repeat the header row when the table breaks across pages so
            # readers always see column headings.
            tr_pr_parts.append('<w:tblHeader/>')
        tr_pr = f"<w:trPr>{''.join(tr_pr_parts)}</w:trPr>"
        trs.append(f"<w:tr>{tr_pr}{''.join(cells)}</w:tr>")
    return f"<w:tbl>{tbl_pr}{tbl_grid}{''.join(trs)}</w:tbl>"
