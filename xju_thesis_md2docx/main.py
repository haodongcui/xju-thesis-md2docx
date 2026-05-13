#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from .constants import DEFAULT_COVER_ASSETS_DIR
from .exporter import write_docx


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
