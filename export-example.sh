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

"$PYTHON" md2docx.py all \
  example/thesis-demo.md \
  example/thesis-demo.docx \
  example/thesis-demo.pdf \
  --profile xju-undergraduate-thesis \
  --backend "$PDF_BACKEND"

echo "Generated: $ROOT/example/thesis-demo.docx"
echo "Generated: $ROOT/example/thesis-demo.pdf"

if ! command -v pdftoppm >/dev/null 2>&1; then
  echo "pdftoppm not found. Install poppler-utils to render PDF pages." >&2
  exit 1
fi

mkdir -p example/pages
find example/pages -type f -name 'page*.png' -delete
pdftoppm -png -r "$PREVIEW_DPI" example/thesis-demo.pdf example/pages/page
echo "Generated PDF pages: $ROOT/example/pages/page-*.png"
