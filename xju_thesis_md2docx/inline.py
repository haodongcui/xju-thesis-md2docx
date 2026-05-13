from __future__ import annotations

import re

from .constants import INLINE_MATH_PATTERN


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
