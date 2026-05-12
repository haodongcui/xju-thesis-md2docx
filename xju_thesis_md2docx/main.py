#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import subprocess
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency in some environments
    Image = None

TOOL_ROOT = Path(__file__).resolve().parent
DEFAULT_COVER_ASSETS_DIR = TOOL_ROOT / "resources"
DEFAULT_LOCAL_COVER_ASSETS_REL = Path("img/cover-assets")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"

INLINE_MATH_PATTERN = re.compile(r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$(?!\$)")
INLINE_CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*(?:[-,，]\s*\d+)*)+)\]")
IMAGE_PATTERN = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]+)\)$")
FIGURE_ROW_START_PATTERN = re.compile(r"^:::\s*figure-row\s*$")
FIGURE_ROW_END_PATTERN = re.compile(r"^:::\s*$")
TABLE_SPLIT_COMMENT_PATTERN = re.compile(
    r"^<!--\s*xju-table-split\s*:\s*(?P<spec>\d+(?:\s*,\s*\d+)*)\s*-->\s*$"
)
CAPTION_PATTERN = re.compile(
    r"^[图表]\s*(?:附录\d+-)?(?:[A-Z]|\d+)(?:[-.]\d+)*(?:\([a-zA-Z]\))?\s+"
)
WORD_MATH_DIR = TOOL_ROOT / "world-math"
WORD_MATH_SCRIPT = WORD_MATH_DIR / "convert.js"
WORD_MATH_REQUIRED_MODULES = (
    WORD_MATH_DIR / "node_modules" / "temml",
    WORD_MATH_DIR / "node_modules" / "@hungknguyen" / "mathml2omml",
)
OMML_TEXT_PATTERN = re.compile(r"(<(?:m|w):t\b[^>]*>)(.*?)(</(?:m|w):t>)", re.DOTALL)
OMML_ACCENT_CHAR_MAP = {
    "^": "\u0302",  # combining circumflex accent
    "ˆ": "\u0302",
    "‾": "\u0305",  # combining overline
    "¯": "\u0305",
    "ˉ": "\u0305",
}
COVER_EMBLEM_NAME = "xju-emblem.jpeg"
COVER_WORDMARK_NAME = "xju-wordmark.png"

IMAGE_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
}
IMAGE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
EMU_PER_INCH = 914400
DEFAULT_DPI = 96
MAX_IMAGE_WIDTH_IN = 5.8
MAX_IMAGE_HEIGHT_IN = 8.0
FIGURE_ROW_MAX_WIDTH_IN = 2.75
FIGURE_ROW_MAX_HEIGHT_IN = 3.2
BODY_TEXT_WIDTH_TWIPS = 8313
BODY_TEXT_CENTER_TWIPS = BODY_TEXT_WIDTH_TWIPS // 2
SIGNATURE_IMAGE_WIDTH_EMU = 1051560
SIGNATURE_IMAGE_HEIGHT_EMU = 494511

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

REL_ID_STYLES = "rId1"
REL_ID_SETTINGS = "rId2"
REL_ID_FONT_TABLE = "rId3"
REL_ID_HEADER = "rId4"
REL_ID_EMPTY_FOOTER = "rId5"
REL_ID_PAGE_FOOTER = "rId6"
REL_ID_NUMBERING = "rId7"
IMAGE_STARTING_RID = 8


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


def text_runs(text: str, run_kwargs: dict[str, object] | None = None, preserve_breaks: bool = False) -> list[str]:
    run_kwargs = run_kwargs or {}
    if preserve_breaks and "\n" in text:
        parts = text.split("\n")
        runs: list[str] = []
        for idx, part in enumerate(parts):
            runs.extend(text_runs(part, run_kwargs=run_kwargs, preserve_breaks=False))
            if idx != len(parts) - 1:
                runs.append(break_run_xml())
        return runs

    text = text.replace("\\_", "_")
    segments = split_inline_emphasis(text)
    runs: list[str] = []
    for kind, value in segments:
        local_kwargs = dict(run_kwargs)
        if kind == "bold":
            local_kwargs["bold"] = True
        elif kind == "italic":
            local_kwargs["italic"] = True
        runs.append(run_text_xml(value, **local_kwargs))
    return runs


