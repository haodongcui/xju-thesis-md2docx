#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$ROOT/md2docx.sh" docx \
  "$ROOT/example/thesis-demo.md" \
  "$ROOT/example/thesis-demo.generated.docx" \
  --profile xju-undergraduate-thesis

echo "Generated: $ROOT/example/thesis-demo.generated.docx"
