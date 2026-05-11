#!/usr/bin/env bash
set -u

STATUS=0

ok() {
  echo "[ok] $*"
}

warn() {
  echo "[warn] $*" >&2
}

fail_check() {
  echo "[fail] $*" >&2
  STATUS=1
}

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1: $(command -v "$1")"
  else
    fail_check "$1 not found in PATH"
  fi
}

echo "word-docx2pdf environment check"
echo

if uname -r | grep -qi microsoft; then
  ok "WSL kernel detected: $(uname -r)"
else
  warn "this does not look like WSL: $(uname -r)"
fi

check_command powershell.exe
check_command wslpath

if command -v powershell.exe >/dev/null 2>&1; then
  TEMP_PATH="$(
    powershell.exe -NoProfile -Command "[Console]::Out.Write([IO.Path]::GetTempPath())" 2>&1 \
      | tr -d '\r'
  )"
  if [[ -n "$TEMP_PATH" && "$TEMP_PATH" != *"ERROR:"* ]]; then
    ok "Windows temp path: $TEMP_PATH"
  else
    fail_check "could not read Windows temp path: $TEMP_PATH"
  fi

  WORD_CHECK="$(
    powershell.exe -NoProfile -Command "try { \$w = New-Object -ComObject Word.Application; \$w.Quit(); [Console]::Out.Write('OK') } catch { [Console]::Out.Write('FAIL:' + \$_.Exception.Message) }" 2>&1 \
      | tr -d '\r'
  )"
  if [[ "$WORD_CHECK" == "OK" ]]; then
    ok "Microsoft Word COM automation is available"
  else
    fail_check "Microsoft Word COM automation is unavailable: $WORD_CHECK"
  fi
fi

exit "$STATUS"
