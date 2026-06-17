@echo off
REM ===========================================================================
REM Transport compliance checker - Windows launcher
REM
REM EDIT the two paths below to point at your real folders, then either
REM double-click this file or schedule it in Task Scheduler (see README.md).
REM ===========================================================================

set "ROOT=C:\Users\%USERNAME%\OneDrive\Compliance"
set "OUT=C:\Users\%USERNAME%\OneDrive\Compliance\Reports"

REM Use the Python launcher if present, else fall back to python on PATH.
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PY=py"
) else (
    set "PY=python"
)

cd /d "%~dp0"
%PY% compliance_check.py --root "%ROOT%" --out "%OUT%"

REM Keep the window open if launched by double-click (not when scheduled).
if "%1"=="" pause
