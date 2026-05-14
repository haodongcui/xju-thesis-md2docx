from __future__ import annotations

import re

from thesis_md2docx.body_rules import BodyParseRules
from thesis_md2docx.profiles.xju_undergraduate_thesis.body import body_parse_rules


def test_empty_body_rules_do_not_assume_thesis_headings() -> None:
    rules = BodyParseRules()

    assert not rules.is_reference_heading("参考文献")
    assert not rules.is_acknowledgement_heading("致谢")
    assert not rules.is_appendix_heading("附录")
    assert not rules.is_caption_paragraph("图 1-1 示例")
    assert rules.extract_chapter_number("1 绪论") == ""


def test_xju_body_rules_define_thesis_semantics() -> None:
    rules = body_parse_rules()

    assert rules.is_reference_heading("参考文献")
    assert rules.is_acknowledgement_heading("致谢")
    assert rules.display_heading_text("致谢") == "致  谢"
    assert rules.is_appendix_heading("附录")
    assert rules.is_reference_entry("[1] 作者. 题名.")
    assert rules.is_caption_paragraph("图 2-1 模型结构")
    assert rules.is_table_caption("表 2-1 实验设置")
    assert rules.table_split_spec("<!-- thesis-table-split: 8, 10 -->") == "8, 10"
    assert rules.extract_chapter_number("1 绪论") == "1"
    assert rules.formula_scope(in_appendix=True, current_appendix_index=2, current_chapter_number="") == "附录2"


def test_table_split_spec_can_use_numbered_capture_group() -> None:
    rules = BodyParseRules(table_split_pattern=re.compile(r"^split:\s*(\d+(?:,\s*\d+)*)$"))

    assert rules.table_split_spec("split: 3, 4") == "3, 4"
