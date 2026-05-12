#!/usr/bin/env bash
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_ROOT="$(cd "$TOOL_DIR/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  bash tools/docx2pdf/docx2pdf.sh [--backend BACKEND] <input.docx> [output.pdf] [backend options]

Backends:
  word          WSL + Windows Microsoft Word COM automation. Highest fidelity for Word preview.
  libreoffice   LibreOffice headless conversion. More portable, lower fidelity for Word-specific layout.
  auto          Prefer word when available, otherwise use libreoffice.

Options:
  --backend BACKEND     word, libreoffice, lo, or auto. Defaults to $XJU_DOCX2PDF_BACKEND or word.
  --list-backends       Print supported backend names.
  -h, --help            Show this help.

Backend-specific options are passed through to the selected backend.
EOF
}

fail() {
  echo "error: $*" >&2
  exit 1
}

word_available() {
  command -v powershell.exe >/dev/null 2>&1 || return 1
  command -v wslpath >/dev/null 2>&1 || return 1
  local check
  check="$(
    powershell.exe -NoProfile -Command "try { \$w = New-Object -ComObject Word.Application; \$w.Quit(); [Console]::Out.Write('OK') } catch { [Console]::Out.Write('FAIL') }" 2>/dev/null \
      | tr -d '\r' || true
  )"
  [[ "$check" == OK ]]
}

libreoffice_available() {
  command -v libreoffice >/dev/null 2>&1 || command -v soffice >/dev/null 2>&1 || [[ -n "${XJU_LIBREOFFICE_BIN:-}" ]]
}

BACKEND="${XJU_DOCX2PDF_BACKEND:-word}"
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --list-backends)
      printf 'word\nlibreoffice\nauto\n'
      exit 0
      ;;
    --backend)
      [[ $# -ge 2 ]] || fail "--backend requires a value"
      BACKEND="$2"
      shift 2
      ;;
    --backend=*)
      BACKEND="${1#--backend=}"
      shift
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

case "$BACKEND" in
  word)
    BACKEND_SCRIPT="$TOOLS_ROOT/word-docx2pdf/docx2pdf.sh"
    ;;
  libreoffice|lo)
    BACKEND_SCRIPT="$TOOLS_ROOT/libreoffice-docx2pdf/docx2pdf.sh"
    ;;
  auto)
    if word_available; then
      BACKEND_SCRIPT="$TOOLS_ROOT/word-docx2pdf/docx2pdf.sh"
    elif libreoffice_available; then
      BACKEND_SCRIPT="$TOOLS_ROOT/libreoffice-docx2pdf/docx2pdf.sh"
    else
      fail "no available DOCX to PDF backend found"
    fi
    ;;
  *)
    fail "unknown backend: $BACKEND"
    ;;
esac

[[ -x "$BACKEND_SCRIPT" ]] || fail "backend script is not executable: $BACKEND_SCRIPT"
exec bash "$BACKEND_SCRIPT" "${ARGS[@]}"