def split_inline_code(text: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    i = 0
    last = 0
    while i < len(text):
        if text[i] != "`":
            i += 1
            continue

        tick_count = 1
        while i + tick_count < len(text) and text[i + tick_count] == "`":
            tick_count += 1

        marker = "`" * tick_count
        closing = text.find(marker, i + tick_count)
        if closing == -1:
            i += tick_count
            continue

        if i > last:
            parts.append(("text", text[last:i]))
        parts.append(("code", text[i + tick_count : closing]))
        i = closing + tick_count
        last = i

    if last < len(text):
        parts.append(("text", text[last:]))

    return parts if parts else [("text", text)]


def split_inline_emphasis(text: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    pattern = re.compile(r"\*\*.+?\*\*|\*[^*\n][^*\n]*?\*")
    last = 0
    for match in pattern.finditer(text):
        if match.start() > last:
            parts.append(("text", text[last:match.start()]))
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            parts.append(("bold", token[2:-2]))
        else:
            parts.append(("italic", token[1:-1]))
        last = match.end()
    if last < len(text):
        parts.append(("text", text[last:]))
    return parts if parts else [("text", text)]


def split_inline_math(text: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    last = 0
    for match in INLINE_MATH_PATTERN.finditer(text):
        if match.start() > last:
            parts.append(("text", text[last:match.start()]))
        latex = match.group(1).strip()
        if latex:
            parts.append(("math", latex))
        else:
            parts.append(("text", "$$"))
        last = match.end()
    if last < len(text):
        parts.append(("text", text[last:]))
    return [(kind, value.replace(r"\$", "$")) for kind, value in parts if value]


def inline_code_run_xml(text: str, *, size: int | None = None) -> str:
    return run_text_xml(
        text,
        font_ascii="Courier New",
        font_hansi="Courier New",
        font_eastasia="等线",
        size=size,
    )


def reference_bookmark_name(ref_id: str) -> str:
    return f"ref_{ref_id}"


def reference_bookmark_id(ref_id: str) -> int:
    return 1000 + int(ref_id)


def extract_reference_anchors(text: str) -> dict[str, str]:
    anchors: dict[str, str] = {}
    for ref_id in re.findall(r"^\[(\d+)\]\s", text, re.MULTILINE):
        anchors.setdefault(ref_id, reference_bookmark_name(ref_id))
    return anchors


def hyperlink_run_xml(
    text: str,
    anchor: str,
    *,
    run_kwargs: dict[str, object] | None = None,
    superscript: bool = False,
) -> str:
    run_kwargs = dict(run_kwargs or {})
    run_kwargs.pop("bold", None)
    run_kwargs.pop("italic", None)
    rpr: list[str] = []
    fonts: list[str] = []
    if font_ascii := run_kwargs.get("font_ascii"):
        fonts.append(f'w:ascii="{escape(str(font_ascii))}"')
    if font_hansi := run_kwargs.get("font_hansi"):
        fonts.append(f'w:hAnsi="{escape(str(font_hansi))}"')
    if font_eastasia := run_kwargs.get("font_eastasia"):
        fonts.append(f'w:eastAsia="{escape(str(font_eastasia))}"')
    if fonts:
        rpr.append(f"<w:rFonts {' '.join(fonts)}/>")
    if size := run_kwargs.get("size"):
        rpr.append(f'<w:sz w:val="{int(size)}"/><w:szCs w:val="{int(size)}"/>')
    if superscript:
        rpr.append('<w:vertAlign w:val="superscript"/>')
    rpr_xml = f"<w:rPr>{''.join(rpr)}</w:rPr>" if rpr else ""
    return f'<w:hyperlink w:anchor="{escape(anchor)}" w:history="1"><w:r>{rpr_xml}{xml_text(text)}</w:r></w:hyperlink>'


def citation_text_runs(
    text: str,
    *,
    run_kwargs: dict[str, object] | None = None,
    reference_anchors: dict[str, str] | None = None,
) -> list[str]:
    if not reference_anchors:
        return text_runs(text, run_kwargs=run_kwargs)

    runs: list[str] = []
    last = 0
    for match in INLINE_CITATION_PATTERN.finditer(text):
        if match.start() > last:
            runs.extend(text_runs(text[last:match.start()], run_kwargs=run_kwargs))

        ref_ids = re.findall(r"\d+", match.group(1))
        anchor = reference_anchors.get(ref_ids[0]) if ref_ids else None
        if anchor:
            runs.append(
                hyperlink_run_xml(
                    match.group(0),
                    anchor,
                    run_kwargs=run_kwargs,
                    superscript=True,
                )
            )
        else:
            runs.append(run_text_xml(match.group(0), superscript=True, **(run_kwargs or {})))
        last = match.end()

    if last < len(text):
        runs.extend(text_runs(text[last:], run_kwargs=run_kwargs))
    return runs


def paragraph_with_inline_math_xml(
    text: str,
    *,
    style: str | None = None,
    align: str | None = None,
    ppr_extra: str = "",
    first_line_chars: int | None = None,
    first_line: int | None = None,
    preserve_breaks: bool = False,
    run_kwargs: dict[str, object] | None = None,
    math_converter: "MathConverter | None" = None,
    reference_anchors: dict[str, str] | None = None,
) -> str:
    code_segments = split_inline_code(text)
    has_code = any(kind == "code" for kind, _ in code_segments)
    has_math = any(
        kind == "math"
        for segment_kind, segment_text in code_segments
        if segment_kind == "text"
        for kind, _ in split_inline_math(segment_text)
    )
    has_citation = any(
        bool(reference_anchors) and bool(INLINE_CITATION_PATTERN.search(segment_text))
        for segment_kind, segment_text in code_segments
        if segment_kind == "text"
    )
    if not has_code and not has_math and not has_citation:
        return formatted_paragraph_xml(
            text,
            style=style,
            align=align,
            ppr_extra=ppr_extra,
            first_line_chars=first_line_chars,
            first_line=first_line,
            preserve_breaks=preserve_breaks,
            run_kwargs=run_kwargs,
        )

    run_kwargs = run_kwargs or {}
    runs: list[str] = []
    code_size = int(run_kwargs.get("size")) if run_kwargs.get("size") else None
    for segment_kind, segment_text in code_segments:
        if segment_kind == "code":
            runs.append(inline_code_run_xml(segment_text, size=code_size))
            continue
        for kind, value in split_inline_math(segment_text):
            if kind == "text":
                runs.extend(citation_text_runs(value, run_kwargs=run_kwargs, reference_anchors=reference_anchors))
                continue
            omml = math_converter.get(value, display_mode=False) if math_converter else None
            if omml:
                runs.append(omml)
            else:
                runs.append(run_text_xml(f"${value}$", **run_kwargs))

    return paragraph_xml(
        style=style,
        align=align,
        runs=runs,
        ppr_extra=ppr_extra,
        first_line_chars=first_line_chars,
        first_line=first_line,
    )


def math_paragraph_xml(
    latex: str,
    *,
    style: str | None = None,
    align: str | None = None,
    math_converter: "MathConverter | None" = None,
    equation_number: str | None = None,
) -> str:
    # Give display equations a bit more breathing room than normal body text and
    # disable document-grid snapping so taller formulas are not visually cramped.
    math_ppr_extra = '<w:snapToGrid w:val="0"/>' + spacing_xml(before=120, after=120, line=360)
    if equation_number:
        math_ppr_extra += (
            "<w:tabs>"
            f'<w:tab w:val="center" w:pos="{BODY_TEXT_CENTER_TWIPS}"/>'
            f'<w:tab w:val="right" w:pos="{BODY_TEXT_WIDTH_TWIPS}"/>'
            "</w:tabs>"
        )
        runs: list[str] = [tab_run_xml()]
        if math_converter:
            omml = math_converter.get(latex, display_mode=True)
            if omml:
                runs.append(omml)
            else:
                runs.append(run_text_xml(latex))
        else:
            runs.append(run_text_xml(latex))
        runs.append(tab_run_xml())
        runs.append(
            run_text_xml(
                equation_number,
                font_ascii="Times New Roman",
                font_hansi="Times New Roman",
                font_eastasia="宋体",
                size=24,
            )
        )
        return paragraph_xml(
            style=style,
            align=align,
            runs=runs,
            ppr_extra=math_ppr_extra,
            first_line_chars=0,
            first_line=0,
        )
    if math_converter:
        omml = math_converter.get(latex, display_mode=True)
        if omml:
            return paragraph_xml(style=style, align=align, runs=[omml], ppr_extra=math_ppr_extra)
    return paragraph_xml(latex, style=style, align=align, ppr_extra=math_ppr_extra)


def collect_math_items(text: str) -> list[tuple[str, bool]]:
    items: list[tuple[str, bool]] = []
    seen: set[tuple[str, bool]] = set()
    lines = text.splitlines()
    in_code = False
    in_math = False
    math_lines: list[str] = []

    def remember(latex: str, display_mode: bool) -> None:
        normalized = latex.strip()
        if not normalized:
            return
        key = (normalized, display_mode)
        if key not in seen:
            seen.add(key)
            items.append(key)

    for line in lines:
        stripped = line.strip()

        if in_code:
            if stripped.startswith("```"):
                in_code = False
            continue

        if in_math:
            if stripped == "$$":
                remember("\n".join(math_lines).strip("\n"), True)
                in_math = False
                math_lines = []
            else:
                math_lines.append(line.rstrip("\n"))
            continue

        if stripped.startswith("```"):
            in_code = True
            continue

        if stripped == "$$":
            in_math = True
            math_lines = []
            continue

        for segment_kind, segment_text in split_inline_code(line):
            if segment_kind != "text":
                continue
            for kind, value in split_inline_math(segment_text):
                if kind == "math":
                    remember(value, False)

    if in_math and math_lines:
        remember("\n".join(math_lines).strip("\n"), True)

    return items


class MathConverter:
    def __init__(self) -> None:
        self.cache: dict[tuple[str, bool], str | None] = {}
        self.ready = False
        self.failed = False
        self.failed_reason: str | None = None
        self.fallback_items: set[tuple[str, bool]] = set()
        self.item_errors: list[str] = []
        self.warning_reported = False

    def _remember_failure(self, reason: str) -> None:
        self.failed = True
        if self.failed_reason is None:
            self.failed_reason = reason

    def _remember_item_error(self, message: str) -> None:
        cleaned = message.strip()
        if cleaned and cleaned not in self.item_errors and len(self.item_errors) < 3:
            self.item_errors.append(cleaned)

    def ensure_ready(self) -> bool:
        if self.failed:
            return False
        if self.ready:
            return True
        if not WORD_MATH_SCRIPT.exists():
            self._remember_failure(f"missing converter script: {WORD_MATH_SCRIPT}")
            return False
        missing_modules = [str(path) for path in WORD_MATH_REQUIRED_MODULES if not path.exists()]
        if missing_modules:
            self._remember_failure(
                "formula converter dependencies are not installed"
            )
            return False
        self.ready = True
        return True

    def convert_many(self, items: list[tuple[str, bool]]) -> None:
        pending = []
        for latex, display_mode in items:
            key = (latex.strip(), display_mode)
            if key[0] and key not in self.cache:
                pending.append(key)
        if not pending:
            return
        if not self.ensure_ready():
            for key in pending:
                self.cache[key] = None
                self.fallback_items.add(key)
            return

        payload = {
            "items": [
                {"id": str(idx), "latex": latex, "displayMode": display_mode}
                for idx, (latex, display_mode) in enumerate(pending)
            ]
        }
        try:
            result = subprocess.run(
                ["node", str(WORD_MATH_SCRIPT)],
                cwd=WORD_MATH_DIR,
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout or "{}")
        except FileNotFoundError:
            self._remember_failure("node is not available, so formulas cannot be converted into Word equations")
            for key in pending:
                self.cache[key] = None
                self.fallback_items.add(key)
            return
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip().splitlines()
            reason = "the formula converter failed while invoking node"
            if detail:
                reason += f": {detail[0]}"
            self._remember_failure(reason)
            for key in pending:
                self.cache[key] = None
                self.fallback_items.add(key)
            return
        except json.JSONDecodeError:
            self._remember_failure("the formula converter returned invalid output")
            for key in pending:
                self.cache[key] = None
                self.fallback_items.add(key)
            return

        results = {str(item.get("id")): item for item in data.get("results", []) if isinstance(item, dict)}
        for idx, key in enumerate(pending):
            item = results.get(str(idx), {})
            omml = item.get("omml") if item.get("ok") else None
            sanitized = self.sanitize_omml(omml) if isinstance(omml, str) else None
            self.cache[key] = sanitized
            if sanitized is None:
                self.fallback_items.add(key)
                error_message = item.get("error") if isinstance(item, dict) else None
                if isinstance(error_message, str):
                    self._remember_item_error(error_message)
                elif isinstance(omml, str):
                    self._remember_item_error("converter returned invalid OMML")

    def preload_from_markdown(self, text: str) -> None:
        self.convert_many(collect_math_items(text))

    def get(self, latex: str, *, display_mode: bool) -> str | None:
        key = (latex.strip(), display_mode)
        if key[0] and key not in self.cache:
            self.convert_many([key])
        return self.cache.get(key)

    @staticmethod
    def sanitize_omml(omml: str) -> str | None:
        def is_breaking_math_sibling(elem: ET.Element) -> bool:
            text = "".join(elem.itertext()).strip()
            if not text:
                return False
            return text[0] in "+-=<>.,;:])}"

        def is_empty_nary_body(elem: ET.Element) -> bool:
            if elem.tag != f"{{{M_NS}}}nary":
                return False
            body = elem.find(f"{{{M_NS}}}e")
            if body is None:
                return False
            return len(body) == 0 and not "".join(body.itertext()).strip()

        def attach_nary_body(parent: ET.Element) -> None:
            children = list(parent)
            idx = 0
            while idx < len(children):
                child = children[idx]
                if is_empty_nary_body(child):
                    body = child.find(f"{{{M_NS}}}e")
                    assert body is not None
                    move_until = idx + 1
                    moved_any = False
                    while move_until < len(children):
                        sibling = children[move_until]
                        if is_breaking_math_sibling(sibling):
                            break
                        body.append(sibling)
                        moved_any = True
                        move_until += 1
                    if moved_any:
                        for j in range(idx + 1, move_until):
                            parent.remove(children[j])
                        children = list(parent)
                attach_nary_body(child)
                idx += 1

        def accent_char_from_limupp(elem: ET.Element) -> str | None:
            if elem.tag != f"{{{M_NS}}}limUpp":
                return None
            limit = elem.find(f"{{{M_NS}}}lim")
            if limit is None:
                return None
            limit_text = "".join(limit.itertext()).strip()
            if len(limit_text) != 1:
                return None
            return OMML_ACCENT_CHAR_MAP.get(limit_text)

        def make_accent_element(limupp: ET.Element, accent_char: str) -> ET.Element | None:
            base = limupp.find(f"{{{M_NS}}}e")
            if base is None:
                return None

            accent = ET.Element(f"{{{M_NS}}}acc")
            accent_pr = ET.SubElement(accent, f"{{{M_NS}}}accPr")
            ET.SubElement(accent_pr, f"{{{M_NS}}}chr", {f"{{{M_NS}}}val": accent_char})
            acc_base = ET.SubElement(accent, f"{{{M_NS}}}e")
            acc_base.text = base.text
            for child in list(base):
                acc_base.append(child)
            accent.tail = limupp.tail
            return accent

        def replace_limupp_accents(parent: ET.Element) -> None:
            children = list(parent)
            for idx, child in enumerate(children):
                replace_limupp_accents(child)
                accent_char = accent_char_from_limupp(child)
                if accent_char is None:
                    continue
                accent = make_accent_element(child, accent_char)
                if accent is None:
                    continue
                parent.remove(child)
                parent.insert(idx, accent)

        def repl(match: re.Match[str]) -> str:
            raw = match.group(2)
            cleaned = escape(html.unescape(raw))
            return f"{match.group(1)}{cleaned}{match.group(3)}"

        sanitized = OMML_TEXT_PATTERN.sub(repl, omml)
        try:
            root = ET.fromstring(sanitized)
        except ET.ParseError:
            return None
        attach_nary_body(root)
        replace_limupp_accents(root)
        return ET.tostring(root, encoding="unicode")

    def emit_warning(self) -> None:
        if self.warning_reported:
            return
        self.warning_reported = True

        fallback_count = len(self.fallback_items)
        if fallback_count == 0:
            return

        if self.failed_reason:
            install_dir = str(WORD_MATH_DIR.resolve())
            print(
                (
                    "[warning] Word formula conversion is unavailable: "
                    f"{self.failed_reason}. {fallback_count} formula(s) were kept as raw LaTeX.\n"
                    "          To enable Word equations, install the helper dependencies with:\n"
                    f"          cd {install_dir}\n"
                    "          npm install"
                ),
                file=sys.stderr,
            )
            return

        detail = f" Example converter error: {self.item_errors[0]}" if self.item_errors else ""
        print(
            (
                f"[warning] {fallback_count} formula(s) could not be converted to Word equations "
                f"and were kept as raw LaTeX.{detail}"
            ),
            file=sys.stderr,
        )


@dataclass
class MediaImage:
    source_path: Path
    filename: str
    part_name: str
    rel_id: str
    content_type: str
    width_emu: int
    height_emu: int


class MediaManager:
    def __init__(self, *, starting_rid: int = 2, starting_image_index: int = 1) -> None:
        self.starting_rid = starting_rid
        self.next_rid = starting_rid
        self.next_image_index = starting_image_index
        self.next_docpr_id = 1
        self.images: list[MediaImage] = []
        self.by_path: dict[Path, MediaImage] = {}

    def register_image(self, source_path: Path) -> MediaImage | None:
        resolved = source_path.resolve()
        if resolved in self.by_path:
            return self.by_path[resolved]
        if not resolved.exists() or not resolved.is_file():
            return None

        suffix = resolved.suffix.lower().lstrip(".")
        content_type = IMAGE_CONTENT_TYPES.get(suffix)
        if not content_type:
            return None

        width_emu, height_emu = image_extent_emu(resolved)
        rel_id = f"rId{self.next_rid}"
        self.next_rid += 1
        filename = f"image{self.next_image_index}{resolved.suffix.lower()}"
        self.next_image_index += 1
        item = MediaImage(
            source_path=resolved,
            filename=filename,
            part_name=f"media/{filename}",
            rel_id=rel_id,
            content_type=content_type,
            width_emu=width_emu,
            height_emu=height_emu,
        )
        self.images.append(item)
        self.by_path[resolved] = item
        return item

    def next_drawing_id(self) -> int:
        current = self.next_docpr_id
        self.next_docpr_id += 1
        return current

    def image_extensions(self) -> set[str]:
        return {item.filename.rsplit(".", 1)[-1].lower() for item in self.images if "." in item.filename}


def image_extent_emu(path: Path) -> tuple[int, int]:
    default_width = int(MAX_IMAGE_WIDTH_IN * EMU_PER_INCH)
    default_height = int(3.8 * EMU_PER_INCH)
    if Image is None:
        return default_width, default_height

    try:
        with Image.open(path) as img:
            width_px, height_px = img.size
            dpi_info = img.info.get("dpi", (DEFAULT_DPI, DEFAULT_DPI))
    except Exception:
        return default_width, default_height

    if width_px <= 0 or height_px <= 0:
        return default_width, default_height

    try:
        dpi_x = float(dpi_info[0]) if dpi_info and dpi_info[0] else DEFAULT_DPI
        dpi_y = float(dpi_info[1]) if dpi_info and len(dpi_info) > 1 and dpi_info[1] else dpi_x
    except (TypeError, ValueError):
        dpi_x = dpi_y = DEFAULT_DPI

    dpi_x = dpi_x if dpi_x > 1 else DEFAULT_DPI
    dpi_y = dpi_y if dpi_y > 1 else DEFAULT_DPI

    width_emu = int(width_px / dpi_x * EMU_PER_INCH)
    height_emu = int(height_px / dpi_y * EMU_PER_INCH)

    max_width_emu = int(MAX_IMAGE_WIDTH_IN * EMU_PER_INCH)
    max_height_emu = int(MAX_IMAGE_HEIGHT_IN * EMU_PER_INCH)
    scale = min(
        1.0,
        max_width_emu / width_emu if width_emu else 1.0,
        max_height_emu / height_emu if height_emu else 1.0,
    )
    width_emu = max(1, int(width_emu * scale))
    height_emu = max(1, int(height_emu * scale))
    return width_emu, height_emu


def fit_extent_emu(
    width_emu: int,
    height_emu: int,
    *,
    max_width_emu: int,
    max_height_emu: int,
) -> tuple[int, int]:
    if width_emu <= 0 or height_emu <= 0:
        return max_width_emu, max_height_emu
    scale = min(
        1.0,
        max_width_emu / width_emu if width_emu else 1.0,
        max_height_emu / height_emu if height_emu else 1.0,
    )
    return max(1, int(width_emu * scale)), max(1, int(height_emu * scale))


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


def is_caption_paragraph(text: str) -> bool:
    candidate = text.strip()
    if not CAPTION_PATTERN.match(candidate):
        return False
    # 真正的题注应是标题式短语，不应包含中文句号。正文里以
    # "图/表 X-Y" 开头并继续展开说明的段落不能套用题注格式。
    return not any(mark in candidate for mark in ("。", "．"))


def paragraph_xml(
    text: str | None = None,
    *,
    style: str | None = None,
    align: str | None = None,
    preserve_breaks: bool = False,
    runs: list[str] | None = None,
    ppr_extra: str = "",
    first_line_chars: int | None = None,
    first_line: int | None = None,
) -> str:
    ppr: list[str] = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    indent = indent_xml(first_line_chars=first_line_chars, first_line=first_line)
    if indent:
        ppr.append(indent)
    if ppr_extra:
        ppr.append(ppr_extra)
    ppr_xml = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""

    if runs is None:
        value = text or ""
        if preserve_breaks and "\n" in value:
            body = "".join(text_runs(value, preserve_breaks=True))
        else:
            body = f"<w:r>{xml_text(value)}</w:r>"
    else:
        body = "".join(runs)
    return f"<w:p>{ppr_xml}{body}</w:p>"


def formatted_paragraph_xml(
    text: str,
    *,
    style: str | None = None,
    align: str | None = None,
    ppr_extra: str = "",
    first_line_chars: int | None = None,
    first_line: int | None = None,
    run_kwargs: dict[str, object] | None = None,
    preserve_breaks: bool = False,
) -> str:
    runs = text_runs(text, run_kwargs=run_kwargs, preserve_breaks=preserve_breaks)
    return paragraph_xml(
        style=style,
        align=align,
        runs=runs,
        ppr_extra=ppr_extra,
        first_line_chars=first_line_chars,
        first_line=first_line,
    )


def page_break_xml() -> str:
    spacer = spacing_xml(before=0, after=0, line=1, line_rule="exact")
    return f'<w:p><w:pPr>{spacer}</w:pPr><w:r><w:br w:type="page"/></w:r></w:p>'


def add_page_break_before_paragraph_xml(paragraph: str) -> str:
    if "<w:pPr>" in paragraph:
        return paragraph.replace("<w:pPr>", "<w:pPr><w:pageBreakBefore/>", 1)
    return paragraph.replace("<w:p>", "<w:p><w:pPr><w:pageBreakBefore/></w:pPr>", 1)


def section_break_paragraph_xml(sect_pr: str) -> str:
    spacer = spacing_xml(before=0, after=0, line=1, line_rule="exact")
    return f"<w:p><w:pPr>{spacer}{sect_pr}</w:pPr></w:p>"


def add_section_to_paragraph_xml(paragraph: str, sect_pr: str) -> str:
    if "</w:pPr>" in paragraph:
        return paragraph.replace("</w:pPr>", f"{sect_pr}</w:pPr>", 1)
    return paragraph.replace("<w:p>", f"<w:p><w:pPr>{sect_pr}</w:pPr>", 1)


def toc_field_paragraph_xml() -> str:
    runs = [
        field_char_run_xml("begin", dirty=True),
        # Restrict the TOC to heading styles only. The school template marks some
        # non-heading styles (for example the code block style) with outline levels,
        # and the `\\u` switch would pull those paragraphs into the TOC.
        instr_text_run_xml(' TOC \\o "1-3" \\h \\z '),
        field_char_run_xml("separate"),
        run_text_xml(" ", size=24),
        field_char_run_xml("end"),
    ]
    return paragraph_xml(
        runs=runs,
        style=STYLE_TOC_FIELD,
        ppr_extra=spacing_xml(line=288),
    )


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
    cell_style: str = STYLE_TABLE_TEXT,
    *,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
) -> str:
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


def needs_soft_wrap_space(left: str, right: str) -> bool:
    if not left or not right:
        return False
    left_char = left[-1]
    right_char = right[0]
    return (
        left_char.isascii()
        and right_char.isascii()
        and left_char.isalnum()
        and right_char.isalnum()
    )


def join_soft_wrapped_lines(lines: list[str]) -> str:
    parts = [line.strip() for line in lines if line.strip()]
    if not parts:
        return ""
    merged = parts[0]
    for part in parts[1:]:
        separator = " " if needs_soft_wrap_space(merged.rstrip(), part.lstrip()) else ""
        merged += separator + part
    return merged


def split_plain_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    buffer: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if buffer:
                paragraph = join_soft_wrapped_lines(buffer)
                if paragraph:
                    paragraphs.append(paragraph)
                buffer = []
            continue
        if stripped.startswith(">"):
            stripped = stripped[1:].strip()
        buffer.append(stripped)
    if buffer:
        paragraph = join_soft_wrapped_lines(buffer)
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def parse_markdown_document(text: str) -> tuple[str, dict[str, str], str]:
    lines = text.splitlines()
    title = ""
    front_sections: dict[str, str] = {}
    current_section: str | None = None
    buffer: list[str] = []
    body_start = len(lines)

    for idx, line in enumerate(lines):
        if not title:
            match = re.match(r"^#\s+(.*)$", line)
            if match:
                title = match.group(1).strip()
                continue

        if re.match(r"^#\s+\d+\b", line):
            body_start = idx
            break

        section_match = re.match(r"^##\s+(.*)$", line)
        if section_match:
            if current_section is not None:
                front_sections[current_section] = "\n".join(buffer).strip()
            current_section = section_match.group(1).strip()
            buffer = []
            continue

        if re.fullmatch(r"-{3,}|\*{3,}", line.strip()):
            if current_section is not None:
                front_sections[current_section] = "\n".join(buffer).strip()
                current_section = None
                buffer = []
            continue

        if current_section is not None:
            buffer.append(line)

    if current_section is not None:
        front_sections[current_section] = "\n".join(buffer).strip()

    body_text = "\n".join(lines[body_start:]).strip()
    return title, front_sections, body_text


def parse_cover_info(text: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if "：" in stripped:
            key, value = stripped.split("：", 1)
        elif ":" in stripped:
            key, value = stripped.split(":", 1)
        else:
            continue
        info[key.strip()] = value.strip()
    return info


def extract_abstract_and_keywords(text: str, keyword_prefix: str) -> tuple[list[str], str]:
    paragraphs = split_plain_paragraphs(text)
    body: list[str] = []
    keywords = ""
    for paragraph in paragraphs:
        if paragraph.startswith(keyword_prefix):
            keywords = paragraph[len(keyword_prefix):].strip()
        else:
            body.append(paragraph)
    return body, keywords


def split_cover_title_lines(title: str) -> list[str]:
    compact = re.sub(r"\s+", "", title.strip())
    if not compact:
        return [""]

    def avoid_ascii_word_break(value: str, split_at: int) -> int:
        if not (0 < split_at < len(value)):
            return split_at
        if not (value[split_at - 1].isascii() and value[split_at - 1].isalnum()):
            return split_at
        if not (value[split_at].isascii() and value[split_at].isalnum()):
            return split_at

        left = split_at
        while left > 0 and value[left - 1].isascii() and value[left - 1].isalnum():
            left -= 1
        right = split_at
        while right < len(value) and value[right].isascii() and value[right].isalnum():
            right += 1

        candidates = [pos for pos in (left, right) if 0 < pos < len(value)]
        if not candidates:
            return split_at
        return min(candidates, key=lambda pos: abs(pos - split_at))

    if len(compact) <= 14:
        return [compact]
    if len(compact) <= 28:
        split_at = (len(compact) + 1) // 2
        # Avoid visually awkward breaks inside common compound terms on the cover.
        for phrase in ("自适应", "强化学习", "世界模型"):
            start = compact.find(phrase)
            if start < 0:
                continue
            end = start + len(phrase)
            if start < split_at < end:
                split_at = end
                break
        split_at = avoid_ascii_word_break(compact, split_at)
        return [compact[:split_at], compact[split_at:]]

    lines: list[str] = []
    chunk = 14
    start = 0
    while start < len(compact):
        end = min(len(compact), start + chunk)
        end = avoid_ascii_word_break(compact, end)
        if end <= start:
            end = min(len(compact), start + chunk)
        lines.append(compact[start:end])
        start = end
    return lines


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
        # The declaration page in the official sample is higher than the
        # abstract/TOC headings even though it uses the same heading face/size.
        # Use the measured sample position for this special front-matter page.
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


def build_caption_paragraph(
    text: str,
    *,
    style: str | None = None,
    english: bool = False,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
    keep_next: bool = False,
) -> str:
    # Regulation: 五号宋体加粗，居中，段前段后0行
    run_kwargs = {
        "font_ascii": "Times New Roman",
        "font_hansi": "Times New Roman",
        "font_eastasia": "Times New Roman" if english else "宋体",
        "size": 21,
        "bold": True,
    }
    ppr_extra = spacing_xml(line=360, before=0, after=0) + indent_xml(left=0, first_line=0)
    if keep_next:
        # Used by table captions ("表 X-Y …") so the caption stays on the same
        # page as the table that follows.
        ppr_extra += "<w:keepNext/>"
    return paragraph_with_inline_math_xml(
        text,
        style=style,
        align="center",
        ppr_extra=ppr_extra,
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


def build_reference_paragraph(text: str, reference_anchors: dict[str, str] | None = None) -> str:
    run_kwargs = {
        "font_ascii": "Times New Roman",
        "font_hansi": "Times New Roman",
        "font_eastasia": "宋体",
        "size": 21,
    }
    match = re.match(r"^\[(\d+)\]\s*(.*)$", text)
    if not match:
        return formatted_paragraph_xml(
            text,
            style=STYLE_REFERENCE,
            ppr_extra=spacing_xml(line=360) + indent_xml(left=420, hanging=420),
            run_kwargs=run_kwargs,
        )

    ref_id, rest = match.groups()
    anchor = reference_anchors.get(ref_id, reference_bookmark_name(ref_id)) if reference_anchors else reference_bookmark_name(ref_id)
    bookmark_id = reference_bookmark_id(ref_id)
    runs = [
        f'<w:bookmarkStart w:id="{bookmark_id}" w:name="{escape(anchor)}"/>',
        run_text_xml(f"[{ref_id}] ", **run_kwargs),
        f'<w:bookmarkEnd w:id="{bookmark_id}"/>',
    ]
    if rest:
        runs.extend(text_runs(rest, run_kwargs=run_kwargs))
    return paragraph_xml(
        style=STYLE_REFERENCE,
        runs=runs,
        ppr_extra=spacing_xml(line=360) + indent_xml(left=420, hanging=420),
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


def split_statement_content(text: str) -> tuple[list[str], str, str]:
    body_lines: list[str] = []
    author_value = ""
    date_value = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("作者签名："):
            author_value = line.split("：", 1)[1].strip()
            continue
        if line.startswith("签字日期："):
            date_value = line.split("：", 1)[1].strip()
            continue
        body_lines.append(line)
    body_text = "\n".join(body_lines)
    return split_plain_paragraphs(body_text), author_value, date_value


def parse_inline_image_value(value: str) -> tuple[str, str] | None:
    match = IMAGE_PATTERN.match(value.strip())
    if not match:
        return None
    return match.group("alt").strip(), match.group("target").strip()


def first_nonempty_value(*values: str | None, default: str = "") -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return default


def wrap_taskbook_text(text: str, *, max_chars: int = 31, max_lines: int = 6) -> list[str]:
    compact = join_soft_wrapped_lines(split_plain_paragraphs(text))
    lines: list[str] = []
    while compact and len(lines) < max_lines:
        lines.append(compact[:max_chars])
        compact = compact[max_chars:].lstrip()
    while len(lines) < max_lines:
        lines.append("")
    return lines


def taskbook_run_kwargs(*, bold: bool = False, size: int = 24) -> dict[str, object]:
    return {
        "font_ascii": "宋体",
        "font_hansi": "宋体",
        "font_eastasia": "宋体",
        "bold": bold,
        "size": size,
    }


def taskbook_display_width(text: str) -> int:
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in {"W", "F"}:
            width += 2
        else:
            width += 1
    return width


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


def header_xml() -> str:
    ppr_extra = (
        "<w:pBdr>"
        '<w:top w:val="none" w:sz="0" w:space="1" w:color="auto"/>'
        '<w:left w:val="none" w:sz="0" w:space="4" w:color="auto"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="1" w:color="auto"/>'
        '<w:right w:val="none" w:sz="0" w:space="4" w:color="auto"/>'
        "</w:pBdr>"
    )
    paragraph = formatted_paragraph_xml(
        "新疆大学本科毕业论文（设计）",
        style=STYLE_HEADER,
        align="center",
        ppr_extra=ppr_extra,
        run_kwargs={
            "font_ascii": "宋体",
            "font_hansi": "宋体",
            "font_eastasia": "宋体",
            "size": 18,
        },
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:hdr xmlns:w="{W_NS}" xmlns:r="{R_NS}">{paragraph}</w:hdr>'
    )


def empty_footer_xml() -> str:
    paragraph = paragraph_xml("", style=STYLE_FOOTER, first_line=0, first_line_chars=0)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:ftr xmlns:w="{W_NS}" xmlns:r="{R_NS}">{paragraph}</w:ftr>'
    )


def page_footer_xml() -> str:
    runs = [
        field_char_run_xml("begin"),
        instr_text_run_xml("PAGE   \\* MERGEFORMAT"),
        field_char_run_xml("separate"),
        run_text_xml(
            "1",
            font_ascii="Times New Roman",
            font_hansi="Times New Roman",
            font_eastasia="宋体",
            size=18,
        ),
        field_char_run_xml("end"),
    ]
    paragraph = paragraph_xml(runs=runs, style=STYLE_FOOTER, align="center", first_line=0, first_line_chars=0)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:ftr xmlns:w="{W_NS}" xmlns:r="{R_NS}">{paragraph}</w:ftr>'
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


def build_native_document(
    text: str,
    *,
    math_converter: MathConverter | None = None,
    reference_anchors: dict[str, str] | None = None,
    markdown_dir: Path | None = None,
    cover_assets_dir: Path | None = None,
    media_manager: MediaManager | None = None,
) -> tuple[list[str], str, str]:
    markdown_title, front_sections, body_text = parse_markdown_document(text)
    cover_info = parse_cover_info(front_sections.get("封面信息", ""))
    thesis_title = cover_info.get("论文题目") or markdown_title or "新疆大学本科毕业论文"
    profile = native_style_profile()

    # Keep the cover and its blank verso page in an empty-footer section. The
    # second page break carries the section properties, so the declaration starts
    # on physical page 3 while Roman numbering still starts at I.
    cover_sect = native_sect_pr_xml(with_header=True, footer_kind="empty", section_type="continuous")
    front_sect = native_sect_pr_xml(
        with_header=True,
        footer_kind="page",
        section_type="nextPage",
        page_number_format="upperRoman",
        page_number_start=1,
    )
    body_start_sect = native_sect_pr_xml(
        with_header=True,
        footer_kind="page",
        page_number_format="decimal",
        page_number_start=1,
    )
    body_continue_sect = native_sect_pr_xml(with_header=True, footer_kind="page")

    elements: list[str] = []
    elements.extend(
        build_cover_elements(
            thesis_title,
            cover_info,
            cover_assets_dir=cover_assets_dir,
            media_manager=media_manager,
        )
    )
    elements.append(page_break_xml())
    elements.append(add_section_to_paragraph_xml(page_break_xml(), cover_sect))

    declaration = front_sections.get("声明", "").strip()
    if declaration:
        elements.append(build_front_heading("声  明", statement=True))
        statement_paragraphs, author_value, date_value = split_statement_content(declaration)
        for paragraph in statement_paragraphs:
            elements.append(
                build_statement_body_paragraph(
                    paragraph,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
        signature_image = None
        signature_alt = "电子签名"
        inline_signature = parse_inline_image_value(author_value)
        if inline_signature is not None and media_manager is not None and markdown_dir is not None:
            signature_alt, signature_target = inline_signature
            signature_image = media_manager.register_image(markdown_dir / signature_target)
            if signature_image is not None:
                author_value = ""
        signature_blank_count = 10 if signature_image is not None else 14
        for _ in range(signature_blank_count):
            elements.append(build_blank_paragraph(run_size=24))
        elements.append(
            build_statement_signature_paragraph(
                "作者签名：",
                author_value,
                signature_image=signature_image,
                media_manager=media_manager,
                signature_alt=signature_alt or "电子签名",
            )
        )
        elements.append(build_statement_signature_paragraph("签字日期：", date_value, is_date=True))
        elements.append(page_break_xml())

    taskbook = front_sections.get("任务书", "").strip()
    if taskbook:
        elements.extend(build_taskbook_elements(taskbook, cover_info))

    cn_abstract, cn_keywords = extract_abstract_and_keywords(front_sections.get("摘要", ""), "关键词：")
    if cn_abstract or cn_keywords:
        elements.append(build_front_heading("摘  要", page_break_before=bool(taskbook)))
        for paragraph in cn_abstract:
            elements.append(
                build_body_paragraph(
                    paragraph,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
        keyword_paragraph = build_keyword_paragraph(cn_keywords)
        if keyword_paragraph:
            elements.append(build_blank_paragraph())
            elements.append(keyword_paragraph)
        elements.append(page_break_xml())

    en_abstract, en_keywords = extract_abstract_and_keywords(front_sections.get("ABSTRACT", ""), "KEY WORDS:")
    if en_abstract or en_keywords:
        elements.append(build_front_heading("ABSTRACT", english=True))
        for paragraph in en_abstract:
            elements.append(
                build_body_paragraph(
                    paragraph,
                    english=True,
                    math_converter=math_converter,
                    reference_anchors=reference_anchors,
                )
            )
        keyword_paragraph = build_keyword_paragraph(en_keywords, english=True)
        if keyword_paragraph:
            elements.append(build_blank_paragraph())
            elements.append(keyword_paragraph)
        elements.append(page_break_xml())

    elements.append(build_front_heading("目  录", toc=True))
    elements.append(add_section_to_paragraph_xml(toc_field_paragraph_xml(), front_sect))

    body_elements, body_has_section_breaks = build_document_elements(
        body_text,
        profile=profile,
        treat_first_heading_as_title=False,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
        markdown_dir=markdown_dir,
        media_manager=media_manager,
    )
    elements.extend(body_elements)
    body_sect = body_continue_sect if body_has_section_breaks else body_start_sect
    return elements, body_sect, thesis_title


def write_docx(
    markdown_path: Path,
    output_path: Path,
    *,
    cover_assets_dir: Path | None = None,
    use_cover_assets: bool = True,
    enable_formula_conversion: bool = True,
) -> None:
    text = markdown_path.read_text(encoding="utf-8")
    resolved_cover_assets_dir = resolve_cover_assets_dir(markdown_path, cover_assets_dir, use_cover_assets=use_cover_assets)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    math_converter = MathConverter() if enable_formula_conversion else None
    if math_converter is not None:
        math_converter.preload_from_markdown(text)
    reference_anchors = extract_reference_anchors(text)
    media_manager = MediaManager(starting_rid=IMAGE_STARTING_RID)
    elements, sect_pr, doc_title = build_native_document(
        text,
        math_converter=math_converter,
        reference_anchors=reference_anchors,
        markdown_dir=markdown_path.parent,
        cover_assets_dir=resolved_cover_assets_dir,
        media_manager=media_manager,
    )
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(media_manager.image_extensions()))
        zf.writestr("_rels/.rels", rels_xml())
        zf.writestr("docProps/core.xml", core_xml(doc_title))
        zf.writestr("docProps/app.xml", app_xml())
        zf.writestr("word/document.xml", document_xml(elements, sect_pr=sect_pr))
        zf.writestr("word/styles.xml", styles_xml())
        zf.writestr("word/numbering.xml", numbering_xml())
        zf.writestr("word/settings.xml", settings_xml())
        zf.writestr("word/fontTable.xml", font_table_xml())
        zf.writestr("word/header1.xml", header_xml())
        zf.writestr("word/footer1.xml", empty_footer_xml())
        zf.writestr("word/footer2.xml", page_footer_xml())
        zf.writestr("word/_rels/document.xml.rels", document_rels_xml(media_manager))
        for image in media_manager.images:
            zf.writestr(f"word/{image.part_name}", image.source_path.read_bytes())

    if math_converter is not None:
        math_converter.emit_warning()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="xju_thesis_md2docx.py",
        description="Convert a Xinjiang University thesis-style Markdown document to an OOXML DOCX."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", nargs="?", type=Path, default=None)
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=DEFAULT_COVER_ASSETS_DIR if DEFAULT_COVER_ASSETS_DIR.exists() else None,
        help="Directory containing cover assets such as xju-emblem.jpeg and xju-wordmark.png.",
    )
    parser.add_argument(
        "--no-cover-assets",
        action="store_true",
        help="Disable cover logos even if asset files are available.",
    )
    parser.add_argument(
        "--no-formula-conversion",
        action="store_true",
        help="Disable LaTeX-to-OMML conversion and keep formulas as plain LaTeX text.",
    )
    args = parser.parse_args()
    output_path = args.output or args.input.with_suffix(".docx")
    write_docx(
        args.input,
        output_path,
        cover_assets_dir=args.assets_dir,
        use_cover_assets=not args.no_cover_assets,
        enable_formula_conversion=not args.no_formula_conversion,
    )


if __name__ == "__main__":
    main()
