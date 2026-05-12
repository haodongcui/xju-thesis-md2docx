#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash docx2pdf.sh [options] <input.docx> [output.pdf]

Options:
  --soffice PATH        LibreOffice executable path. Defaults to libreoffice/soffice in PATH.
  --tmp-root PATH       Temporary root directory. Defaults to $TMPDIR/xju_libreoffice_docx2pdf.
  --keep-tmp           Keep temporary files for debugging.
  -h, --help            Show this help.

Environment:
  XJU_LIBREOFFICE_BIN
  XJU_LIBREOFFICE_DOCX2PDF_TMP_ROOT
  XJU_LIBREOFFICE_DOCX2PDF_KEEP_TMP=1
EOF
}

fail() {
  echo "error: $*" >&2
  exit 1
}

path_to_unix() {
  local raw="$1"
  readlink -m "$raw"
}

find_soffice() {
  if [[ -n "${XJU_LIBREOFFICE_BIN:-}" ]]; then
    printf '%s\n' "$XJU_LIBREOFFICE_BIN"
    return 0
  fi
  if command -v libreoffice >/dev/null 2>&1; then
    command -v libreoffice
    return 0
  fi
  if command -v soffice >/dev/null 2>&1; then
    command -v soffice
    return 0
  fi
  return 1
}

KEEP_TMP="${XJU_LIBREOFFICE_DOCX2PDF_KEEP_TMP:-0}"
TMP_ROOT_RAW="${XJU_LIBREOFFICE_DOCX2PDF_TMP_ROOT:-}"
SOFFICE_RAW=""
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --soffice)
      [[ $# -ge 2 ]] || fail "--soffice requires a path"
      SOFFICE_RAW="$2"
      shift 2
      ;;
    --tmp-root)
      [[ $# -ge 2 ]] || fail "--tmp-root requires a path"
      TMP_ROOT_RAW="$2"
      shift 2
      ;;
    --keep-tmp)
      KEEP_TMP=1
      shift
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        POSITIONAL+=("$1")
        shift
      done
      ;;
    -*)
      fail "unknown option: $1"
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [[ ${#POSITIONAL[@]} -lt 1 || ${#POSITIONAL[@]} -gt 2 ]]; then
  usage
  exit 2
fi

if [[ -n "$SOFFICE_RAW" ]]; then
  SOFFICE="$(path_to_unix "$SOFFICE_RAW")"
else
  SOFFICE="$(find_soffice)" || fail "LibreOffice executable not found. Install libreoffice or set XJU_LIBREOFFICE_BIN."
fi
[[ -x "$SOFFICE" ]] || fail "LibreOffice executable is not executable: $SOFFICE"

INPUT_DOCX="$(path_to_unix "${POSITIONAL[0]}")"
[[ -f "$INPUT_DOCX" ]] || fail "input DOCX not found: $INPUT_DOCX"
INPUT_DOCX="$(readlink -f "$INPUT_DOCX")"

if [[ ${#POSITIONAL[@]} -eq 2 ]]; then
  OUTPUT_PDF="$(path_to_unix "${POSITIONAL[1]}")"
else
  OUTPUT_PDF="${INPUT_DOCX%.*}.pdf"
fi
mkdir -p "$(dirname "$OUTPUT_PDF")"
OUTPUT_PDF="$(readlink -m "$OUTPUT_PDF")"

if [[ -z "$TMP_ROOT_RAW" ]]; then
  TMP_ROOT="${TMPDIR:-/tmp}/xju_libreoffice_docx2pdf"
else
  TMP_ROOT="$(path_to_unix "$TMP_ROOT_RAW")"
fi
mkdir -p "$TMP_ROOT"

JOB_DIR="$(mktemp -d "$TMP_ROOT/job-XXXXXX")"
cleanup() {
  if [[ "$KEEP_TMP" == "1" ]]; then
    echo "Temporary files kept at: $JOB_DIR" >&2
  else
    rm -rf "$JOB_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT

cp "$INPUT_DOCX" "$JOB_DIR/input.docx"
mkdir -p "$JOB_DIR/profile"

PROFILE_URI="file://$JOB_DIR/profile"
LOG_FILE="$JOB_DIR/libreoffice.log"
SAL_USE_VCLPLUGIN=gen "$SOFFICE" \
  --headless \
  --nologo \
  --nodefault \
  --nofirststartwizard \
  --nolockcheck \
  --norestore \
  "-env:UserInstallation=$PROFILE_URI" \
  --convert-to pdf:writer_pdf_Export \
  --outdir "$JOB_DIR" \
  "$JOB_DIR/input.docx" >"$LOG_FILE" 2>&1 || {
    cat "$LOG_FILE" >&2 || true
    fail "LibreOffice conversion failed"
  }

if [[ ! -f "$JOB_DIR/input.pdf" ]]; then
  cat "$LOG_FILE" >&2 || true
  fail "LibreOffice did not produce input.pdf in the temporary working directory"
fi

cp "$JOB_DIR/input.pdf" "$OUTPUT_PDF"
echo "PDF written to: $OUTPUT_PDF"
echo "Backend: libreoffice"
