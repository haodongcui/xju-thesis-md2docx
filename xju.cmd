@echo off
setlocal

pushd "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "xju.py" %*
) else (
  python "xju.py" %*
)
set STATUS=%errorlevel%
popd

exit /b %STATUS%
