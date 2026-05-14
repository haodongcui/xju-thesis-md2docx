@echo off
setlocal

pushd "%~dp0"

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

if "%THESIS_DOCX2PDF_BACKEND%"=="" set "THESIS_DOCX2PDF_BACKEND=auto"
if "%THESIS_PDF_PREVIEW_DPI%"=="" set "THESIS_PDF_PREVIEW_DPI=120"
if not exist "example\output\pages" mkdir "example\output\pages"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "md2docx.py" all "example\thesis-demo.md" "example\output\thesis-demo.docx" "example\output\thesis-demo.pdf" --profile xju-undergraduate-thesis --backend "%THESIS_DOCX2PDF_BACKEND%"
) else (
  python "md2docx.py" all "example\thesis-demo.md" "example\output\thesis-demo.docx" "example\output\thesis-demo.pdf" --profile xju-undergraduate-thesis --backend "%THESIS_DOCX2PDF_BACKEND%"
)

set STATUS=%errorlevel%
if not %STATUS%==0 goto done

echo Generated: %cd%\example\output\thesis-demo.docx
echo Generated: %cd%\example\output\thesis-demo.pdf

where pdftoppm >nul 2>nul
if not %errorlevel%==0 (
  echo pdftoppm not found. Install Poppler and make pdftoppm available in PATH to render PDF pages. 1>&2
  set STATUS=1
  goto done
)

del /q "example\output\pages\page*.png" >nul 2>nul
pdftoppm -png -r "%THESIS_PDF_PREVIEW_DPI%" "example\output\thesis-demo.pdf" "example\output\pages\page"
set STATUS=%errorlevel%
if %STATUS%==0 echo Generated PDF pages: %cd%\example\output\pages\page-*.png

:done
popd
exit /b %STATUS%
