@echo off
setlocal

pushd "%~dp0"

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

if "%THESIS_DOCX2PDF_BACKEND%"=="" set "THESIS_DOCX2PDF_BACKEND=auto"
if "%THESIS_PDF_PREVIEW_DPI%"=="" set "THESIS_PDF_PREVIEW_DPI=120"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "md2docx.py" all "example\thesis-demo.md" "example\thesis-demo.docx" "example\thesis-demo.pdf" --profile xju-undergraduate-thesis --backend "%THESIS_DOCX2PDF_BACKEND%"
) else (
  python "md2docx.py" all "example\thesis-demo.md" "example\thesis-demo.docx" "example\thesis-demo.pdf" --profile xju-undergraduate-thesis --backend "%THESIS_DOCX2PDF_BACKEND%"
)

set STATUS=%errorlevel%
if not %STATUS%==0 goto done

echo Generated: %cd%\example\thesis-demo.docx
echo Generated: %cd%\example\thesis-demo.pdf

where pdftoppm >nul 2>nul
if not %errorlevel%==0 (
  echo pdftoppm not found. Install Poppler and make pdftoppm available in PATH to render PDF pages. 1>&2
  set STATUS=1
  goto done
)

if not exist "example\pages" mkdir "example\pages"
del /q "example\pages\page*.png" >nul 2>nul
pdftoppm -png -r "%THESIS_PDF_PREVIEW_DPI%" "example\thesis-demo.pdf" "example\pages\page"
set STATUS=%errorlevel%
if %STATUS%==0 echo Generated PDF pages: %cd%\example\pages\page-*.png

:done
popd
exit /b %STATUS%
