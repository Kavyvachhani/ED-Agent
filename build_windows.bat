@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM build_windows.bat — Build IndustrilityAgent.exe + IndustrilityAgentSetup.exe
REM
REM OUTPUT:
REM   dist\IndustrilityAgent.exe        — raw portable executable (PyInstaller)
REM   dist\IndustrilityAgentSetup.exe   — proper Windows installer (NSIS)
REM       Installs to Program Files, adds Start Menu, Desktop shortcut,
REM       Apps & Features entry, and auto-start at login.
REM
REM REQUIREMENTS (run once, in any order):
REM   1. Python 3.10+ from https://python.org  (check "Add to PATH")
REM   2. NSIS 3.x     from https://nsis.sourceforge.io/Download
REM      (makensis.exe must be on PATH, or placed in  C:\Program Files (x86)\NSIS\)
REM ═══════════════════════════════════════════════════════════════════════════════

setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Industrility — Windows Build           ║
echo  ╚══════════════════════════════════════════╝
echo.

REM ── 1. Check Python ───────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  ❌  Python not found.
    echo      Download from https://python.org and check "Add Python to PATH".
    pause & exit /b 1
)
echo  ✔  Python found.

REM ── 2. Install / update dependencies ─────────────────────────────────────────
echo  → Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo  ❌  pip install failed
    pause & exit /b 1
)
echo  ✔  Dependencies installed.

REM ── 3. Prepare icons ─────────────────────────────────────────────────────────
echo  → Preparing icons...
python prepare_icons.py
if errorlevel 1 (
    echo  ⚠️   Icon preparation warning - continuing with existing icon
)

REM ── 4. Clean previous builds ─────────────────────────────────────────────────
echo  → Cleaning previous build artefacts...
if exist build       rmdir /s /q build
if exist dist        rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

REM ── 5. PyInstaller build ─────────────────────────────────────────────────────
echo  → Running PyInstaller...
python -m PyInstaller IndustrilityAgent.spec --noconfirm

if not exist "dist\IndustrilityAgent.exe" (
    echo  ❌  PyInstaller did not produce dist\IndustrilityAgent.exe
    pause & exit /b 1
)
echo  ✔  PyInstaller: dist\IndustrilityAgent.exe

REM ── 6. NSIS Installer ────────────────────────────────────────────────────────
echo  → Looking for NSIS (makensis.exe)...

REM Try PATH first
where makensis >nul 2>&1
if not errorlevel 1 (
    set MAKENSIS=makensis
    goto :found_nsis
)

REM Try common install locations
set NSIS_PATHS=^
    "C:\Program Files (x86)\NSIS\makensis.exe" ^
    "C:\Program Files\NSIS\makensis.exe"

for %%P in (%NSIS_PATHS%) do (
    if exist %%P (
        set MAKENSIS=%%P
        goto :found_nsis
    )
)

REM NSIS not found — warn and exit gracefully
echo.
echo  ⚠️  NSIS not found — skipping installer creation.
echo     To build the proper Windows installer:
echo       1. Download NSIS from  https://nsis.sourceforge.io/Download
echo       2. Install it (adds makensis to PATH automatically)
echo       3. Re-run this script
echo.
echo  ✔  Portable .exe is at:  dist\IndustrilityAgent.exe
echo     (Users can run this directly, but it won't appear in Apps and Features)
echo.
pause
exit /b 0

:found_nsis
echo  ✔  NSIS found: %MAKENSIS%

echo  → Building Windows installer with NSIS...
%MAKENSIS% installer_windows.nsi

if not exist "dist\IndustrilityAgentSetup.exe" (
    echo  ❌  NSIS did not produce dist\IndustrilityAgentSetup.exe
    pause & exit /b 1
)
echo  ✔  Installer: dist\IndustrilityAgentSetup.exe

REM ── 7. Summary ───────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════════════════╗
echo  ║  ✅  BUILD COMPLETE                                                  ║
echo  ╠══════════════════════════════════════════════════════════════════════╣
echo  ║  Portable .exe   →  dist\IndustrilityAgent.exe                       ║
echo  ║  Installer       →  dist\IndustrilityAgentSetup.exe  ← share this   ║
echo  ╠══════════════════════════════════════════════════════════════════════╣
echo  ║  How to distribute:                                                  ║
echo  ║    Share IndustrilityAgentSetup.exe with employees.                  ║
echo  ║    They double-click it → Next → Install.                            ║
echo  ║    Appears in Start Menu, Desktop, and Apps and Features.            ║
echo  ╚══════════════════════════════════════════════════════════════════════╝
echo.
pause
