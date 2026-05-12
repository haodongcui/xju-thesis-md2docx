#!/usr/bin/env bash
set -euo pipefail

TOOL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_VBS_TEMPLATE="$TOOL_DIR/word_export.vbs"

usage() {
  cat <<'EOF'
Usage:
  bash docx2pdf.sh [options] <input.docx> [output.pdf]

Options:
  --tmp-root PATH        Windows-local temporary root. Accepts WSL or Windows path.
  --vbs-template PATH    Override the VBS converter template.
  --keep-tmp            Keep temporary files for debugging.
  --skip-word-check      Skip the upfront Word COM availability check.
  --no-update-fields     Do not update Word fields before exporting.
  -h, --help             Show this help.

Environment:
  XJU_WORD_DOCX2PDF_TMP_ROOT
  XJU_WORD_DOCX2PDF_VBS_TEMPLATE
  XJU_WORD_DOCX2PDF_KEEP_TMP=1
  XJU_WORD_DOCX2PDF_SKIP_WORD_CHECK=1
  XJU_WORD_DOCX2PDF_UPDATE_FIELDS=0
EOF
}

fail() {
  echo "error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 not found in PATH"
}

powershell_out() {
  powershell.exe -NoProfile -Command "$1" | tr -d '\r'
}

path_to_unix() {
  local raw="$1"
  if [[ "$raw" == /* ]]; then
    readlink -m "$raw"
  elif [[ "$raw" == [A-Za-z]:* || "$raw" == \\\\* ]]; then
    wslpath -u "$raw"
  else
    readlink -m "$raw"
  fi
}

ps_single_quote() {
  local value="$1"
  value="${value//\'/\'\'}"
  printf "'%s'" "$value"
}

KEEP_TMP="${XJU_WORD_DOCX2PDF_KEEP_TMP:-0}"
TMP_ROOT_RAW="${XJU_WORD_DOCX2PDF_TMP_ROOT:-}"
VBS_TEMPLATE="${XJU_WORD_DOCX2PDF_VBS_TEMPLATE:-$DEFAULT_VBS_TEMPLATE}"
SKIP_WORD_CHECK="${XJU_WORD_DOCX2PDF_SKIP_WORD_CHECK:-0}"
UPDATE_FIELDS="${XJU_WORD_DOCX2PDF_UPDATE_FIELDS:-1}"
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --tmp-root)
      [[ $# -ge 2 ]] || fail "--tmp-root requires a path"
      TMP_ROOT_RAW="$2"
      shift 2
      ;;
    --vbs-template)
      [[ $# -ge 2 ]] || fail "--vbs-template requires a path"
      VBS_TEMPLATE="$2"
      shift 2
      ;;
    --keep-tmp)
      KEEP_TMP=1
      shift
      ;;
    --skip-word-check)
      SKIP_WORD_CHECK=1
      shift
      ;;
    --no-update-fields)
      UPDATE_FIELDS=0
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

VBS_TEMPLATE="$(path_to_unix "$VBS_TEMPLATE")"
[[ -f "$VBS_TEMPLATE" ]] || fail "VBS template not found: $VBS_TEMPLATE"

require_command powershell.exe
require_command wslpath

if [[ "$SKIP_WORD_CHECK" != "1" ]]; then
  WORD_CHECK="$(
    powershell.exe -NoProfile -Command "try { \$w = New-Object -ComObject Word.Application; \$w.Quit(); [Console]::Out.Write('OK') } catch { [Console]::Out.Write('FAIL:' + \$_.Exception.Message) }" 2>&1 \
      | tr -d '\r' || true
  )"
  [[ "$WORD_CHECK" == OK ]] || fail "Microsoft Word COM automation is unavailable: $WORD_CHECK"
fi

if [[ -z "$TMP_ROOT_RAW" ]]; then
  TMP_ROOT_RAW="$(powershell_out "[Console]::Out.Write([IO.Path]::GetTempPath())")"
  TMP_ROOT="$(path_to_unix "$TMP_ROOT_RAW")/xju_word_docx2pdf"
else
  TMP_ROOT="$(path_to_unix "$TMP_ROOT_RAW")"
fi

mkdir -p "$TMP_ROOT"
TMP_ROOT_WIN="$(wslpath -w "$TMP_ROOT")"
if [[ "$TMP_ROOT_WIN" == \\\\* ]]; then
  fail "--tmp-root must resolve to a Windows-local path, not a WSL UNC path: $TMP_ROOT_WIN"
fi

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
cp "$VBS_TEMPLATE" "$JOB_DIR/word_export.vbs"

WIN_VBS="$(wslpath -w "$JOB_DIR/word_export.vbs")"
WIN_INPUT_DOCX="$(wslpath -w "$JOB_DIR/input.docx")"
WIN_TMP_PDF="$(wslpath -w "$JOB_DIR/output.pdf")"
WIN_OUTPUT_PDF="$(wslpath -w "$OUTPUT_PDF")"
WIN_JOB_DIR="$(wslpath -w "$JOB_DIR")"

PS_CMD="Set-Location -LiteralPath $(ps_single_quote "$WIN_JOB_DIR"); & cscript //nologo $(ps_single_quote "$WIN_VBS") $(ps_single_quote "$WIN_INPUT_DOCX") $(ps_single_quote "$WIN_TMP_PDF") $(ps_single_quote "$UPDATE_FIELDS")"
PS_STATUS=0
PS_OUTPUT="$(powershell.exe -NoProfile -Command "$PS_CMD" 2>&1)" || PS_STATUS=$?

if [[ $PS_STATUS -ne 0 ]]; then
  [[ -z "$PS_OUTPUT" ]] || echo "$PS_OUTPUT" >&2
  exit "$PS_STATUS"
fi

if [[ ! -f "$JOB_DIR/output.pdf" ]]; then
  [[ -z "$PS_OUTPUT" ]] || echo "$PS_OUTPUT" >&2
  fail "Word did not produce output.pdf in the temporary working directory"
fi

cp "$JOB_DIR/output.pdf" "$OUTPUT_PDF"
echo "PDF written to: $OUTPUT_PDF"
echo "Windows-side PDF path: $WIN_OUTPUT_PDF"
