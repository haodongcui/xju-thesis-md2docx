@echo off
setlocal

pushd "%~dp0\..\.."
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m xju_thesis_md2docx.pdf %*
) else (
  python -m xju_thesis_md2docx.pdf %*
)
set STATUS=%errorlevel%
popd

exit /b %STATUS%
