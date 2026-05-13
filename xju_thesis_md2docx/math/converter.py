from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from ..constants import (
    M_NS,
    OMML_ACCENT_CHAR_MAP,
    OMML_TEXT_PATTERN,
    WORD_MATH_DIR,
    WORD_MATH_REQUIRED_MODULES,
    WORD_MATH_SCRIPT,
)
from ..inline import split_inline_code, split_inline_math


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
                encoding="utf-8",
                errors="replace",
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
