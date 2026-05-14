#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ -f "$ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi

PDF_BACKEND="${THESIS_DOCX2PDF_BACKEND:-auto}"
PREVIEW_DPI="${THESIS_PDF_PREVIEW_DPI:-120}"
OUTPUT_DIR="example/output"
PAGES_DIR="$OUTPUT_DIR/pages"

mkdir -p "$PAGES_DIR"

"$PYTHON" md2docx.py all \
  example/thesis-demo.md \
  "$OUTPUT_DIR/thesis-demo.docx" \
  "$OUTPUT_DIR/thesis-demo.pdf" \
  --profile xju-undergraduate-thesis \
  --backend "$PDF_BACKEND"

echo "Generated: $ROOT/$OUTPUT_DIR/thesis-demo.docx"
echo "Generated: $ROOT/$OUTPUT_DIR/thesis-demo.pdf"

if ! command -v pdftoppm >/dev/null 2>&1; then
  echo "pdftoppm not found. Install poppler-utils to render PDF pages." >&2
  exit 1
fi

find "$PAGES_DIR" -type f -name 'page*.png' -delete
pdftoppm -png -r "$PREVIEW_DPI" "$OUTPUT_DIR/thesis-demo.pdf" "$PAGES_DIR/page"
echo "Generated PDF pages: $ROOT/$PAGES_DIR/page-*.png"
