$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue

if ($PythonLauncher) {
    & py -3 (Join-Path $ScriptRoot "md2docx.py") @args
} else {
    & python (Join-Path $ScriptRoot "md2docx.py") @args
}

exit $LASTEXITCODE
