from __future__ import annotations

from pathlib import Path

from ...constants import (
    COVER_EMBLEM_NAME,
    COVER_WORDMARK_NAME,
    DEFAULT_LOCAL_COVER_ASSETS_REL,
    EMU_PER_INCH,
    SIGNATURE_IMAGE_HEIGHT_EMU,
    SIGNATURE_IMAGE_WIDTH_EMU,
)
from ...frontmatter import (
    first_nonempty_value,
    taskbook_display_width,
    taskbook_run_kwargs,
    wrap_taskbook_text,
)
from ...markdown import parse_cover_info, split_cover_title_lines
from ...math.converter import MathConverter
from ...media import MediaImage, MediaManager, fit_extent_emu
from ...ooxml.render import (
    add_page_break_before_paragraph_xml,
    formatted_paragraph_xml,
    image_run_xml,
    paragraph_with_inline_math_xml,
    paragraph_xml,
)
from ...ooxml.xml import indent_xml, run_text_xml, spacing_xml
from .styles import STYLE_BODY, STYLE_FRONT_HEADING


def resolve_cover_assets_dir(markdown_path: Path, assets_dir: Path | None, *, use_cover_assets: bool) -> Path | None:
    if not use_cover_assets:
        return None

    candidates: list[Path] = []
    if assets_dir is not None:
        candidates.append(assets_dir)
    local_assets_dir = markdown_path.parent / DEFAULT_LOCAL_COVER_ASSETS_REL
    if local_assets_dir not in candidates:
        candidates.append(local_assets_dir)

    for candidate in candidates:
        if (candidate / COVER_EMBLEM_NAME).exists() or (candidate / COVER_WORDMARK_NAME).exists():
            return candidate

    return candidates[0] if candidates else None


