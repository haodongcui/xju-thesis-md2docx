from __future__ import annotations

import re
import unicodedata

from .constants import BODY_TEXT_WIDTH_TWIPS


def split_markdown_row(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw.split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_markdown_row(line)
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_table_split_spec(spec: str) -> list[int]:
    return [int(part.strip()) for part in spec.split(",") if part.strip() and int(part.strip()) > 0]


def split_table_rows(rows: list[list[str]], data_row_counts: list[int]) -> list[list[list[str]]]:
    """Split a markdown table by data-row counts, keeping the header in every part."""
    if len(rows) <= 1 or not data_row_counts:
        return [rows]
    header = rows[0]
    data_rows = rows[1:]
    chunks: list[list[list[str]]] = []
    start = 0
    for count in data_row_counts:
        if start >= len(data_rows):
            break
        end = min(start + count, len(data_rows))
        if end > start:
            chunks.append([header] + data_rows[start:end])
        start = end
    if start < len(data_rows):
        chunks.append([header] + data_rows[start:])
    return chunks if chunks else [rows]


def table_visual_width(text: str) -> float:
    width = 0.0
    for ch in text.replace("\n", ""):
        if ch.isspace():
            width += 0.4
        elif unicodedata.east_asian_width(ch) in {"W", "F"}:
            width += 2.0
        elif ch.isdigit():
            width += 0.9
        elif ch.isalpha():
            width += 0.95
        else:
            width += 0.7
    return width


def is_numeric_like_table_cell(text: str) -> bool:
    compact = text.strip().replace("**", "")
    if not compact:
        return False
    if re.search(r"[\u4e00-\u9fffA-Za-z]{3,}", compact):
        return False
    return bool(re.fullmatch(r"[\d\s\.\-+±×xX/%@_=<>\(\),:;·]+", compact))


def format_table_header_text(text: str) -> str:
    compact = " ".join(text.split())
    if compact in {"Cheetah 回报", "Finger 回报", "Cartpole MSE@6", "Reacher MSE@6"}:
        return compact
    task_step = re.fullmatch(r"(Reacher|Finger|Cheetah|Cartpole)\s+k=(\d+)", compact)
    if task_step:
        return f"{task_step.group(1)}\nk={task_step.group(2)}"
    en_cn = re.fullmatch(r"([A-Za-z][A-Za-z0-9.-]*)\s+(.+)", compact)
    if en_cn and re.search(r"[\u4e00-\u9fff]", en_cn.group(2)):
        return f"{en_cn.group(1)}\n{en_cn.group(2)}"
    if compact.endswith(" 平均") and " " in compact:
        return compact.rsplit(" ", 1)[0] + "\n平均"
    if " OOD " in compact:
        left, right = compact.split(" OOD ", 1)
        return f"{left} OOD\n{right}"
    if compact == "Avg. AUC":
        return "Avg.\nAUC"
    if compact == "DreamerV3":
        return "Dreamer\nV3"
    if compact == "HaM-World":
        return "HaM-\nWorld"
    return compact


def choose_table_font_size(rows: list[list[str]]) -> int:
    col_count = max(len(rows[0]), 1)
    longest_cell = max((table_visual_width(cell) for row in rows for cell in row), default=0.0)
    header_names = [rows[0][i].strip() if i < len(rows[0]) else "" for i in range(col_count)]
    if col_count == 7 and header_names[0] == "变体":
        return 14
    if col_count == 3 and header_names[0] == "方法" and all("平均" in h for h in header_names[1:]):
        return 19
    if col_count == 7 and header_names[:2] == ["任务", "条件"]:
        return 18
    if col_count >= 12:
        return 14
    if col_count >= 7:
        if longest_cell >= 12 or len(rows) >= 5:
            return 16
        return 18
    if col_count == 6:
        return 17
    return 21


def parse_grouped_step_header(header_row: list[str]) -> dict[str, object] | None:
    if len(header_row) < 6:
        return None
    first = " ".join(header_row[0].split())
    avg = " ".join(header_row[-1].split())
    groups: list[tuple[str, list[str]]] = []
    current_task = ""
    current_steps: list[str] = []
    for cell in header_row[1:-1]:
        compact = " ".join(cell.split())
        match = re.fullmatch(r"(Reacher|Finger|Cheetah|Cartpole)\s+k=(\d+)", compact)
        if not match:
            return None
        task, step = match.groups()
        if current_task and task != current_task:
            groups.append((current_task, current_steps))
            current_steps = []
        current_task = task
        current_steps.append(step)
    if current_task:
        groups.append((current_task, current_steps))
    if len(groups) < 2 or any(len(steps) < 2 for _, steps in groups):
        return None
    return {"first": first, "avg": avg, "groups": groups}


def compute_grouped_metric_column_widths(col_count: int) -> list[int]:
    if col_count < 6:
        return [BODY_TEXT_WIDTH_TWIPS // col_count] * col_count
    first_width = 980
    avg_width = 500
    remaining_cols = col_count - 2
    remaining_width = BODY_TEXT_WIDTH_TWIPS - first_width - avg_width
    base = remaining_width // remaining_cols
    widths = [first_width] + [base] * remaining_cols + [avg_width]
    diff = BODY_TEXT_WIDTH_TWIPS - sum(widths)
    widths[-2] += diff
    return widths


def compute_table_column_widths(rows: list[list[str]]) -> list[int]:
    col_count = max(len(rows[0]), 1)
    min_widths = [480] * col_count
    header_names = [rows[0][i].strip() if i < len(rows[0]) else "" for i in range(col_count)]

    main_result_layout = (
        col_count == 6
        and header_names[0] == "方法"
        and any("AUC" in header for header in header_names)
    )
    variant_ablation_layout = col_count == 7 and header_names[0] == "变体"
    ood_comparison_layout = col_count == 7 and header_names[:2] == ["任务", "条件"]
    avg_summary_layout = col_count == 3 and header_names[0] == "方法" and all("平均" in h for h in header_names[1:])
    if main_result_layout:
        widths = [900, 1482, 1482, 1482, 1482, 1485]
        diff = BODY_TEXT_WIDTH_TWIPS - sum(widths)
        widths[-1] += diff
        return widths
    if variant_ablation_layout:
        widths = [600, 1370, 1370, 1170, 1170, 1315, 1318]
        diff = BODY_TEXT_WIDTH_TWIPS - sum(widths)
        widths[-1] += diff
        return widths
    if ood_comparison_layout:
        widths = [1250, 1450, 1220, 1220, 1300, 930, 943]
        diff = BODY_TEXT_WIDTH_TWIPS - sum(widths)
        widths[-1] += diff
        return widths
    if avg_summary_layout:
        widths = [1100, 3600, 3613]
        diff = BODY_TEXT_WIDTH_TWIPS - sum(widths)
        widths[-1] += diff
        return widths

    for idx, header in enumerate(header_names):
        if idx == 0 and not variant_ablation_layout:
            min_widths[idx] = 900
        if header in {"方法", "变体"} and not variant_ablation_layout:
            min_widths[idx] = 1400
        elif header == "任务":
            min_widths[idx] = 1100
        elif header == "条件":
            min_widths[idx] = 1000
        elif "OOD" in header:
            min_widths[idx] = 1100
        elif "平均" in header:
            min_widths[idx] = 950

    scores: list[float] = []
    for col_idx in range(col_count):
        header_display = format_table_header_text(header_names[col_idx])
        header_score = max(table_visual_width(part) for part in header_display.split("\n")) if header_display else 1.0
        if col_count <= 8:
            min_widths[col_idx] = max(min_widths[col_idx], int(header_score * 150))
        body_cells = [row[col_idx].strip() for row in rows[1:] if col_idx < len(row)]
        body_score = max((table_visual_width(cell) for cell in body_cells), default=1.0)
        numeric_ratio = (
            sum(1 for cell in body_cells if is_numeric_like_table_cell(cell)) / len(body_cells)
            if body_cells
            else 0.0
        )
        score = max(header_score, body_score)
        if col_idx == 0:
            score *= 1.55
        if header_names[col_idx] in {"方法", "变体", "任务", "条件"}:
            score *= 1.35
        elif "OOD" in header_names[col_idx]:
            score *= 1.2
        elif numeric_ratio >= 0.8:
            score *= 0.9
        scores.append(max(score, 1.0))

    total_min = sum(min_widths)
    if total_min >= BODY_TEXT_WIDTH_TWIPS:
        scale = BODY_TEXT_WIDTH_TWIPS / total_min
        widths = [max(360, int(width * scale)) for width in min_widths]
    else:
        remaining = BODY_TEXT_WIDTH_TWIPS - total_min
        score_sum = sum(scores) or float(col_count)
        widths = [
            min_widths[idx] + int(remaining * scores[idx] / score_sum)
            for idx in range(col_count)
        ]

    diff = BODY_TEXT_WIDTH_TWIPS - sum(widths)
    if diff:
        widths[-1] += diff
    return widths
