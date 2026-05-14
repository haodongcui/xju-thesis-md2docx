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

if ($PythonLauncher) {
    & py -3 "md2docx.py" all `
        "example\thesis-demo.md" `
        "example\thesis-demo.docx" `
        "example\thesis-demo.pdf" `
        --profile xju-undergraduate-thesis `
        --backend $PdfBackend
} else {
    & python "md2docx.py" all `
        "example\thesis-demo.md" `
        "example\thesis-demo.docx" `
        "example\thesis-demo.pdf" `
        --profile xju-undergraduate-thesis `
        --backend $PdfBackend
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Generated: $Root\example\thesis-demo.docx"
Write-Host "Generated: $Root\example\thesis-demo.pdf"

$PdfToPpm = Get-Command pdftoppm -ErrorAction SilentlyContinue
if (-not $PdfToPpm) {
    Write-Error "pdftoppm not found. Install Poppler and make pdftoppm available in PATH to render PDF pages."
    exit 1
}

$PagesDir = Join-Path $Root "example\pages"
New-Item -ItemType Directory -Force -Path $PagesDir | Out-Null
Get-ChildItem -Path $PagesDir -Filter "page*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force
& $PdfToPpm.Source -png -r $PreviewDpi "example\thesis-demo.pdf" "example\pages\page"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Generated PDF pages: $Root\example\pages\page-*.png"