def cover_logo_table_xml(
    emblem_item: MediaImage | None,
    wordmark_item: MediaImage | None,
    media_manager: MediaManager | None,
) -> str:
    if media_manager is None or (emblem_item is None and wordmark_item is None):
        return ""

    tbl_pr = (
        "<w:tblPr>"
        '<w:tblW w:w="5400" w:type="dxa"/>'
        '<w:jc w:val="center"/>'
        '<w:tblLayout w:type="fixed"/>'
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
    tbl_grid = (
        "<w:tblGrid>"
        '<w:gridCol w:w="1850"/>'
        '<w:gridCol w:w="400"/>'
        '<w:gridCol w:w="3150"/>'
        "</w:tblGrid>"
    )

    def cover_logo_cell(
        item: MediaImage | None,
        *,
        max_width_in: float,
        max_height_in: float,
        align: str = "center",
    ) -> str:
        if item is None or media_manager is None:
            body = paragraph_xml(" ", align=align, ppr_extra=spacing_xml(after=0))
        else:
            width_emu, height_emu = fit_extent_emu(
                item.width_emu,
                item.height_emu,
                max_width_emu=int(max_width_in * EMU_PER_INCH),
                max_height_emu=int(max_height_in * EMU_PER_INCH),
            )
            body = paragraph_xml(
                align=align,
                runs=[
                    image_run_xml(
                        item,
                        docpr_id=media_manager.next_drawing_id(),
                        alt_text=item.filename,
                        width_emu=width_emu,
                        height_emu=height_emu,
                    )
                ],
                ppr_extra=spacing_xml(after=0),
            )
        return "<w:tc><w:tcPr><w:vAlign w:val=\"center\"/></w:tcPr>" + body + "</w:tc>"

    row = (
        "<w:tr>"
        '<w:trPr><w:trHeight w:val="860" w:hRule="atLeast"/></w:trPr>'
        + cover_logo_cell(emblem_item, max_width_in=1.29, max_height_in=1.29, align="left")
        + "<w:tc><w:tcPr><w:vAlign w:val=\"center\"/></w:tcPr>"
        + paragraph_xml(" ", ppr_extra=spacing_xml(after=0))
        + "</w:tc>"
        + cover_logo_cell(wordmark_item, max_width_in=2.42, max_height_in=1.39, align="left")
        + "</w:tr>"
    )
    return f"<w:tbl>{tbl_pr}{tbl_grid}{row}</w:tbl>"


def cover_info_table_xml(title: str, cover_info: dict[str, str]) -> str:
    title_lines = split_cover_title_lines(title)
    info_rows: list[tuple[str, str, bool]] = []

    if title_lines:
        info_rows.append(("论文题目:", title_lines[0], False))
        for extra_line in title_lines[1:]:
            info_rows.append(("", extra_line, True))

    ordered_fields = [
        ("学生姓名", "学生姓名:"),
        ("学号", "学    号:"),
        ("所属院系", "所属院系:"),
        ("专业", "专    业:"),
        ("班级", "班    级:"),
        ("指导教师", "指导老师:"),
        ("日期", "日    期:"),
    ]
    for source_key, display_label in ordered_fields:
        value = cover_info.get(source_key)
        if value:
            info_rows.append((display_label, value, True))

    tbl_pr = (
        "<w:tblPr>"
        '<w:tblW w:w="6943" w:type="dxa"/>'
        '<w:jc w:val="center"/>'
        '<w:tblLayout w:type="fixed"/>'
        "<w:tblCellMar>"
        '<w:top w:w="0" w:type="dxa"/>'
        '<w:left w:w="108" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/>'
        '<w:right w:w="108" w:type="dxa"/>'
        "</w:tblCellMar>"
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
    tbl_grid = '<w:tblGrid><w:gridCol w:w="1948"/><w:gridCol w:w="4995"/></w:tblGrid>'

    label_run = {
        "font_ascii": "Times New Roman",
        "font_hansi": "Times New Roman",
        "font_eastasia": "楷体_GB2312",
        "bold": True,
        "size": 32,
    }
    value_run = {
        "font_ascii": "Times New Roman",
        "font_hansi": "Times New Roman",
        "font_eastasia": "楷体_GB2312",
        "bold": True,
        "size": 32,
    }

    rows_xml: list[str] = []
    for idx, (label, value, draw_top) in enumerate(info_rows):
        label_para = formatted_paragraph_xml(
            label,
            align="center",
            ppr_extra=spacing_xml(before=100, after=50, line=360),
            run_kwargs=label_run,
        )
        value_para = formatted_paragraph_xml(
            value,
            align="center",
            ppr_extra=spacing_xml(before=100, after=50, line=360),
            run_kwargs=value_run,
        )
        value_borders = ["<w:tcBorders>"]
        if draw_top and idx > 0:
            value_borders.append('<w:top w:val="single" w:color="auto" w:sz="4" w:space="0"/>')
        value_borders.append('<w:bottom w:val="single" w:color="auto" w:sz="4" w:space="0"/>')
        value_borders.append("</w:tcBorders>")

        rows_xml.append(
            "<w:tr>"
            '<w:trPr><w:trHeight w:val="686" w:hRule="atLeast"/></w:trPr>'
            '<w:tc><w:tcPr><w:tcW w:w="1948" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
            + label_para
            + "</w:tc>"
            + '<w:tc><w:tcPr><w:tcW w:w="4995" w:type="dxa"/>'
            + "".join(value_borders)
            + '<w:vAlign w:val="center"/></w:tcPr>'
            + value_para
            + "</w:tc>"
            + "</w:tr>"
        )

    return f"<w:tbl>{tbl_pr}{tbl_grid}{''.join(rows_xml)}</w:tbl>"


def build_cover_elements(
    title: str,
    cover_info: dict[str, str],
    *,
    cover_assets_dir: Path | None = None,
    media_manager: MediaManager | None = None,
) -> list[str]:
    elements: list[str] = []
    title_run = {
        "font_ascii": "Times New Roman",
        "font_hansi": "Times New Roman",
        "font_eastasia": "黑体",
    }

    elements.append(
        formatted_paragraph_xml(
            "新疆大学本科毕业论文(设计)",
            align="center",
            ppr_extra=spacing_xml(before=560, after=0, line=360),
            run_kwargs={**title_run, "bold": True, "size": 52},
        )
    )

    elements.append(paragraph_xml(" ", ppr_extra=spacing_xml(after=0, line=480)))

    emblem_item = None
    wordmark_item = None
    if cover_assets_dir is not None and media_manager is not None:
        emblem_item = media_manager.register_image(cover_assets_dir / COVER_EMBLEM_NAME)
        wordmark_item = media_manager.register_image(cover_assets_dir / COVER_WORDMARK_NAME)

    logo_tbl = cover_logo_table_xml(emblem_item, wordmark_item, media_manager)
    if logo_tbl:
        elements.append(logo_tbl)

    for _ in range(2):
        elements.append(paragraph_xml(" ", ppr_extra=spacing_xml(after=132, line=360)))

    elements.append(cover_info_table_xml(title, cover_info))

    return elements


def build_front_heading(
    text: str,
    *,
    english: bool = False,
    toc: bool = False,
    statement: bool = False,
    page_break_before: bool = False,
) -> str:
    if toc:
        paragraph = formatted_paragraph_xml(
            "目  录",
            style=STYLE_FRONT_HEADING,
            align="center",
            ppr_extra='<w:snapToGrid w:val="0"/>'
            + spacing_xml(before_lines=300, before=720, after_lines=200, after=480, line=240),
            run_kwargs={
                "font_ascii": "黑体",
                "font_hansi": "黑体",
                "font_eastasia": "黑体",
                "size": 32,
            },
        )
        return add_page_break_before_paragraph_xml(paragraph) if page_break_before else paragraph

    if statement:
        run_kwargs = {
            "font_ascii": "黑体",
            "font_hansi": "黑体",
            "font_eastasia": "黑体",
            "size": 32,
        }
        ppr_extra = '<w:snapToGrid w:val="0"/>' + spacing_xml(
            before_lines=100,
            before=240,
            after_lines=200,
            after=480,
            line=240,
        )
    elif english:
        run_kwargs = {
            "font_ascii": "Times New Roman",
            "font_hansi": "Times New Roman",
            "font_eastasia": "Times New Roman",
            "size": 32,
        }
        ppr_extra = spacing_xml(before_lines=300, before=720, after_lines=200, after=480, line=240)
    else:
        run_kwargs = {
            "font_ascii": "黑体",
            "font_hansi": "黑体",
            "font_eastasia": "黑体",
            "size": 32,
        }
        ppr_extra = '<w:snapToGrid w:val="0"/>' + spacing_xml(
            before_lines=300,
            before=720,
            after_lines=200,
            after=480,
            line=240,
        )

    if page_break_before and not statement:
        if english:
            ppr_extra = spacing_xml(before_lines=300, before=720, after_lines=200, after=480, line=240)
        else:
            ppr_extra = '<w:snapToGrid w:val="0"/>' + spacing_xml(
                before_lines=300,
                before=720,
                after_lines=200,
                after=480,
                line=240,
            )

    paragraph = formatted_paragraph_xml(
        text,
        style=STYLE_FRONT_HEADING,
        align="center",
        ppr_extra=ppr_extra,
        run_kwargs=run_kwargs,
    )
    return add_page_break_before_paragraph_xml(paragraph) if page_break_before else paragraph


def build_body_paragraph(
    text: str,
    *,
    english: bool = False,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
) -> str:
    run_kwargs = {
        "font_ascii": "Times New Roman",
        "font_hansi": "Times New Roman",
        "font_eastasia": "Times New Roman" if english else "宋体",
        "size": 24,
    }
    return paragraph_with_inline_math_xml(
        text,
        style=STYLE_BODY,
        ppr_extra='<w:widowControl w:val="0"/>' + spacing_xml(line=360),
        first_line_chars=200,
        first_line=480,
        run_kwargs=run_kwargs,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
    )


def build_keyword_paragraph(keywords: str, *, english: bool = False) -> str | None:
    if not keywords:
        return None
    if english:
        runs = [
            run_text_xml(
                "KEY WORDS: ",
                bold=True,
                font_ascii="Times New Roman",
                font_hansi="Times New Roman",
                font_eastasia="Times New Roman",
                size=24,
            ),
            run_text_xml(
                keywords,
                font_ascii="Times New Roman",
                font_hansi="Times New Roman",
                font_eastasia="Times New Roman",
                size=24,
            ),
        ]
    else:
        runs = [
            run_text_xml(
                "关 键 词：",
                bold=True,
                font_ascii="Times New Roman",
                font_hansi="Times New Roman",
                font_eastasia="宋体",
                size=24,
            ),
            run_text_xml(
                keywords,
                font_ascii="Times New Roman",
                font_hansi="Times New Roman",
                font_eastasia="宋体",
                size=24,
            ),
        ]
    return paragraph_xml(
        runs=runs,
        style=STYLE_BODY,
        ppr_extra=spacing_xml(line=360) + indent_xml(left=0, first_line_chars=0, first_line=0),
    )


def build_blank_paragraph(*, style: str = STYLE_BODY, line: int = 360, run_size: int | None = None) -> str:
    if run_size is None:
        return paragraph_xml(" ", style=style, ppr_extra=spacing_xml(line=line))
    return formatted_paragraph_xml(
        " ",
        style=style,
        ppr_extra=spacing_xml(line=line),
        run_kwargs={
            "font_ascii": "Times New Roman",
            "font_hansi": "Times New Roman",
            "font_eastasia": "宋体",
            "size": run_size,
        },
    )


def build_statement_body_paragraph(
    text: str,
    *,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
) -> str:
    run_kwargs = {
        "font_ascii": "Times New Roman",
        "font_hansi": "Times New Roman",
        "font_eastasia": "宋体",
        "size": 28,
    }
    return paragraph_with_inline_math_xml(
        text,
        style=STYLE_BODY,
        ppr_extra=spacing_xml(line=360),
        first_line_chars=200,
        first_line=560,
        run_kwargs=run_kwargs,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
    )


def build_statement_signature_paragraph(
    label: str,
    value: str = "",
    *,
    is_date: bool = False,
    signature_image: MediaImage | None = None,
    media_manager: MediaManager | None = None,
    signature_alt: str = "电子签名",
) -> str:
    normalized = value.strip().strip("_").strip()
    if not normalized:
        normalized = "   年   月   日" if is_date else ""
    run_kwargs = {
        "font_ascii": "宋体",
        "font_hansi": "宋体",
        "font_eastasia": "宋体",
        "size": 28,
    }
    ppr_extra = spacing_xml(line=360)
    if not is_date:
        ppr_extra += indent_xml(right=280)
    if signature_image is not None and media_manager is not None:
        runs = [
            run_text_xml(label, **run_kwargs),
            image_run_xml(
                signature_image,
                docpr_id=media_manager.next_drawing_id(),
                alt_text=signature_alt,
                width_emu=SIGNATURE_IMAGE_WIDTH_EMU,
                height_emu=SIGNATURE_IMAGE_HEIGHT_EMU,
            ),
        ]
        return paragraph_xml(runs=runs, align="right", ppr_extra=ppr_extra)
    return formatted_paragraph_xml(
        f"{label}{normalized}",
        align="right",
        ppr_extra=ppr_extra,
        run_kwargs=run_kwargs,
    )


def taskbook_underlined_run(value: str = "", *, width: int = 24) -> str:
    text = value.strip()
    padding = " " * max(2, width - taskbook_display_width(text))
    return run_text_xml(text + padding, underline=True, **taskbook_run_kwargs())


def taskbook_line_xml(runs: list[str], *, spacing: str | None = None, align: str | None = None) -> str:
    return paragraph_xml(
        runs=runs,
        align=align,
        ppr_extra=spacing if spacing is not None else spacing_xml(line=360),
    )


def build_taskbook_elements(taskbook_text: str, cover_info: dict[str, str]) -> list[str]:
    task_info = parse_cover_info(taskbook_text)
    college = first_nonempty_value(task_info.get("学院"), cover_info.get("所属院系"))
    class_name = first_nonempty_value(task_info.get("班级"), cover_info.get("班级"))
    student = first_nonempty_value(task_info.get("姓名"), cover_info.get("学生姓名"))
    title = first_nonempty_value(task_info.get("毕业论文（设计）题目"), task_info.get("论文题目"), cover_info.get("论文题目"))
    year = first_nonempty_value(task_info.get("届"), default="……")
    start_date = first_nonempty_value(task_info.get("工作开始日期"), task_info.get("开始日期"))
    end_date = first_nonempty_value(task_info.get("工作结束日期"), task_info.get("结束日期"))
    purpose = first_nonempty_value(task_info.get("目的及意义"), task_info.get("题目的目的及意义"))
    tasks = first_nonempty_value(task_info.get("主要工作任务"), task_info.get("工作任务"))
    teacher = first_nonempty_value(task_info.get("指导教师"), cover_info.get("指导教师"))
    office_head = first_nonempty_value(task_info.get("教研室（系）主任"), task_info.get("教研室主任"))
    student_signature = first_nonempty_value(task_info.get("学生签名"))
    accepted_date = first_nonempty_value(task_info.get("接受任务日期"), task_info.get("接受日期"))

    body_run = taskbook_run_kwargs()
    title_run = taskbook_run_kwargs(bold=True, size=44)
    note_run = taskbook_run_kwargs(size=21)

    elements: list[str] = []
    elements.append(
        formatted_paragraph_xml(
            "新 疆 大 学",
            align="center",
            ppr_extra=spacing_xml(line=360),
            run_kwargs=title_run,
        )
    )
    elements.append(
        formatted_paragraph_xml(
            f"本科毕业论文（设计）任务书（{year}届）",
            align="center",
            ppr_extra="",
            run_kwargs=title_run,
        )
    )
    elements.append(paragraph_xml(""))
    elements.append(
        taskbook_line_xml(
            [
                run_text_xml("学院：", **body_run),
                taskbook_underlined_run(college, width=24),
                run_text_xml("  班级：", **body_run),
                taskbook_underlined_run(class_name, width=22),
            ]
        )
    )
    elements.append(
        taskbook_line_xml(
            [
                run_text_xml("姓名：", **body_run),
                taskbook_underlined_run(student, width=25),
            ]
        )
    )
    elements.append(
        taskbook_line_xml(
            [
                run_text_xml("毕业论文（设计）题目：", **body_run),
                taskbook_underlined_run(title, width=35),
            ]
        )
    )
    elements.append(
        taskbook_line_xml(
            [
                run_text_xml("毕业设计(论文)工作自", **body_run),
                taskbook_underlined_run(start_date, width=11),
                run_text_xml("起至", **body_run),
                taskbook_underlined_run(end_date, width=11),
                run_text_xml("止", **body_run),
            ]
        )
    )
    elements.append(formatted_paragraph_xml("毕业设计(论文)题目的目的及意义", ppr_extra="", run_kwargs=body_run))
    purpose_line_count = 3 if purpose else 6
    for line in wrap_taskbook_text(purpose, max_lines=purpose_line_count):
        elements.append(taskbook_line_xml([taskbook_underlined_run(line, width=70)]))
    elements.append(formatted_paragraph_xml("毕业设计(论文)的主要工作任务", ppr_extra="", run_kwargs=body_run))
    task_line_count = 4 if tasks else 6
    for line in wrap_taskbook_text(tasks, max_lines=task_line_count):
        elements.append(taskbook_line_xml([taskbook_underlined_run(line, width=70)]))
    elements.append(paragraph_xml("", ppr_extra=spacing_xml(line=360)))
    elements.append(
        taskbook_line_xml(
            [run_text_xml("指   导   教  师：", **body_run), taskbook_underlined_run(teacher, width=52)]
        )
    )
    elements.append(
        taskbook_line_xml(
            [run_text_xml("教研室（系）主任：", **body_run), taskbook_underlined_run(office_head, width=52)]
        )
    )
    elements.append(
        taskbook_line_xml(
            [run_text_xml("学   生   签  名：", **body_run), taskbook_underlined_run(student_signature, width=52)]
        )
    )
    elements.append(
        taskbook_line_xml(
            [run_text_xml("接受毕业论文(设计)任务日期：", **body_run), taskbook_underlined_run(accepted_date, width=39)]
        )
    )
    elements.append(formatted_paragraph_xml("（注：本任务书由指导教师填写）", ppr_extra="", run_kwargs=note_run))
    return elements
