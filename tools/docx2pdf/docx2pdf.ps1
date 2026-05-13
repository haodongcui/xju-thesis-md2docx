$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptRoot)
$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue

Push-Location $RepoRoot
if ($PythonLauncher) {
    & py -3 -m xju_thesis_md2docx.pdf @args
} else {
    & python -m xju_thesis_md2docx.pdf @args
}
$Status = $LASTEXITCODE
Pop-Location

exit $Status
