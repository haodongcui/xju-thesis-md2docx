#!/usr/bin/env bash
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$BACKEND_DIR/../../../.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi

cd "$REPO_ROOT"
exec "$PYTHON" -m xju_thesis_md2docx.pdf doctor --backend libreoffice "$@"
