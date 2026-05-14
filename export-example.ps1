$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvActivate = Join-Path $Root ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    . $VenvActivate
}

$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
$PdfBackend = if ($env:THESIS_DOCX2PDF_BACKEND) { $env:THESIS_DOCX2PDF_BACKEND } else { "auto" }
$PreviewDpi = if ($env:THESIS_PDF_PREVIEW_DPI) { $env:THESIS_PDF_PREVIEW_DPI } else { "120" }
$OutputDir = Join-Path $Root "example\output"
$PagesDir = Join-Path $OutputDir "pages"
New-Item -ItemType Directory -Force -Path $PagesDir | Out-Null

if ($PythonLauncher) {
    & py -3 "md2docx.py" all `
        "example\thesis-demo.md" `
        "example\output\thesis-demo.docx" `
        "example\output\thesis-demo.pdf" `
        --profile xju-undergraduate-thesis `
        --backend $PdfBackend
} else {
    & python "md2docx.py" all `
        "example\thesis-demo.md" `
        "example\output\thesis-demo.docx" `
        "example\output\thesis-demo.pdf" `
        --profile xju-undergraduate-thesis `
        --backend $PdfBackend
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Generated: $Root\example\output\thesis-demo.docx"
Write-Host "Generated: $Root\example\output\thesis-demo.pdf"

$PdfToPpm = Get-Command pdftoppm -ErrorAction SilentlyContinue
if (-not $PdfToPpm) {
    Write-Error "pdftoppm not found. Install Poppler and make pdftoppm available in PATH to render PDF pages."
    exit 1
}

Get-ChildItem -Path $PagesDir -Filter "page*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force
& $PdfToPpm.Source -png -r $PreviewDpi "example\output\thesis-demo.pdf" "example\output\pages\page"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Generated PDF pages: $Root\example\output\pages\page-*.png"
