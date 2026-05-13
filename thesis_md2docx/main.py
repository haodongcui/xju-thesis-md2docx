from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .doctor import run_doctor
from .exporter import write_docx
from .pdf.common import PdfError
from .pdf.main import add_backend_options, convert_from_args
from .pdf.registry import backend_names
from .profiles import DEFAULT_PROFILE_NAME, profile_names


def default_pdf_backend() -> str:
    return os.environ.get("THESIS_DOCX2PDF_BACKEND", "word")


def add_docx_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        default=os.environ.get("THESIS_MD2DOCX_PROFILE", DEFAULT_PROFILE_NAME),
        help=(
            f"Thesis format profile: {', '.join(profile_names())}. "
            f"Defaults to $THESIS_MD2DOCX_PROFILE or {DEFAULT_PROFILE_NAME}."
        ),
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Directory containing cover assets such as xju-emblem.jpeg and xju-wordmark.png.",
    )
    parser.add_argument("--no-cover-assets", action="store_true", help="Disable cover logos.")
    parser.add_argument(
        "--no-formula-conversion",
        action="store_true",
        help="Keep formulas as LaTeX text instead of converting them to Word OMML.",
    )


def run_docx(args: argparse.Namespace) -> Path:
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".docx")
    write_docx(
        input_path,
        output_path,
        cover_assets_dir=args.assets_dir,
        use_cover_assets=not args.no_cover_assets,
        enable_formula_conversion=not args.no_formula_conversion,
        profile=args.profile,
    )
    print(f"DOCX written to: {output_path}")
    return output_path


def run_all(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_docx = Path(args.output_docx) if args.output_docx else input_path.with_suffix(".docx")
    output_pdf = Path(args.output_pdf) if args.output_pdf else output_docx.with_suffix(".pdf")
    write_docx(
        input_path,
        output_docx,
        cover_assets_dir=args.assets_dir,
        use_cover_assets=not args.no_cover_assets,
        enable_formula_conversion=not args.no_formula_conversion,
        profile=args.profile,
    )
    print(f"DOCX written to: {output_docx}")
    args.input = str(output_docx)
    args.output = str(output_pdf)
    convert_from_args(args)


def build_parser() -> argparse.ArgumentParser:
    backend_help = ", ".join(backend_names())
    parser = argparse.ArgumentParser(
        prog="md2docx",
        description="Profile-based thesis Markdown to DOCX/PDF helper.",
        epilog=(
            "Examples:\n"
            f"  md2docx docx thesis.md thesis.docx --profile {DEFAULT_PROFILE_NAME}\n"
            "  md2docx pdf thesis.docx thesis.pdf --backend word\n"
            f"  md2docx all thesis.md thesis.docx thesis.pdf --profile {DEFAULT_PROFILE_NAME} --backend auto\n"
            "  md2docx doctor\n"
            "  md2docx doctor --backend auto"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    docx_parser = subparsers.add_parser("docx", help="convert Markdown to DOCX")
    docx_parser.add_argument("input", help="Input Markdown path.")
    docx_parser.add_argument("output", nargs="?", help="Output DOCX path. Defaults to input with .docx suffix.")
    add_docx_options(docx_parser)

    pdf_parser = subparsers.add_parser("pdf", help="convert DOCX to PDF")
    pdf_parser.add_argument("input", help="Input DOCX path.")
    pdf_parser.add_argument("output", nargs="?", help="Output PDF path. Defaults to input with .pdf suffix.")
    pdf_parser.add_argument(
        "--backend",
        default=default_pdf_backend(),
        help=f"PDF backend: {backend_help}. Defaults to $THESIS_DOCX2PDF_BACKEND or word.",
    )
    add_backend_options(pdf_parser)

    all_parser = subparsers.add_parser("all", help="convert Markdown to DOCX, then PDF")
    all_parser.add_argument("input", help="Input Markdown path.")
    all_parser.add_argument("output_docx", nargs="?", help="Output DOCX path.")
    all_parser.add_argument("output_pdf", nargs="?", help="Output PDF path.")
    all_parser.add_argument(
        "--backend",
        default=default_pdf_backend(),
        help=f"PDF backend: {backend_help}. Defaults to $THESIS_DOCX2PDF_BACKEND or word.",
    )
    add_docx_options(all_parser)
    add_backend_options(all_parser)

    doctor_parser = subparsers.add_parser("doctor", help="check DOCX/PDF export environment")
    doctor_parser.add_argument(
        "--backend",
        default="none",
        help=f"PDF backend to check after core DOCX checks: none, {backend_help}. Defaults to none.",
    )

    subparsers.add_parser("list-backends", help="print supported PDF backend names")
    subparsers.add_parser("list-profiles", help="print supported thesis format profile names")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "docx":
            run_docx(args)
            return 0
        if args.command == "pdf":
            convert_from_args(args)
            return 0
        if args.command == "all":
            run_all(args)
            return 0
        if args.command == "doctor":
            return run_doctor(args.backend)
        if args.command == "list-backends":
            print("\n".join(backend_names()))
            return 0
        if args.command == "list-profiles":
            print("\n".join(profile_names()))
            return 0
    except (PdfError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
