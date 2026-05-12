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

echo "libreoffice-docx2pdf environment check"
echo

SOFFICE="$(find_soffice 2>/dev/null || true)"
if [[ -z "$SOFFICE" ]]; then
  fail_check "LibreOffice executable not found in PATH"
else
  ok "LibreOffice executable: $SOFFICE"
  VERSION_OUTPUT="$("$SOFFICE" --version 2>&1 | head -n 1)"
  if [[ -n "$VERSION_OUTPUT" ]]; then
    ok "$VERSION_OUTPUT"
  else
    warn "could not read LibreOffice version"
  fi
fi

if command -v fc-match >/dev/null 2>&1; then
  ok "fontconfig: $(command -v fc-match)"
  for font in SimSun "Times New Roman" "Microsoft YaHei" "Noto Serif CJK SC"; do
    MATCH="$(fc-match "$font" 2>/dev/null | head -n 1)"
    if [[ -n "$MATCH" ]]; then
      ok "font match for $font: $MATCH"
    else
      warn "no font match for $font"
    fi
  done
else
  warn "fc-match not found; cannot inspect font fallback"
fi

exit "$STATUS"
